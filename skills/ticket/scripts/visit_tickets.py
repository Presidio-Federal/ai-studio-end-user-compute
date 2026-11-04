#!/usr/bin/env python3
"""Ticket visit.

open runs under mcp_orchestration. It reads the investigation SOAP and
stamp, reuses an active INC when one matches, otherwise creates one,
and writes the ticket chart. It does not investigate.
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

STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "tickets-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "tickets-metadata.schema.json"
META_REL = "tickets/metadata.json"
INVEST_META = "investigations/metadata.json"
MATERIAL = ("number", "sys_id", "state", "short_description", "source_ref", "asset_tag", "cmdb_ci")
INC_RE = re.compile(r"\bINC\d+\b", re.I)
ACTIVE_STATES = {
    "1",
    "2",
    "3",
    "new",
    "in progress",
    "in_progress",
    "on hold",
    "on_hold",
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


def sentence(text):
    cleaned = " ".join(str(text).replace("{", "(").replace("}", ")").split())
    if len(cleaned) > 399:
        cleaned = cleaned[:398].rstrip() + "."
    return cleaned


def checked_at(now):
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def watch_id(now):
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")


def row_keys(serial):
    if isinstance(serial, str) and serial:
        return [f"device:{serial}"]
    return []


def show(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def signature(row):
    return {field: show(row.get(field)) for field in MATERIAL}


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
    return resolved


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def stamp_path(ws, now):
    moment = now
    for _ in range(5):
        ident = watch_id(moment)
        path = Path(ws) / "tickets" / f"{ident}.json"
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
        current = visit_common.load_json(ws, f"tickets/{prior_id}.json")
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


def soap_args(args):
    updates = {}
    for field in ("subjective", "objective", "assessment", "plan"):
        text = strip_arg(getattr(args, field))
        if not text or len(text) > 400 or "{" in text:
            print(json.dumps({"error": f"{field} must be one sentence under 400 characters with no JSON"}), file=sys.stderr)
            return None
        updates[field] = text
    return updates


def metadata(now, **fields):
    body = {
        "keys": [],
        "schema": "tickets-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "ticket",
        "evidence_ref": fields.get("evidence_ref"),
        "last_visit_id": fields.get("last_visit_id"),
        "last_collected_at": fields.get("last_collected_at"),
        "baseline_ref": fields.get("baseline_ref"),
        "status": fields["status"],
        "coverage": fields["coverage"],
        "delta": fields["delta"],
        "devices": fields["devices"],
        "number": fields.get("number"),
        "state": fields.get("state"),
        "issue": fields.get("issue"),
        "subjective": fields["subjective"],
        "objective": fields["objective"],
        "assessment": fields["assessment"],
        "plan": fields["plan"],
    }
    visit_common.validate(body, META_SCHEMA)
    return body


def reply(payload):
    print(visit_common.summary(payload))


def prepare_device(row, note):
    if not isinstance(row, dict) or not row.get("id"):
        return None
    body = dict(row)
    body["id"] = str(body["id"])
    body["name"] = body.get("name") or ""
    body["keys"] = row_keys(body.get("serial"))
    body["note"] = note[:200]
    body["created"] = bool(body.get("created"))
    return body


def save_record(ws, record, soap):
    now = datetime.now(timezone.utc)
    meta = load_meta(ws)
    folded, prior = fold(ws, meta)
    if folded is None:
        print('{"error": "prior stamp chain is unreadable"}', file=sys.stderr)
        return 1
    first = prior is None or not folded
    note = "Baseline." if first else "Changed."
    devices = [row for row in (prepare_device(item, note) for item in record["devices"]) if row]
    if not devices:
        print('{"error": "record has no device with an id"}', file=sys.stderr)
        return 1
    changes = []
    current_ids = set()
    for row in devices:
        current_ids.add(str(row["id"]))
        old = folded.get(str(row["id"]))
        if old:
            before = signature(old)
            after = signature(row)
            for field in MATERIAL:
                if before.get(field) != after.get(field):
                    changes.append(
                        {
                            "id": str(row["id"]),
                            "field": field,
                            "prior": show(before.get(field)),
                            "current": show(after.get(field)),
                        }
                    )
    removed = []
    scope = str(record.get("scope") or "")
    no_motion = (not first) and (not changes) and (not removed) and all(str(row["id"]) in folded for row in devices)
    status = record.get("status") if record.get("status") in ("ok", "degraded", "unknown") else "unknown"
    coverage = record.get("coverage") if record.get("coverage") in ("complete", "partial") else "partial"
    rel = (meta or {}).get("evidence_ref")
    path = None
    if no_motion:
        delta = "unchanged"
        base_ref = (meta or {}).get("baseline_ref")
        last_visit = (meta or {}).get("last_visit_id")
        collected = (meta or {}).get("last_collected_at")
    else:
        delta = "first" if first else "changed"
        ident, path = stamp_path(ws, now)
        if ident is None:
            return 1
        rel = f"tickets/{ident}.json"
        base_ref = None if first else ((prior or {}).get("baseline_ref") or (meta or {}).get("baseline_ref"))
        stamp = {
            "keys": sorted({key for row in devices for key in row["keys"]}),
            "schema": "tickets/v1",
            "source": "tickets",
            "watch_id": ident,
            "checked_at": checked_at(now),
            "ok": status == "ok",
            "status": status,
            "headline": str(record.get("headline") or "")[:400],
            "coverage": coverage,
            "baseline_ref": base_ref,
            "vs_prior": {
                "prior_watch_id": None if first or not prior else prior.get("watch_id"),
                "delta": delta,
                "changed": changes[:40],
            },
            "devices": devices,
            "unchanged": 0 if first else len(current_ids & set(folded)),
            "removed": removed,
            "notes": note,
            "scope": scope or devices[0]["id"],
        }
        if first:
            base_ref = rel
        collected = checked_at(now)
        last_visit = ident
        try:
            visit_common.validate(stamp, STAMP_SCHEMA)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
            return 1
    try:
        body = metadata(
            now,
            evidence_ref=rel,
            last_visit_id=last_visit,
            last_collected_at=collected,
            baseline_ref=base_ref if not (path is not None and first) else rel,
            status=status,
            coverage=coverage if not no_motion else (meta or {}).get("coverage") or coverage,
            delta=delta,
            devices=len(devices),
            number=devices[0].get("number"),
            state=devices[0].get("state"),
            issue=record.get("issue"),
            **soap,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    if path is not None:
        if first:
            stamp["baseline_ref"] = None
        write_json(path, stamp)
        print(f"tickets wrote {rel}", file=sys.stderr)
    write_json(Path(ws) / META_REL, body)
    reply(
        {
            "plane": "tickets",
            "status": body["status"],
            "coverage": body["coverage"],
            "stamp": body["evidence_ref"],
            "metadata": META_REL,
            "delta": delta,
            "devices": len(devices),
            "number": devices[0].get("number"),
            "state": devices[0].get("state"),
            "name": devices[0].get("name"),
            "serial": devices[0].get("serial"),
            "asset_tag": devices[0].get("asset_tag"),
            "created": devices[0].get("created"),
            "quiet": no_motion,
            "plan": soap["plan"],
        }
    )
    return 0


def call(tool, args, budget):
    if budget.exhausted():
        return None, "budget exhausted"
    print(f"tickets call {tool}", file=sys.stderr)
    return visit_common.tool_dict(visit_common.mcp_call(tool, args, retries=1))


def optional(tool, args, budget):
    body, err = call(tool, args, budget)
    if err and visit_common.tool_missing(err):
        return None, "unattached"
    return body, err


def required(tool, args, budget):
    body, err = call(tool, args, budget)
    if err and visit_common.tool_missing(err):
        print(json.dumps({"error": f"{tool} is not attached"}), file=sys.stderr)
        return None, "unattached"
    return body, err


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


def dicts_from(payload):
    found = []

    def walk(obj, depth):
        if depth > 6 or len(found) > 40:
            return
        if isinstance(obj, dict):
            if obj.get("number") or obj.get("sys_id") or obj.get("short_description"):
                found.append(obj)
            for key in ("incidents", "results", "records", "data", "value", "result", "incident"):
                if key in obj:
                    walk(obj[key], depth + 1)
        elif isinstance(obj, list):
            for item in obj[:40]:
                walk(item, depth + 1)

    walk(payload, 0)
    return found


def pick_number(obj, depth=0):
    if depth > 6:
        return None
    if isinstance(obj, str):
        match = INC_RE.search(obj)
        return match.group(0).upper() if match else None
    if isinstance(obj, dict):
        for key in ("number", "incident_number"):
            value = blank(obj.get(key))
            if value:
                return value.upper()
        for value in obj.values():
            found = pick_number(value, depth + 1)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj[:20]:
            found = pick_number(item, depth + 1)
            if found:
                return found
    return None


def pick_sys_id(obj, depth=0):
    if depth > 6:
        return None
    if isinstance(obj, dict):
        for key in ("sys_id", "incident_id", "sysId"):
            value = blank(obj.get(key))
            if value and not INC_RE.fullmatch(value):
                return value
        for value in obj.values():
            found = pick_sys_id(value, depth + 1)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj[:20]:
            found = pick_sys_id(item, depth + 1)
            if found:
                return found
    return None


def pick_state(obj):
    if not isinstance(obj, dict):
        return None
    return cell(obj, "state", "incident_state", "state_label")


def is_active(state):
    text = (state or "").strip().lower()
    if not text:
        return True
    return text in ACTIVE_STATES


def matches_endpoint(row, serial, name):
    desc = (cell(row, "short_description", "description") or "").lower()
    ci = (cell(row, "cmdb_ci", "cmdb_ci.name", "configuration_item") or "").lower()
    blob = f"{desc} {ci}"
    if serial and serial.lower() in blob:
        return True
    if name and name.lower() in blob:
        return True
    return False


def load_investigation(ws, serial):
    meta = visit_common.load_json(ws, INVEST_META)
    if not isinstance(meta, dict):
        print('{"error": "investigations/metadata.json missing"}', file=sys.stderr)
        return None
    ref = blank(meta.get("evidence_ref"))
    if not ref:
        print('{"error": "investigation has no stamp"}', file=sys.stderr)
        return None
    stamp = visit_common.load_json(ws, ref)
    if not isinstance(stamp, dict):
        print('{"error": "investigation stamp is unreadable"}', file=sys.stderr)
        return None
    devices = [row for row in (stamp.get("devices") or []) if isinstance(row, dict)]
    chosen = None
    if serial:
        chosen = next((row for row in devices if blank(row.get("serial")) == serial or blank(row.get("id")) == serial), None)
        if chosen is None:
            print('{"error": "investigation stamp has no matching serial"}', file=sys.stderr)
            return None
    elif devices:
        chosen = devices[0]
    if chosen is None:
        print('{"error": "investigation stamp has no device"}', file=sys.stderr)
        return None
    return meta, stamp, chosen, ref


def find_existing(serial, name, prior_number, budget):
    if prior_number:
        body, err = required("snow_get_incident", {"incident_number": prior_number}, budget)
        if err == "unattached":
            return None, err
        if not err and body:
            state = pick_state(body) or pick_state((dicts_from(body) or [{}])[0])
            number = pick_number(body) or prior_number
            if is_active(state):
                row = dicts_from(body)
                hit = row[0] if row else body
                return {
                    "number": number,
                    "sys_id": pick_sys_id(body),
                    "state": state,
                    "short_description": cell(hit, "short_description"),
                    "created": False,
                }, None
    searches = []
    if name:
        searches.append(name)
    if serial and serial != name:
        searches.append(serial)
    for term in searches:
        body, err = required("snow_find_incidents", {"search": term, "active_only": True, "limit": 25}, budget)
        if err == "unattached":
            return None, err
        if err:
            print(f"tickets find {term} {err[:120]}", file=sys.stderr)
            continue
        for hit in dicts_from(body or {}):
            number = pick_number(hit)
            if not number:
                continue
            if matches_endpoint(hit, serial, name) or (prior_number and number.upper() == prior_number.upper()):
                state = pick_state(hit)
                if is_active(state):
                    return {
                        "number": number,
                        "sys_id": pick_sys_id(hit),
                        "state": state,
                        "short_description": cell(hit, "short_description"),
                        "created": False,
                    }, None
    return None, None


def pick_company(payload):
    rows = dicts_from(payload)
    if not rows and isinstance(payload, dict):
        rows = [payload]
    preferred = []
    for row in rows:
        name = (cell(row, "name", "title") or "").strip()
        ident = pick_sys_id(row) or blank(row.get("sys_id")) or blank(row.get("id"))
        if not ident:
            continue
        item = {"id": ident, "name": name}
        if name.lower().endswith(" euc"):
            preferred.append(item)
        else:
            preferred.append(item)
    for item in preferred:
        if item["name"].lower().endswith(" euc"):
            return item
    return preferred[0] if preferred else None


def pick_asset(payload):
    rows = dicts_from(payload)
    if not rows and isinstance(payload, dict) and (payload.get("sys_id") or payload.get("serial_number")):
        rows = [payload]
    if not rows:
        return None
    hit = rows[0]
    return {
        "asset_id": pick_sys_id(hit) or blank(hit.get("sys_id")) or blank(hit.get("id")),
        "asset_tag": cell(hit, "asset_tag", "display_name"),
        "cmdb_ci": pick_sys_id(hit.get("ci") if isinstance(hit.get("ci"), dict) else {"sys_id": hit.get("ci")})
        if hit.get("ci")
        else None,
        "serial": cell(hit, "serial_number", "serial"),
    }


def ensure_asset(device, budget):
    serial = blank(device.get("serial"))
    hostname = blank(device.get("name")) or serial or "unnamed"
    if not serial:
        return {}, None
    company_id = None
    companies, company_err = optional("snow_find_companies", {"u_euc_demo": True, "limit": 25}, budget)
    if company_err and company_err != "unattached":
        print(f"tickets company {company_err[:120]}", file=sys.stderr)
    elif not company_err:
        chosen = pick_company(companies)
        if chosen:
            company_id = chosen["id"]
    found = None
    for args in (
        {"serial_number": serial, "u_euc_demo": True, "limit": 5},
        {"serial_number": serial, "limit": 5},
    ):
        body, err = optional("snow_find_assets", args, budget)
        if err == "unattached":
            break
        if err:
            print(f"tickets asset find {err[:120]}", file=sys.stderr)
            continue
        found = pick_asset(body)
        if found and found.get("asset_id"):
            break
        found = None
    if found is None:
        payload = {
            "serial_number": serial,
            "display_name": hostname,
            "install_status": "in_use",
            "comments": f"EUC_DEMO endpoint. hostname={hostname}. serial={serial}.",
        }
        if company_id:
            payload["company"] = company_id
        body, err = optional("snow_upsert_asset", payload, budget)
        if err and err != "unattached":
            print(f"tickets asset upsert {err[:120]}", file=sys.stderr)
        elif not err:
            found = pick_asset(body) or {"asset_id": pick_sys_id(body), "asset_tag": None, "cmdb_ci": None, "serial": serial}
    cis, ci_err = optional("snow_find_cis", {"serial_number": serial, "limit": 5}, budget)
    if ci_err and ci_err != "unattached":
        print(f"tickets cis {ci_err[:120]}", file=sys.stderr)
    ci_id = None
    for hit in dicts_from(cis or {}):
        ci_id = pick_sys_id(hit) or blank(hit.get("sys_id")) or blank(hit.get("id"))
        if ci_id:
            break
    if found is None:
        found = {}
    if ci_id:
        found["cmdb_ci"] = ci_id
    return found, None


def pack_line(label, value):
    text = blank(value)
    if not text:
        return None
    return f"{label}={text}"


def troubleshooting_pack(device, invest_meta, source_ref):
    signals = device.get("signals") if isinstance(device.get("signals"), list) else []
    signal_text = "; ".join(
        f"{item.get('name')}={item.get('value')}"
        for item in signals[:8]
        if isinstance(item, dict) and item.get("name") is not None
    )
    lines = [
        "EUC_DEMO",
        pack_line("serial", device.get("serial")),
        pack_line("hostname", device.get("name")),
        pack_line("user", device.get("user")),
        pack_line("email", device.get("email")),
        pack_line("issue", device.get("issue") or invest_meta.get("issue")),
        pack_line("treat", device.get("recommended_treat") or invest_meta.get("treat")),
        pack_line("jamf_id", device.get("jamf_id")),
        pack_line("managed", device.get("managed")),
        pack_line("collector_uid", device.get("collector_uid")),
        pack_line("platform", device.get("platform")),
        pack_line("model", device.get("model")),
        pack_line("os", device.get("os")),
        pack_line("free_disk", device.get("free_disk")),
        pack_line("dex_score", device.get("dex_score")),
        pack_line("crash_count", device.get("crash_count")),
        pack_line("top_process", device.get("top_process")),
        pack_line("last_check_in", device.get("last_check_in") or device.get("last_seen")),
        pack_line("signals", signal_text[:240] if signal_text else None),
        pack_line("proof", source_ref),
        pack_line("soap", blank(invest_meta.get("assessment")) or blank(invest_meta.get("objective"))),
    ]
    return "\n".join(line for line in lines if line)


def create_incident(device, invest_meta, source_ref, budget, asset=None):
    hostname = blank(device.get("name")) or "unnamed"
    issue = blank(device.get("issue")) or blank(invest_meta.get("issue")) or "unknown"
    treat = blank(device.get("recommended_treat") or invest_meta.get("treat")) or "none"
    short = f"EUC_DEMO {issue} on {hostname}"[:160]
    pack = troubleshooting_pack(device, invest_meta, source_ref)
    description = " ".join(
        part
        for part in (
            blank(invest_meta.get("objective")),
            blank(invest_meta.get("assessment")),
            pack.replace("\n", " "),
        )
        if part
    ) or short
    evidence = {}
    if blank(device.get("serial")):
        evidence["serial"] = device["serial"]
    if blank(device.get("name")):
        evidence["hostname"] = device["name"]
    if blank(device.get("user")):
        evidence["username"] = device["user"]
    if blank(device.get("email")):
        evidence["email"] = device["email"]
    if blank(device.get("model")):
        evidence["model"] = device["model"]
    if blank(device.get("os")):
        evidence["os"] = device["os"]
    if blank(device.get("last_check_in") or device.get("last_seen")):
        evidence["last_check_in"] = device.get("last_check_in") or device.get("last_seen")
    if blank(device.get("jamf_id")):
        evidence["jamf_id"] = str(device["jamf_id"])
    if treat:
        evidence["notes"] = f"EUC_DEMO treat={treat} proof={source_ref}"
    payload = {
        "short_description": short,
        "description": description[:4000],
        "work_notes": pack,
        "urgency": "2",
        "impact": "2",
        "contact_type": "virtual_agent",
    }
    if evidence:
        payload["jamf_evidence"] = evidence
    if asset and asset.get("cmdb_ci"):
        payload["cmdb_ci"] = asset["cmdb_ci"]
    body, err = required("snow_create_incident", payload, budget)
    if err:
        return None, err
    number = pick_number(body)
    if not number:
        return None, "create returned no incident number"
    return {
        "number": number,
        "sys_id": pick_sys_id(body),
        "state": pick_state(body) or "1",
        "short_description": short,
        "created": True,
    }, None


def cmd_open(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial)
    if serial and not serial.isalnum():
        print('{"error": "serial must be letters and digits"}', file=sys.stderr)
        return 1
    loaded = load_investigation(ws, serial or None)
    if loaded is None:
        return 1
    invest_meta, _stamp, device, source_ref = loaded
    ident = blank(device.get("serial")) or blank(device.get("id")) or blank(device.get("name"))
    hostname = blank(device.get("name")) or ""
    issue = blank(device.get("issue")) or blank(invest_meta.get("issue"))
    prior_meta = load_meta(ws)
    folded, _prior = fold(ws, prior_meta)
    if folded is None:
        print('{"error": "prior stamp chain is unreadable"}', file=sys.stderr)
        return 1
    prior_row = folded.get(ident) if ident else None
    prior_number = blank((prior_row or {}).get("number")) or blank((prior_meta or {}).get("number"))
    budget = visit_common.Budget(240)
    asset, _asset_err = ensure_asset(device, budget)
    found, err = find_existing(blank(device.get("serial")), hostname or None, prior_number, budget)
    if err == "unattached":
        return 1
    if found is None:
        found, err = create_incident(device, invest_meta, source_ref, budget, asset)
        if err == "unattached":
            return 1
        if err:
            print(json.dumps({"error": err[:200]}), file=sys.stderr)
            return 1
    row = {
        "id": ident,
        "name": hostname,
        "serial": blank(device.get("serial")),
        "user": blank(device.get("user")),
        "number": found["number"],
        "sys_id": found.get("sys_id"),
        "state": found.get("state") or "1",
        "short_description": (found.get("short_description") or f"{issue} on {hostname or ident}")[:160],
        "source_ref": source_ref,
        "asset_tag": (asset or {}).get("asset_tag"),
        "cmdb_ci": (asset or {}).get("cmdb_ci"),
        "created": bool(found.get("created")),
    }
    status = "ok" if row["number"] else "unknown"
    coverage = "complete" if row["number"] else "partial"
    created_word = "opened" if row["created"] else "reused"
    soap = {
        "subjective": sentence(f"Open an incident from the investigation SOAP for {hostname or ident}."),
        "objective": sentence(
            f"{row['number']} {created_word} for {hostname or ident}. Issue {issue or 'unknown'}. Proof will be the ticket stamp."
        ),
        "assessment": sentence(f"{row['number']} covers {issue or 'the finding'} on {hostname or ident}."),
        "plan": sentence("Investigation replies to the caller with this number. This visit does not investigate."),
    }
    record = {
        "status": status,
        "headline": f"{row['number']} {hostname or ident} issue {issue or 'unknown'}."[:400],
        "coverage": coverage,
        "scope": ident,
        "issue": issue,
        "devices": [row],
    }
    return save_record(ws, record, soap)


def cmd_annotate(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    meta = load_meta(ws)
    if not meta:
        print('{"error": "tickets/metadata.json missing"}', file=sys.stderr)
        return 1
    stamp = strip_arg(args.stamp)
    if stamp != meta.get("evidence_ref"):
        print('{"error": "stamp does not match evidence_ref"}', file=sys.stderr)
        return 1
    soap = soap_args(args)
    if soap is None:
        return 1
    meta.update(soap)
    meta["updated_at"] = checked_at(datetime.now(timezone.utc))
    try:
        visit_common.validate(meta, META_SCHEMA)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    write_json(Path(ws) / META_REL, meta)
    reply({"plane": "tickets", "annotated": True, "stamp": stamp, "metadata": META_REL, "number": meta.get("number")})
    return 0


def main():
    parser = argparse.ArgumentParser(description="Tickets visit")
    sub = parser.add_subparsers(dest="command", required=True)
    open_cmd = sub.add_parser("open")
    open_cmd.add_argument("--workspace", required=True)
    open_cmd.add_argument("--serial", default="")
    open_cmd.set_defaults(func=cmd_open)
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
