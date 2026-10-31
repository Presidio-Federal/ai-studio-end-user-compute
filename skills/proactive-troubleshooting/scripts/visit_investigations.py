#!/usr/bin/env python3
"""Proactive troubleshooting visit.

collect runs under execute_command with execution_type mcp_orchestration.
It calls Jamf and Nexthink, then writes the investigations stamp and the
SOAP metadata. annotate runs under execution_type standard and replaces
only the four SOAP sentences.

One device per visit. The first visit is a baseline. A later visit writes
only what changed about that device's issue. A quiet visit rewrites
metadata and does not add a stamp.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workspace-handoff" / "scripts"))
try:
    import visit_common
except ImportError:
    print('{"error": "workspace-handoff skill is not attached"}', file=sys.stderr)
    sys.exit(1)

SECTIONS = ["GENERAL", "HARDWARE", "USER_AND_LOCATION"]
STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "investigations-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "investigations-metadata.schema.json"
META_REL = "investigations/metadata.json"
NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,128}")
INTEREST = ("crash", "cpu", "memory", "disk", "free", "dex", "boot", "score", "process", "freeze", "health")
MATERIAL = ("issue", "serial", "user", "managed", "crash_count", "top_process", "signal")
ISSUES = {
    "application_crashes",
    "experience_recorded",
    "experience_unread",
    "not_in_nexthink",
    "not_in_jamf",
    "no_signal",
    "unknown",
}


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
    print(f"investigations call {tool}", file=sys.stderr)
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


def cell(row, *names):
    if not isinstance(row, dict):
        return None
    folded = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in folded:
            return blank(folded[name.lower()])
    for key, value in folded.items():
        if any(name.lower() in key for name in names):
            return blank(value)
    return None


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
    return []


def nql_rows(payload):
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    headers = payload.get("headers")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, list) and isinstance(headers, list):
        rows = []
        for item in data:
            if isinstance(item, list):
                rows.append({str(headers[i]): item[i] if i < len(item) else None for i in range(len(headers))})
        return rows
    return []


def nql(query_id, parameters, budget):
    payload, err = call("nexthink_nql_execute", {"query_id": query_id, "parameters": parameters}, budget)
    if err:
        return None, err
    return nql_rows(payload), None


def serial_of(raw):
    hardware = section(raw, "hardware")
    general = section(raw, "general")
    return blank(first(hardware.get("serialNumber"), raw.get("serial"), general.get("serialNumber")))


def id_of(raw):
    general = section(raw, "general")
    return blank(first(raw.get("id"), general.get("id")))


def capable(general, raw):
    value = general.get("mdmCapable")
    if value is None:
        value = raw.get("mdmCapable")
    if isinstance(value, dict):
        return as_bool(value.get("capable"))
    return as_bool(value)


def normalize_jamf(raw):
    general = section(raw, "general")
    hardware = section(raw, "hardware")
    located = section(raw, "userAndLocation")
    remote = section(general, "remoteManagement")
    return {
        "id": id_of(raw),
        "name": blank(first(general.get("name"), raw.get("name"))) or "",
        "serial": serial_of(raw),
        "user": blank(first(located.get("username"), located.get("realname"), raw.get("username"))),
        "last_contact": blank(first(general.get("lastContactTime"), raw.get("lastContactTime"))),
        "managed": as_bool(first(remote.get("managed"), general.get("managed"), raw.get("managed"))),
        "supervised": as_bool(first(general.get("supervised"), raw.get("supervised"))),
        "user_approved_mdm": as_bool(first(general.get("userApprovedMdm"), raw.get("userApprovedMdm"))),
        "mdm_capable": capable(general, raw),
    }


def pick_live(rows):
    checked = [row for row in rows if row.get("managed") is True and row.get("last_contact")]
    if not checked:
        checked = [row for row in rows if row.get("last_contact")]
    if not checked:
        return rows[0] if rows else None
    checked.sort(key=lambda row: row.get("last_contact") or "")
    return checked[-1]


def find_jamf(serial, name, budget):
    args = {"page": 0, "page_size": 100}
    if serial:
        args["serial"] = serial
    elif name:
        args["name"] = name
    payload, err = call("jamf_find_devices", args, budget)
    if err:
        return None, err
    rows = [normalize_jamf(raw) for raw in rows_from(payload)]
    rows = [row for row in rows if row.get("id")]
    if serial:
        rows = [row for row in rows if row.get("serial") == serial]
        filtered, filter_err = call(
            "jamf_find_devices",
            {"filter": f'hardware.serialNumber=="{serial}"', "page": 0, "page_size": 100},
            budget,
        )
        if not filter_err:
            extra = [normalize_jamf(raw) for raw in rows_from(filtered)]
            rows.extend(row for row in extra if row.get("serial") == serial and row.get("id"))
    elif name:
        exact = [row for row in rows if row.get("name") == name]
        if exact:
            rows = exact
    by_id = {}
    for row in rows:
        by_id[str(row["id"])] = row
    chosen = pick_live(list(by_id.values()))
    if chosen is None:
        return None, None
    detail, detail_err = call(
        "jamf_get_device",
        {"computer_id": str(chosen["id"]), "sections": SECTIONS},
        budget,
    )
    if detail_err:
        chosen["_partial"] = True
        return chosen, None
    detailed = rows_from(detail)
    if detailed:
        merged = normalize_jamf(detailed[0])
        for key, value in chosen.items():
            if merged.get(key) in (None, "") and value not in (None, ""):
                merged[key] = value
        return merged, None
    chosen["_partial"] = True
    return chosen, None


def lookup_nexthink(device_name, budget):
    rows, err = nql("#mcp_device_lookup", {"device_name": device_name, "user_name": "*"}, budget)
    if err:
        return None, err
    if device_name != "*":
        exact = [row for row in rows if cell(row, "device.name") == device_name]
        if exact:
            rows = exact
    return (rows[0] if rows else {}), None


def signals_from(rows):
    if not rows:
        return []
    picked = []
    seen = set()
    for row in rows[:3]:
        if not isinstance(row, dict):
            continue
        ranked = sorted(
            row.items(),
            key=lambda item: 0 if any(word in str(item[0]).lower() for word in INTEREST) else 1,
        )
        for key, value in ranked:
            if not isinstance(value, (str, int, float, bool)) or value == "":
                continue
            name = str(key)[:80]
            if name in seen:
                continue
            if not any(word in name.lower() for word in INTEREST) and len(picked) >= 4:
                continue
            seen.add(name)
            picked.append({"name": name, "value": str(value)[:80]})
            if len(picked) >= 12:
                return picked
    return picked


def top_process(rows):
    for row in rows:
        value = cell(row, "process", "binary", "application", "name")
        if value and value not in ("*",):
            return value[:80]
    return None


def classify(jamf_row, nexthink_row, health_rows, crash_rows, health_err, lookup_err):
    in_jamf = bool(jamf_row and jamf_row.get("id"))
    in_nexthink = bool(nexthink_row)
    if lookup_err and not in_jamf:
        return "unknown"
    if not in_jamf and not in_nexthink:
        return "unknown"
    if not in_jamf:
        return "not_in_jamf"
    if lookup_err or not in_nexthink:
        return "not_in_nexthink"
    if crash_rows:
        return "application_crashes"
    if health_err:
        return "experience_unread"
    if health_rows:
        return "experience_recorded"
    return "no_signal"


def signal_text(signals):
    parts = [f"{item['name']}={item['value']}" for item in signals]
    return "; ".join(parts)[:200]


def row_keys(serial):
    if isinstance(serial, str) and serial:
        return [f"device:{serial}"]
    return []


def build_device(jamf_row, nexthink_row, health_rows, crash_rows, process_rows, health_err, lookup_err, name_arg):
    jamf_row = jamf_row or {}
    nexthink_row = nexthink_row or {}
    name = jamf_row.get("name") or cell(nexthink_row, "device.name") or name_arg or ""
    serial = jamf_row.get("serial")
    issue = classify(jamf_row, nexthink_row, health_rows, crash_rows, health_err, lookup_err)
    signals = signals_from(health_rows)
    process = top_process(process_rows)
    device = {
        "keys": row_keys(serial),
        "id": serial or name or "unknown",
        "name": name,
        "serial": serial,
        "user": jamf_row.get("user") or cell(nexthink_row, "device.login.last_login_user_name"),
        "jamf_id": None if not jamf_row.get("id") else str(jamf_row["id"]),
        "managed": jamf_row.get("managed"),
        "supervised": jamf_row.get("supervised"),
        "user_approved_mdm": jamf_row.get("user_approved_mdm"),
        "mdm_capable": jamf_row.get("mdm_capable"),
        "collector_uid": cell(nexthink_row, "device.collector.uid"),
        "platform": cell(nexthink_row, "device.operating_system.platform"),
        "last_seen": cell(nexthink_row, "device.last_seen") or jamf_row.get("last_contact"),
        "issue": issue,
        "crash_count": None if crash_rows is None else len(crash_rows),
        "top_process": process,
        "signals": signals,
        "note": "",
        "signal": signal_text(signals),
        "_partial": bool(jamf_row.get("_partial") or health_err or lookup_err),
    }
    return device


def signature(row):
    return {field: row.get(field) for field in MATERIAL}


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


def yn(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unset"


def headline(device, scope):
    if device.get("issue") == "unknown":
        return f"No Jamf or Nexthink record matched {scope}."
    name = device.get("name") or "unnamed"
    serial = device.get("serial") or "no serial"
    crashes = device.get("crash_count")
    crash_text = "" if crashes is None else f" {crashes} crash rows."
    return f"{serial} {name} issue {device.get('issue')}.{crash_text}"[:400]


def judge(device):
    issue = device.get("issue")
    coverage = "partial" if device.get("_partial") else "complete"
    if issue == "unknown":
        return "unknown", coverage
    if issue in ("application_crashes", "experience_unread", "not_in_jamf", "not_in_nexthink"):
        return "degraded", coverage
    return "ok", coverage


def soap_draft(scope, device, status, coverage, rel, delta):
    if scope.startswith("serial:"):
        subjective = f"End-user issue check for serial {scope.split(':', 1)[1]}."
    else:
        subjective = f"End-user issue check for {scope.split(':', 1)[1]}."
    issue = device.get("issue")
    if issue == "unknown":
        objective = f"Jamf and Nexthink returned no device. Proof {rel}."
        assessment = "This visit cannot tell what the end user is hitting."
    else:
        whose = device.get("user") or "unassigned"
        crashes = device.get("crash_count")
        crash_text = "crash rows unread" if crashes is None else f"{crashes} crash rows"
        objective = (
            f"{device.get('name') or 'unnamed'} user {whose}. Issue {issue}. {crash_text}. Proof {rel}."
        )
        assessment = (
            f"Issue {issue} on {device.get('name') or 'unnamed'}. "
            f"Managed {yn(device.get('managed'))}."
        )
    if coverage != "complete":
        assessment = "Part of the read failed. " + assessment
    if delta == "unchanged":
        plan = "No material change since the last stamp. This visit does not open a ticket."
    else:
        plan = "A later visit opens the ticket from this stamp. This visit does not."
    if status == "unknown":
        plan = "Check the device name or serial, then run the visit again."
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
    print(f"investigations workspace={resolved}", file=sys.stderr)
    return resolved


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def stamp_path(ws, now):
    moment = now
    for _ in range(5):
        ident = watch_id(moment)
        path = Path(ws) / "investigations" / f"{ident}.json"
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
        current = visit_common.load_json(ws, f"investigations/{prior_id}.json")
        if not isinstance(current, dict):
            return None, None
        guard += 1
    chain.reverse()
    estate = {}
    for stamp in chain:
        for gone in stamp.get("removed") or []:
            if isinstance(gone, dict) and gone.get("id"):
                estate.pop(str(gone["id"]), None)
        for row in stamp.get("devices") or []:
            if isinstance(row, dict) and row.get("id"):
                estate[str(row["id"])] = row
    return estate, chain[-1] if chain else None


def metadata(now, **fields):
    body = {
        "keys": [],
        "schema": "investigations-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "proactive-troubleshooting",
        "evidence_ref": fields.get("evidence_ref"),
        "last_visit_id": fields.get("last_visit_id"),
        "last_collected_at": fields.get("last_collected_at"),
        "baseline_ref": fields.get("baseline_ref"),
        "status": fields["status"],
        "coverage": fields["coverage"],
        "delta": fields["delta"],
        "devices": fields["devices"],
        "issue": fields.get("issue"),
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
            devices=(meta or {}).get("devices") if isinstance((meta or {}).get("devices"), int) else 0,
            issue=(meta or {}).get("issue") if (meta or {}).get("issue") in ISSUES else None,
            subjective=sentence("End-user issue check did not complete."),
            objective=sentence(reason),
            assessment=sentence("The read failed, so this visit does not change the last stamp."),
            plan=sentence("Run the visit again once Jamf and Nexthink answer."),
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    save_meta(ws, body)
    print(json.dumps({"error": reason[:200]}), file=sys.stderr)
    reply(
        {
            "plane": "investigations",
            "status": "unknown",
            "coverage": "unavailable",
            "stamp": None,
            "metadata": META_REL,
            "delta": prior_delta,
            "devices": body["devices"],
            "issue": body["issue"],
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
        return f"investigations/{ident}.json"
    return (meta or {}).get("baseline_ref")


def emit(row, note):
    body = {key: value for key, value in row.items() if not key.startswith("_")}
    body.pop("signal", None)
    body["note"] = note[:200]
    body["id"] = str(body.get("id") or "")
    if not body["id"]:
        return None
    body["name"] = body.get("name") or ""
    body["keys"] = row_keys(body.get("serial"))
    return body


def cmd_collect(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial)
    name = strip_arg(args.name)
    if serial and not serial.isalnum():
        print('{"error": "serial must be letters and digits"}', file=sys.stderr)
        return 1
    if name and not NAME_RE.fullmatch(name):
        print('{"error": "name must be letters, digits, dot, underscore, or hyphen"}', file=sys.stderr)
        return 1
    if not serial and not name:
        print('{"error": "pass --serial or --name from the task line"}', file=sys.stderr)
        return 1
    scope = f"serial:{serial}" if serial else f"name:{name}"
    now = datetime.now(timezone.utc)
    meta = load_meta(ws)
    folded, prior = fold(ws, meta)
    if folded is None:
        print('{"error": "prior stamp chain is unreadable"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(240)
    jamf_row, jamf_err = find_jamf(serial or None, name or None, budget)
    if jamf_err and jamf_row is None and not name:
        return fail(ws, meta, now, jamf_err)
    device_name = (jamf_row or {}).get("name") or name
    nexthink_row = None
    lookup_err = None
    health_rows = None
    crash_rows = None
    process_rows = []
    health_err = None
    if device_name:
        nexthink_row, lookup_err = lookup_nexthink(device_name, budget)
        if lookup_err:
            nexthink_row = None
        elif nexthink_row:
            device_name = cell(nexthink_row, "device.name") or device_name
        if device_name and not lookup_err:
            health_rows, health_err = nql("#mcp_device_health", {"device_name": device_name}, budget)
            crash_rows, crash_err = nql(
                "#mcp_app_crashes",
                {"device_name": device_name, "binary_name": "*"},
                budget,
            )
            process_rows, process_err = nql("#mcp_device_top_processes", {"device_name": device_name}, budget)
            if crash_err:
                crash_rows = None
                health_err = health_err or crash_err
            if process_err:
                process_rows = []
                health_err = health_err or process_err
            if health_err and health_rows is None:
                health_rows = []
        else:
            health_rows = []
            crash_rows = []
    else:
        health_rows = []
        crash_rows = []
    if jamf_err and not jamf_row and lookup_err:
        return fail(ws, meta, now, jamf_err or lookup_err)
    device = build_device(
        jamf_row,
        nexthink_row,
        health_rows or [],
        crash_rows,
        process_rows or [],
        health_err,
        lookup_err,
        name,
    )
    if jamf_err and not jamf_row:
        device["_partial"] = True
    status, coverage = judge(device)
    prior_row = folded.get(str(device["id"]))
    if prior_row is None and serial:
        prior_row = next((row for row in folded.values() if row.get("serial") == serial), None)
    if prior_row is None and device.get("name"):
        prior_row = next((row for row in folded.values() if row.get("name") == device.get("name")), None)
    changes = diff_rows(prior_row, device) if prior_row else []
    first = prior is None or not folded
    removed_ids = []
    if prior_row and str(prior_row.get("id")) != str(device.get("id")):
        removed_ids.append(str(prior_row["id"]))
    no_motion = (not first) and prior_row is not None and (not changes) and device.get("issue") != "unknown"
    if device.get("issue") == "unknown" and prior_row and prior_row.get("issue") == "unknown":
        no_motion = True
        changes = []
    rel = (meta or {}).get("evidence_ref")
    path = None
    ident = None
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
        rel = f"investigations/{ident}.json"
        if first:
            kept = [emit(device, "Baseline.")]
            notes = "Baseline."
            unchanged = 0
            removed = []
            prior_watch = None
            base_ref = None
        else:
            kept = [] if device.get("issue") == "unknown" and not prior_row else [emit(device, "Changed.")]
            kept = [row for row in kept if row]
            notes = "Changed."
            unchanged = 0 if changes or not prior_row else 1
            removed = []
            for gone_id in removed_ids:
                old = folded.get(gone_id) or {}
                removed.append({"id": gone_id, "serial": old.get("serial"), "keys": row_keys(old.get("serial"))})
            prior_watch = prior.get("watch_id") if prior else None
            base_ref = baseline_ref_for(meta, prior)
        if not kept and not removed:
            kept = [emit(device, "Baseline." if first else "Changed.")]
        stamp = {
            "keys": sorted({key for row in kept for key in row["keys"]} | {key for item in removed for key in item["keys"]}),
            "schema": "investigations/v1",
            "source": "investigations",
            "watch_id": ident,
            "checked_at": checked_at(now),
            "ok": status == "ok",
            "status": status,
            "headline": headline(device, scope),
            "coverage": "partial" if coverage == "unavailable" else coverage,
            "baseline_ref": base_ref,
            "vs_prior": {"prior_watch_id": prior_watch, "delta": delta, "changed": changes[:40]},
            "devices": kept,
            "unchanged": unchanged,
            "removed": removed,
            "notes": notes,
            "scope": scope,
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
    subjective, objective, assessment, plan = soap_draft(scope, device, status, coverage, rel or META_REL, delta)
    try:
        body = metadata(
            now,
            evidence_ref=rel,
            last_visit_id=last_visit,
            last_collected_at=collected,
            baseline_ref=base_ref if not (path is not None and first) else rel,
            status=status,
            coverage=coverage,
            delta=delta,
            devices=0 if device.get("issue") == "unknown" else 1,
            issue=device.get("issue"),
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    if path is not None:
        if first:
            stamp["baseline_ref"] = None
        write_json(path, stamp)
        print(f"investigations wrote {rel}", file=sys.stderr)
    save_meta(ws, body)
    reply(
        {
            "plane": "investigations",
            "status": status,
            "coverage": coverage,
            "stamp": body["evidence_ref"],
            "metadata": META_REL,
            "delta": delta,
            "devices": body["devices"],
            "name": device.get("name"),
            "serial": device.get("serial"),
            "user": device.get("user"),
            "issue": device.get("issue"),
            "crash_count": device.get("crash_count"),
            "top_process": device.get("top_process"),
            "managed": device.get("managed"),
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
        print('{"error": "investigations/metadata.json missing"}', file=sys.stderr)
        return 1
    stamp = strip_arg(args.stamp)
    if stamp != meta.get("evidence_ref"):
        print('{"error": "stamp does not match evidence_ref"}', file=sys.stderr)
        return 1
    updates = {}
    for field in ("subjective", "objective", "assessment", "plan"):
        text = strip_arg(getattr(args, field))
        if not text or len(text) > 400 or "{" in text:
            print(json.dumps({"error": f"{field} must be one sentence under 400 characters with no JSON"}), file=sys.stderr)
            return 1
        updates[field] = text
    meta.update(updates)
    meta["updated_at"] = checked_at(datetime.now(timezone.utc))
    try:
        visit_common.validate(meta, META_SCHEMA)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    save_meta(ws, meta)
    reply({"plane": "investigations", "annotated": True, "stamp": stamp, "metadata": META_REL})
    return 0


def main():
    parser = argparse.ArgumentParser(description="Proactive troubleshooting visit")
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--workspace", required=True)
    collect.add_argument("--serial", default="")
    collect.add_argument("--name", default="")
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
