#!/usr/bin/env python3
"""Jamf computer inventory visit.

collect runs under execute_command with execution_type mcp_orchestration.
It calls jamf_find_devices, jamf_get_device, and jamf_get_device_health,
then writes the stamp and the SOAP metadata. annotate runs under
execution_type standard and replaces only the four SOAP sentences.

A first visit is a baseline. A later visit writes only the computers
that changed. A quiet visit rewrites metadata and does not add a stamp.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workspace-handoff" / "scripts"))
try:
    import visit_common
except ImportError:
    print('{"error": "workspace-handoff skill is not attached"}', file=sys.stderr)
    sys.exit(1)

SECTIONS = [
    "GENERAL",
    "HARDWARE",
    "OPERATING_SYSTEM",
    "USER_AND_LOCATION",
    "SECURITY",
    "DISK_ENCRYPTION",
    "STORAGE",
]
STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "jamf-inventory-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "jamf-metadata.schema.json"
META_REL = "jamf/metadata.json"
MATERIAL = (
    "name",
    "serial",
    "model",
    "os_version",
    "user",
    "site",
    "managed",
    "supervised",
    "user_approved_mdm",
    "mdm_capable",
    "filevault",
    "sip",
    "firewall",
    "severity",
    "checked_in",
)


def strip_arg(value):
    text = "" if value is None else str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1].strip()
    return text


def blank(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
    return None


def sentence(text):
    cleaned = " ".join(str(text).replace("{", "(").replace("}", ")").split())
    if len(cleaned) > 399:
        cleaned = cleaned[:398].rstrip() + "."
    return cleaned


def checked_at(now):
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def watch_id(now):
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")


def call(tool, args, budget):
    if budget.exhausted():
        return None, "budget exhausted"
    print(f"jamf call {tool}", file=sys.stderr)
    envelope = visit_common.mcp_call(tool, args, retries=1)
    return visit_common.tool_dict(envelope)


def section(raw, name):
    value = raw.get(name) if isinstance(raw, dict) else None
    return value if isinstance(value, dict) else {}


def first(*values):
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
        elif value is not None and not isinstance(value, (dict, list)):
            return value
    return None


def site_name(general, raw):
    site = general.get("site")
    if site is None:
        site = raw.get("site")
    if isinstance(site, dict):
        return blank(site.get("name") or site.get("siteName"))
    return blank(site)


def capable(general, raw):
    value = general.get("mdmCapable")
    if value is None:
        value = raw.get("mdmCapable", raw.get("mdm_capable"))
    if isinstance(value, dict):
        return as_bool(value.get("capable"))
    return as_bool(value)


def serial_of(raw):
    if not isinstance(raw, dict):
        return None
    hardware = section(raw, "hardware")
    general = section(raw, "general")
    return blank(first(hardware.get("serialNumber"), raw.get("serial"), general.get("serialNumber"), raw.get("serialNumber")))


def id_of(raw):
    if not isinstance(raw, dict):
        return None
    general = section(raw, "general")
    return blank(first(raw.get("id"), general.get("id"), raw.get("computerId")))


def rows_from(payload):
    if not isinstance(payload, dict):
        return []
    for key in ("devices", "results", "computers"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    device = payload.get("device")
    if isinstance(device, dict):
        return [device]
    if id_of(payload) or serial_of(payload):
        return [payload]
    return []


def total_of(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("total", "totalCount"):
        if isinstance(payload.get(key), int):
            return payload[key]
    return None


def filevault_of(raw, operating):
    disk = section(raw, "diskEncryption")
    return blank(
        first(
            operating.get("fileVault2Status"),
            disk.get("fileVault2Status"),
            disk.get("fileVault2Eligibility"),
            raw.get("filevault"),
            raw.get("fileVaultStatus"),
        )
    )


def normalize(raw, fallback=None):
    base = fallback or {}
    general = section(raw, "general")
    hardware = section(raw, "hardware")
    operating = section(raw, "operatingSystem")
    located = section(raw, "userAndLocation")
    security = section(raw, "security")
    remote = section(general, "remoteManagement")
    row = {
        "id": id_of(raw) or base.get("id"),
        "name": blank(first(general.get("name"), raw.get("name"), hardware.get("name"))) or base.get("name") or "",
        "serial": serial_of(raw) or base.get("serial"),
        "model": blank(first(hardware.get("model"), raw.get("model"), hardware.get("modelIdentifier"))) or base.get("model"),
        "os": blank(first(operating.get("name"), raw.get("os"), raw.get("osName"))) or base.get("os"),
        "os_version": blank(first(operating.get("version"), raw.get("osVersion"), raw.get("os_version"))) or base.get("os_version"),
        "user": blank(first(located.get("username"), located.get("realname"), raw.get("username"), raw.get("user"))) or base.get("user"),
        "site": site_name(general, raw) or base.get("site"),
        "last_contact": blank(
            first(
                general.get("lastContactTime"),
                raw.get("lastContactTime"),
                raw.get("lastCheckIn"),
                raw.get("last_check_in"),
            )
        )
        or base.get("last_contact"),
        "last_ip": blank(first(general.get("lastIpAddress"), general.get("lastReportedIp"), raw.get("lastIp"), raw.get("last_ip")))
        or base.get("last_ip"),
        "managed": as_bool(first(remote.get("managed"), general.get("managed"), raw.get("managed"))),
        "supervised": as_bool(first(general.get("supervised"), raw.get("supervised"))),
        "user_approved_mdm": as_bool(first(general.get("userApprovedMdm"), raw.get("userApprovedMdm"), raw.get("user_approved_mdm"))),
        "mdm_capable": capable(general, raw),
        "filevault": filevault_of(raw, operating) or base.get("filevault"),
        "sip": blank(first(security.get("sipStatus"), security.get("systemIntegrityProtection"), raw.get("sip"))) or base.get("sip"),
        "firewall": as_bool(first(security.get("firewallEnabled"), raw.get("firewall"))),
        "severity": base.get("severity"),
        "findings": list(base.get("findings") or []),
        "note": base.get("note") or "",
    }
    if row["managed"] is None:
        row["managed"] = base.get("managed")
    if row["supervised"] is None:
        row["supervised"] = base.get("supervised")
    if row["user_approved_mdm"] is None:
        row["user_approved_mdm"] = base.get("user_approved_mdm")
    if row["mdm_capable"] is None:
        row["mdm_capable"] = base.get("mdm_capable")
    if row["firewall"] is None:
        row["firewall"] = base.get("firewall")
    return row


def row_keys(row):
    keys = []
    serial = row.get("serial")
    if isinstance(serial, str) and serial and not serial.startswith(" "):
        keys.append(f"device:{serial}")
    site = row.get("site")
    if isinstance(site, str) and site.strip() and not site.startswith(" "):
        keys.append(f"site:{site.strip()}")
    return keys


def emit(row, note):
    body = dict(row)
    body.pop("_partial", None)
    body.pop("_health_miss", None)
    body["keys"] = row_keys(body)
    body["note"] = note[:200]
    body["findings"] = [str(item)[:160] for item in (body.get("findings") or [])[:5]]
    if not body.get("id"):
        return None
    body["id"] = str(body["id"])
    body["name"] = body.get("name") or ""
    return body


def signature(row):
    data = {field: row.get(field) for field in MATERIAL if field != "checked_in"}
    data["checked_in"] = bool(row.get("last_contact"))
    return data


def show(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def diff_rows(prior, current):
    changes = []
    before = signature(prior)
    after = signature(current)
    for field in MATERIAL:
        if before.get(field) != after.get(field):
            changes.append(
                {
                    "id": str(current.get("id")),
                    "field": field,
                    "prior": show(before.get(field)),
                    "current": show(after.get(field)),
                }
            )
    return changes


def pick_live(rows):
    checked = [row for row in rows if row.get("managed") is True and row.get("last_contact")]
    if not checked:
        checked = [row for row in rows if row.get("last_contact")]
    if not checked:
        return None
    checked.sort(key=lambda row: row.get("last_contact") or "")
    return checked[-1]


def health_fields(payload):
    body = payload.get("health") if isinstance(payload.get("health"), dict) else payload
    if not isinstance(body, dict):
        return None, []
    severity = blank(body.get("severity"))
    findings = []
    raw = body.get("findings")
    if isinstance(raw, list):
        for item in raw:
            if len(findings) >= 5:
                break
            if isinstance(item, str) and item.strip():
                findings.append(item.strip()[:160])
            elif isinstance(item, dict):
                text = blank(item.get("summary") or item.get("message") or item.get("title"))
                if text:
                    findings.append(text[:160])
    return severity, findings


def find_pages(serial, budget):
    found = []
    seen = set()
    for page in range(5):
        args = {"page": page, "page_size": 100}
        if serial:
            args["serial"] = serial
        payload, err = call("jamf_find_devices", args, budget)
        if err:
            return found, err
        batch = rows_from(payload)
        for raw in batch:
            ident = id_of(raw) or serial_of(raw)
            if ident and ident in seen:
                continue
            if ident:
                seen.add(ident)
            found.append(raw)
        total = total_of(payload)
        if not batch or len(batch) < 100:
            break
        if total is not None and len(found) >= total:
            break
    return found, None


def find_computers(serial, budget):
    found, err = find_pages(serial, budget)
    if serial:
        matched = [raw for raw in found if serial_of(raw) == serial]
        payload, filter_err = call(
            "jamf_find_devices",
            {"filter": f'hardware.serialNumber=="{serial}"', "page": 0, "page_size": 100},
            budget,
        )
        extra = []
        if not filter_err:
            extra = [raw for raw in rows_from(payload) if serial_of(raw) == serial]
        if err and filter_err and not matched and not extra:
            return None, err
        by_id = {}
        for raw in matched + extra:
            ident = id_of(raw) or serial_of(raw)
            if ident:
                by_id[ident] = raw
        return list(by_id.values()), None
    if err:
        return None, err
    return found, None


def enrich(raw, budget, prior_row=None):
    row = normalize(raw, fallback=prior_row)
    if not row.get("id"):
        return row
    payload, err = call("jamf_get_device", {"computer_id": str(row["id"]), "sections": SECTIONS}, budget)
    if err:
        row["_partial"] = True
    else:
        detailed = rows_from(payload)
        if detailed:
            row = normalize(detailed[0], fallback=row)
        else:
            row["_partial"] = True
    if row.get("managed") is True or row.get("last_contact"):
        payload, err = call("jamf_get_device_health", {"computer_id": str(row["id"])}, budget)
        if err:
            row["_health_miss"] = True
            if prior_row and row.get("severity") is None:
                row["severity"] = prior_row.get("severity")
                row["findings"] = list(prior_row.get("findings") or [])
        else:
            severity, findings = health_fields(payload)
            if severity:
                row["severity"] = severity
            if findings:
                row["findings"] = findings
    return row


def headline(rows, serial, live):
    if serial and not rows:
        return f"No Jamf computer matched {serial}."
    if serial and live:
        managed = "managed" if live.get("managed") else "not managed"
        name = live.get("name") or "unnamed"
        text = f"{live.get('serial')} {name} id {live['id']} {managed}."
        quiet_ids = [row["id"] for row in rows if row["id"] != live["id"] and not row.get("last_contact")]
        if quiet_ids:
            text += " Stub id " + ", ".join(quiet_ids) + " has not checked in."
        return text[:400]
    if serial:
        return f"Serial {serial} has {len(rows)} Jamf records and none are managed and checking in."
    managed_count = sum(1 for row in rows if row.get("managed") is True and row.get("last_contact"))
    return f"{len(rows)} Jamf computers. {managed_count} managed and checking in."


def judge(rows, serial, live):
    partial = any(row.get("_partial") or row.get("_health_miss") for row in rows)
    coverage = "partial" if partial else "complete"
    if not rows:
        return "unknown", coverage
    if serial and (not live or live.get("managed") is not True):
        return "degraded", coverage
    if serial and (live.get("_partial") or live.get("_health_miss")):
        return "degraded", coverage
    if not serial and any(row.get("_partial") or row.get("_health_miss") for row in rows):
        return "degraded", coverage
    return "ok", coverage


def soap_draft(serial, rows, live, status, coverage, rel, delta):
    if serial:
        subjective = f"Jamf inventory for serial {serial}."
    else:
        subjective = "Jamf inventory for the computers in this tenant."
    if not rows:
        objective = f"Jamf returned no computer. Proof {rel}."
        assessment = "No enrolled computer matched this visit."
    elif live:
        approved = "false" if live.get("user_approved_mdm") is False else "true" if live.get("user_approved_mdm") else "unset"
        stubs = [row["id"] for row in rows if row["id"] != live["id"] and row.get("serial") == live.get("serial")]
        stub_text = f" Stub id {', '.join(stubs)}." if stubs else ""
        objective = (
            f"{len(rows)} in scope. Live id {live['id']} {live.get('name')} "
            f"{live.get('os') or ''} {live.get('os_version') or ''} severity {live.get('severity') or 'unset'}."
            f"{stub_text} Proof {rel}."
        )
        assessment = (
            f"id {live['id']} is {'managed' if live.get('managed') else 'not managed'} "
            f"and {'checked in' if live.get('last_contact') else 'not checked in'}. "
            f"User-approved MDM is {approved}."
        )
    else:
        objective = f"{len(rows)} Jamf records and none are managed and checking in. Proof {rel}."
        assessment = "No managed computer is checking in."
    if coverage != "complete":
        assessment = "Part of the Jamf read failed. " + assessment
    if delta == "unchanged":
        plan = "No material change since the last stamp."
    elif delta == "changed":
        plan = "Next visit records only what changed."
    else:
        plan = "Next visit records only what changed."
    if status == "unknown" and not rows:
        plan = "Check the serial, or list the computers again on the next visit."
    return sentence(subjective), sentence(objective), sentence(assessment), sentence(plan)


def resolve_workspace(given):
    raw = Path(strip_arg(given)).expanduser()
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    try:
        resolved = raw.resolve()
    except OSError:
        print('{"error": "workspace path is not usable"}', file=sys.stderr)
        return None
    if not resolved.is_dir():
        print('{"error": "workspace directory is missing"}', file=sys.stderr)
        return None
    print(f"jamf workspace={resolved}", file=sys.stderr)
    return resolved


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def stamp_path(ws, now):
    moment = now
    for _ in range(5):
        ident = watch_id(moment)
        path = Path(ws) / "jamf" / f"{ident}.json"
        if not path.exists():
            return ident, path
        moment = moment + timedelta(seconds=1)
    print('{"error": "stamp path already exists"}', file=sys.stderr)
    return None, None


def load_meta(ws):
    data = visit_common.load_json(ws, META_REL)
    return data if isinstance(data, dict) else None


def fold(ws, meta):
    if not meta or not meta.get("evidence_ref"):
        return {}, None
    current = visit_common.load_json(ws, meta["evidence_ref"])
    if not isinstance(current, dict):
        return None, None
    chain = []
    seen = set()
    guard = 0
    while isinstance(current, dict) and guard < 50:
        ident = current.get("watch_id")
        if not ident or ident in seen:
            break
        seen.add(ident)
        chain.append(current)
        prior_id = (current.get("vs_prior") or {}).get("prior_watch_id")
        if (current.get("vs_prior") or {}).get("delta") == "first" or not prior_id:
            break
        current = visit_common.load_json(ws, f"jamf/{prior_id}.json")
        if not isinstance(current, dict):
            return None, None
        guard += 1
    chain.reverse()
    estate = {}
    for stamp in chain:
        for gone in stamp.get("removed") or []:
            if isinstance(gone, dict) and gone.get("id"):
                estate.pop(str(gone["id"]), None)
        for row in stamp.get("computers") or []:
            if isinstance(row, dict) and row.get("id"):
                estate[str(row["id"])] = row
    return estate, chain[-1] if chain else None


def metadata(now, **fields):
    body = {
        "keys": [],
        "schema": "jamf-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "jamf-inventory",
        "evidence_ref": fields.get("evidence_ref"),
        "last_visit_id": fields.get("last_visit_id"),
        "last_collected_at": fields.get("last_collected_at"),
        "baseline_ref": fields.get("baseline_ref"),
        "status": fields["status"],
        "coverage": fields["coverage"],
        "delta": fields["delta"],
        "computers": fields["computers"],
        "live_id": fields.get("live_id"),
        "subjective": fields["subjective"],
        "objective": fields["objective"],
        "assessment": fields["assessment"],
        "plan": fields["plan"],
    }
    visit_common.validate(body, META_SCHEMA)
    return body


def save_meta(ws, body):
    write_json(Path(ws) / META_REL, body)


def reply(payload):
    print(visit_common.summary(payload))


def fail(ws, meta, now, reason):
    prior_delta = (meta or {}).get("delta")
    if prior_delta not in ("first", "unchanged", "changed", "unread"):
        prior_delta = "unread"
    try:
        body = metadata(
            now,
            evidence_ref=(meta or {}).get("evidence_ref"),
            last_visit_id=(meta or {}).get("last_visit_id"),
            last_collected_at=(meta or {}).get("last_collected_at"),
            baseline_ref=(meta or {}).get("baseline_ref"),
            status="unknown",
            coverage="unavailable",
            delta=prior_delta,
            computers=(meta or {}).get("computers") if isinstance((meta or {}).get("computers"), int) else 0,
            live_id=(meta or {}).get("live_id"),
            subjective=sentence("Jamf inventory did not complete."),
            objective=sentence(reason),
            assessment=sentence("The Jamf read failed, so this visit does not change the last stamp."),
            plan=sentence("Run the visit again once Jamf answers."),
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    save_meta(ws, body)
    print(json.dumps({"error": reason[:200]}), file=sys.stderr)
    reply(
        {
            "plane": "jamf",
            "status": "unknown",
            "coverage": "unavailable",
            "stamp": None,
            "metadata": META_REL,
            "delta": prior_delta,
            "computers": body["computers"],
            "live_id": body["live_id"],
            "quiet": False,
            "plan": body["plan"],
        }
    )
    return 1


def baseline_ref_for(meta, prior):
    if not prior:
        return None
    if prior.get("baseline_ref"):
        return prior["baseline_ref"]
    ident = prior.get("watch_id")
    if ident:
        return f"jamf/{ident}.json"
    return (meta or {}).get("baseline_ref")


def cmd_collect(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial) if args.serial else ""
    if serial and not serial.isalnum():
        print('{"error": "serial must be letters and digits"}', file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    meta = load_meta(ws)
    folded, prior = fold(ws, meta)
    if folded is None:
        print('{"error": "prior stamp chain is unreadable"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(240)
    found, err = find_computers(serial or None, budget)
    if err or found is None:
        return fail(ws, meta, now, err or "jamf_find_devices failed")
    rows = []
    for raw in found:
        if budget.exhausted():
            return fail(ws, meta, now, "budget exhausted")
        rows.append(enrich(raw, budget, folded.get(str(id_of(raw) or ""))))
    rows = [row for row in rows if row.get("id")]
    if serial:
        rows = [row for row in rows if row.get("serial") == serial]
    live = pick_live(rows)
    status, coverage = judge(rows, serial or None, live)
    current = {}
    for row in rows:
        current[str(row["id"])] = row
    prior_ids = set(folded)
    scope_ids = set(current)
    if serial:
        compare_ids = {ident for ident, row in folded.items() if row.get("serial") == serial}
        removed_ids = sorted(compare_ids - scope_ids)
        appeared = scope_ids - compare_ids
    else:
        removed_ids = sorted(prior_ids - scope_ids)
        appeared = scope_ids - prior_ids
    changes = []
    changed_ids = set(appeared)
    for ident, row in current.items():
        if ident in folded and (not serial or folded[ident].get("serial") == serial or ident in compare_ids):
            row_changes = diff_rows(folded[ident], row)
            if row_changes:
                changed_ids.add(ident)
                changes.extend(row_changes)
    changes = changes[:40]
    first = prior is None
    no_motion = (not first) and (not changed_ids) and (not removed_ids)
    ident = None
    path = None
    rel = (meta or {}).get("evidence_ref")
    if no_motion:
        delta = "unchanged"
        collected = checked_at(now) if coverage == "complete" else (meta or {}).get("last_collected_at")
        base_ref = (meta or {}).get("baseline_ref")
        last_visit = (meta or {}).get("last_visit_id")
    else:
        delta = "first" if first else "changed"
        ident, path = stamp_path(ws, now)
        if ident is None:
            return 1
        rel = f"jamf/{ident}.json"
        kept = []
        if first:
            for row in rows:
                emitted = emit(row, "Baseline.")
                if emitted:
                    kept.append(emitted)
            notes = "Baseline."
            unchanged = 0
            removed = []
            prior_watch = None
            base_ref = None
        else:
            for row in rows:
                if str(row["id"]) not in changed_ids:
                    continue
                note = "Appeared." if str(row["id"]) in appeared else "Changed."
                emitted = emit(row, note)
                if emitted:
                    kept.append(emitted)
            notes = "Changed."
            unchanged = len([item for item in scope_ids if item not in changed_ids and item in prior_ids])
            removed = []
            for gone_id in removed_ids:
                old = folded.get(gone_id) or {}
                removed.append(
                    {
                        "id": gone_id,
                        "serial": old.get("serial"),
                        "keys": row_keys(old) if old else [],
                    }
                )
            prior_watch = prior.get("watch_id")
            base_ref = baseline_ref_for(meta, prior)
        stamp = {
            "keys": sorted({key for row in kept for key in row["keys"]} | {key for item in removed for key in item["keys"]}),
            "schema": "jamf-inventory/v1",
            "source": "jamf",
            "watch_id": ident,
            "checked_at": checked_at(now),
            "ok": status == "ok",
            "status": status,
            "headline": headline(rows, serial or None, live)[:400],
            "coverage": coverage if coverage != "unavailable" else "partial",
            "baseline_ref": base_ref,
            "vs_prior": {"prior_watch_id": prior_watch, "delta": delta, "changed": changes},
            "computers": kept,
            "unchanged": unchanged,
            "live_id": None if live is None else str(live["id"]),
            "removed": removed,
            "notes": notes,
            "scope": serial or None,
        }
        if first:
            base_ref = rel
        collected = checked_at(now) if coverage == "complete" else (meta or {}).get("last_collected_at")
        last_visit = ident
        try:
            visit_common.validate(stamp, STAMP_SCHEMA)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
            return 1
    subjective, objective, assessment, plan = soap_draft(
        serial or None, rows, live, status, coverage, rel or META_REL, delta
    )
    if no_motion and coverage == "complete" and live and live.get("last_contact"):
        objective = sentence(f"Still checking in as of {live['last_contact']}. Proof {rel}.")
    try:
        body = metadata(
            now,
            evidence_ref=rel,
            last_visit_id=last_visit,
            last_collected_at=collected,
            baseline_ref=base_ref,
            status=status,
            coverage=coverage,
            delta=delta,
            computers=len(rows),
            live_id=None if live is None else str(live["id"]),
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    if path is not None:
        write_json(path, stamp)
        print(f"jamf wrote {rel}", file=sys.stderr)
    save_meta(ws, body)
    stubs = []
    if serial and live:
        stubs = [row["id"] for row in rows if row["id"] != live["id"]]
    reply(
        {
            "plane": "jamf",
            "status": status,
            "coverage": coverage,
            "stamp": body["evidence_ref"],
            "metadata": META_REL,
            "delta": delta,
            "computers": len(rows),
            "live_id": None if live is None else str(live["id"]),
            "live_name": None if live is None else live.get("name"),
            "serial": None if live is None else live.get("serial"),
            "managed": None if live is None else live.get("managed"),
            "severity": None if live is None else live.get("severity"),
            "stubs": stubs,
            "quiet": no_motion,
            "plan": plan,
        }
    )
    return 0


def cmd_annotate(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    meta = load_meta(ws)
    if not meta:
        print('{"error": "jamf/metadata.json missing"}', file=sys.stderr)
        return 1
    stamp = strip_arg(args.stamp)
    if stamp != meta.get("evidence_ref"):
        print('{"error": "stamp does not match evidence_ref"}', file=sys.stderr)
        return 1
    updates = {}
    for name in ("subjective", "objective", "assessment", "plan"):
        text = strip_arg(getattr(args, name))
        if not text or len(text) > 400 or "{" in text:
            print(json.dumps({"error": f"{name} must be one sentence under 400 characters with no JSON"}), file=sys.stderr)
            return 1
        updates[name] = text
    meta.update(updates)
    meta["updated_at"] = checked_at(datetime.now(timezone.utc))
    try:
        visit_common.validate(meta, META_SCHEMA)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    save_meta(ws, meta)
    reply({"plane": "jamf", "annotated": True, "stamp": stamp, "metadata": META_REL})
    return 0


def main():
    parser = argparse.ArgumentParser(description="Jamf inventory visit")
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--workspace", required=True)
    collect.add_argument("--serial", default="")
    collect.set_defaults(func=cmd_collect)
    annotate = sub.add_parser("annotate")
    annotate.add_argument("--workspace", required=True)
    annotate.add_argument("--stamp", required=True)
    annotate.add_argument("--subjective", required=True)
    annotate.add_argument("--objective", required=True)
    annotate.add_argument("--assessment", required=True)
    annotate.add_argument("--plan", required=True)
    annotate.set_defaults(func=cmd_annotate)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
