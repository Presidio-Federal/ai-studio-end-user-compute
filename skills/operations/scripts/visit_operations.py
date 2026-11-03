#!/usr/bin/env python3
"""Operations visit.

collect runs under mcp_orchestration. It uses attached experience, MDM,
and directory tools for in-life devices that are failing. A missing tool
is a gap. It does not enroll, treat, or open a ticket.
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

STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "operations-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "operations-metadata.schema.json"
META_REL = "operations/metadata.json"
MATERIAL = (
    "issue",
    "serial",
    "user",
    "crash_count",
    "free_disk",
    "dex_score",
    "compliance",
    "managed",
    "lifecycle_stage",
    "snow_incident",
)
NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,128}")


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
    return {field: row.get(field) for field in MATERIAL}


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
        path = Path(ws) / "operations" / f"{ident}.json"
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
        current = visit_common.load_json(ws, f"operations/{prior_id}.json")
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
        "schema": "operations-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "operations",
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
    sources = body.get("sources") or []
    body["sources"] = sorted({item for item in sources if item in ("experience", "mdm", "directory")})
    return body


def save_record(ws, record, soap, fleet=True):
    now = datetime.now(timezone.utc)
    meta = load_meta(ws)
    folded, prior = fold(ws, meta)
    if folded is None:
        print('{"error": "prior stamp chain is unreadable"}', file=sys.stderr)
        return 1
    first = prior is None
    note = "Baseline." if first else "Changed."
    devices = [row for row in (prepare_device(item, note) for item in record["devices"]) if row][:40]
    changes = []
    current_ids = {str(row["id"]) for row in devices}
    for row in devices:
        old = folded.get(str(row["id"]))
        if not old:
            continue
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
    if fleet:
        for old_id, old in folded.items():
            if old_id not in current_ids:
                removed.append({"id": old_id, "serial": old.get("serial"), "keys": row_keys(old.get("serial"))})
    no_motion = (not first) and (not changes) and (not removed) and all(str(row["id"]) in folded for row in devices)
    status = record.get("status") if record.get("status") in ("ok", "degraded", "unknown") else "unknown"
    coverage = record.get("coverage") if record.get("coverage") in ("complete", "partial") else "partial"
    issue = devices[0].get("issue") if devices else None
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
        rel = f"operations/{ident}.json"
        base_ref = None if first else ((prior or {}).get("baseline_ref") or (meta or {}).get("baseline_ref"))
        stamp = {
            "keys": sorted({key for row in devices for key in row["keys"]} | {key for item in removed for key in item["keys"]}),
            "schema": "operations/v1",
            "source": "operations",
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
            "scope": str(record.get("scope") or "fleet"),
        }
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
            issue=issue,
            **soap,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    if path is not None:
        if first:
            stamp["baseline_ref"] = None
        write_json(path, stamp)
        print(f"operations wrote {rel}", file=sys.stderr)
    write_json(Path(ws) / META_REL, body)
    reply(
        {
            "plane": "operations",
            "status": body["status"],
            "coverage": body["coverage"],
            "stamp": body["evidence_ref"] if not no_motion else rel,
            "metadata": META_REL,
            "delta": delta,
            "devices": len(devices),
            "issue": issue,
            "quiet": no_motion,
            "plan": soap["plan"],
        }
    )
    return 0


def call(tool, args, budget):
    if budget.exhausted():
        return None, "budget exhausted"
    print(f"operations call {tool}", file=sys.stderr)
    return visit_common.tool_dict(visit_common.mcp_call(tool, args, retries=1))


def optional(tool, args, budget):
    body, err = call(tool, args, budget)
    if err and "not found" in err.lower():
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


def as_int(value):
    text = blank(value)
    if text is None:
        return None
    try:
        return int(float(text.split()[0].replace(",", "")))
    except (TypeError, ValueError):
        return None


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


def nql_rows(payload):
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    headers = payload.get("headers")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, list) and isinstance(headers, list):
        return [
            {str(headers[i]): item[i] if i < len(item) else None for i in range(len(headers))}
            for item in data
            if isinstance(item, list)
        ]
    return []


def rows_from(payload):
    if not isinstance(payload, dict):
        return []
    for key in ("devices", "results", "computers", "value"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    device = payload.get("device")
    if isinstance(device, dict):
        return [device]
    return []


def empty_row(ident):
    return {
        "id": ident,
        "name": "",
        "serial": None,
        "user": None,
        "collector_uid": None,
        "platform": None,
        "last_seen": None,
        "jamf_id": None,
        "managed": None,
        "compliance": None,
        "issue": "unknown",
        "crash_count": None,
        "free_disk": None,
        "dex_score": None,
        "lifecycle_stage": None,
        "snow_incident": None,
        "snow_request": None,
        "agent_case_status": None,
        "sources": [],
        "on_watchlist": False,
    }


def upsert(estate, ident, **fields):
    if not ident:
        return
    row = estate.get(ident) or empty_row(ident)
    source = fields.pop("source", None)
    for key, value in fields.items():
        if value not in (None, "", []):
            row[key] = value
    if source and source not in row["sources"]:
        row["sources"].append(source)
    if row.get("serial"):
        row["id"] = row["serial"]
        row["keys"] = row_keys(row["serial"])
    else:
        row["keys"] = []
    estate[row["id"]] = row
    if ident != row["id"]:
        estate.pop(ident, None)


def from_nql(row):
    serial = cell(row, "device.hardware.bios_serial_number", "serial")
    name = cell(row, "device.name", "name") or ""
    ident = serial or name
    if not ident:
        return None
    crashes = as_int(cell(row, "crash", "number_of_crashes"))
    return {
        "ident": ident,
        "name": name,
        "serial": serial,
        "user": cell(row, "device.login.last_login_user_name", "user"),
        "collector_uid": cell(row, "device.collector.uid", "collector"),
        "platform": cell(row, "device.operating_system.platform", "platform"),
        "last_seen": cell(row, "device.last_seen", "last_seen"),
        "crash_count": crashes,
        "free_disk": cell(row, "free_disk", "free.disk", "disk.free", "free"),
        "dex_score": cell(row, "dex_score", "dex.score", "score"),
        "lifecycle_stage": cell(row, "lifecycle_stage"),
        "snow_incident": cell(row, "snow_incident"),
        "snow_request": cell(row, "snow_request"),
        "agent_case_status": cell(row, "agent_case_status"),
        "source": "experience",
    }


def classify(row):
    if row.get("crash_count"):
        return "crashes"
    disk = blank(row.get("free_disk"))
    if disk:
        try:
            if float(disk.split()[0].replace(",", "")) < 10:
                return "disk"
        except ValueError:
            pass
    score = blank(row.get("dex_score"))
    if score:
        try:
            if float(score.split()[0].replace(",", "")) < 70:
                return "experience"
        except ValueError:
            pass
    compliance = (row.get("compliance") or "").lower()
    if compliance and compliance not in ("compliant", "ok"):
        return "compliance"
    if row.get("on_watchlist"):
        return "experience"
    if row.get("sources"):
        return "recorded"
    return "unknown"


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
        print('{"error": "name must be a hostname"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(240)
    estate = {}
    attached = []
    errors = []

    def take(tool, payload_args):
        body, err = optional(tool, payload_args, budget)
        if err == "unattached":
            return None
        attached.append(tool)
        if err:
            errors.append(err)
            return None
        return body

    fleet = not serial and not name
    if fleet:
        payload = take("nexthink_nql_execute", {"query_id": "#mcp_dex_watchlist"})
        for raw in nql_rows(payload or {}):
            parsed = from_nql(raw)
            if not parsed:
                continue
            ident = parsed.pop("ident")
            parsed["on_watchlist"] = True
            upsert(estate, ident, **parsed)
        payload = take("intune_list_intune_devices", {"compliance_state": "noncompliant", "top": 25})
        for raw in rows_from(payload or {}):
            host = blank(raw.get("deviceName") or raw.get("name")) or ""
            serial_value = blank(raw.get("serialNumber") or raw.get("serial"))
            ident = serial_value or host
            if not ident:
                continue
            upsert(
                estate,
                ident,
                name=host,
                serial=serial_value,
                user=blank(raw.get("userPrincipalName") or raw.get("emailAddress")),
                compliance=blank(raw.get("complianceState") or "noncompliant"),
                source="directory",
            )
    else:
        lookup_name = name
        payload = take("nexthink_nql_execute", {"query_id": "#mcp_device_lookup", "parameters": {"device_name": name or "*", "user_name": "*"}})
        chosen = None
        for raw in nql_rows(payload or {}):
            parsed = from_nql(raw)
            if not parsed:
                continue
            if serial and parsed.get("serial") == serial:
                chosen = parsed
                break
            if name and parsed.get("name") == name:
                chosen = parsed
                break
            if chosen is None:
                chosen = parsed
        if chosen:
            lookup_name = chosen.get("name") or lookup_name
            ident = chosen.pop("ident")
            upsert(estate, ident, **chosen)
        if lookup_name:
            payload = take("nexthink_nql_execute", {"query_id": "#mcp_device_vitals", "parameters": {"device_name": lookup_name}})
            for raw in nql_rows(payload or {}):
                parsed = from_nql(raw)
                if parsed:
                    ident = parsed.pop("ident")
                    upsert(estate, ident, **parsed)
        jamf_args = {"page": 0, "page_size": 25}
        if serial:
            jamf_args["serial"] = serial
        elif name:
            jamf_args["name"] = name
        payload = take("jamf_find_devices", jamf_args)
        jamf_rows = rows_from(payload or {})
        jamf_id = None
        for raw in jamf_rows:
            serial_value = blank(raw.get("serial") or (raw.get("hardware") or {}).get("serialNumber"))
            host = blank(raw.get("name") or (raw.get("general") or {}).get("name")) or ""
            ident = serial_value or host or serial or name
            jamf_id = blank(raw.get("id") or (raw.get("general") or {}).get("id"))
            upsert(
                estate,
                ident,
                name=host,
                serial=serial_value or serial,
                user=blank(raw.get("username") or (raw.get("userAndLocation") or {}).get("username")),
                jamf_id=jamf_id,
                managed=as_bool(raw.get("managed")),
                source="mdm",
            )
            break
        if jamf_id or serial:
            health_args = {"serial": serial} if serial else {"computer_id": jamf_id}
            payload = take("jamf_get_device_health", health_args)
            if payload:
                ident = serial or name
                severity = blank(payload.get("severity"))
                upsert(
                    estate,
                    ident,
                    serial=serial or None,
                    name=name or "",
                    managed=as_bool((payload.get("summary") or {}).get("managed")) if isinstance(payload.get("summary"), dict) else None,
                    source="mdm",
                )
                if ident in estate and severity in ("warn", "critical"):
                    estate[ident]["on_watchlist"] = True
        if lookup_name:
            payload = take("intune_list_intune_devices", {"name": lookup_name, "top": 25})
            for raw in rows_from(payload or {}):
                host = blank(raw.get("deviceName") or raw.get("name")) or lookup_name
                serial_value = blank(raw.get("serialNumber") or raw.get("serial")) or serial
                ident = serial_value or host
                upsert(
                    estate,
                    ident,
                    name=host,
                    serial=serial_value,
                    compliance=blank(raw.get("complianceState")),
                    source="directory",
                )

    devices = list(estate.values())
    for row in devices:
        row["issue"] = classify(row)
        row.pop("on_watchlist", None)
        if errors and not row["sources"]:
            row["issue"] = "unread"
    failing = {"crashes", "disk", "experience", "compliance", "unread"}
    status = "unknown" if not attached else "degraded" if any(row["issue"] in failing for row in devices) else "ok"
    coverage = "partial" if errors or not attached else "complete"
    if not attached:
        coverage = "partial"
        status = "unknown"
    issue = None
    for row in devices:
        if row["issue"] in failing:
            issue = row["issue"]
            break
    if issue is None and devices:
        issue = devices[0]["issue"]
    scope = serial or name or "fleet"
    if devices:
        first = devices[0]
        headline = f"{len(devices)} device(s). {first.get('serial') or 'no serial'} {first.get('name') or 'unnamed'} issue {first.get('issue')}."
    else:
        headline = "No failing devices in scope."
    record = {
        "status": status,
        "headline": headline[:400],
        "coverage": coverage,
        "scope": scope,
        "devices": devices,
    }
    soap = {
        "subjective": sentence(f"In-life check for {scope}."),
        "objective": sentence(f"{len(devices)} in scope. Issue {issue or 'none'}. Coverage {coverage}."),
        "assessment": sentence(f"Status {status}. Issue {issue or 'none'}."),
        "plan": sentence("Investigation takes a serial that is still failing. This visit does not treat."),
    }
    return save_record(ws, record, soap, fleet=fleet)


def cmd_treat(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial)
    group = strip_arg(args.group)
    action = strip_arg(args.action) or "add"
    if not serial or not serial.isalnum():
        print('{"error": "treat needs a chassis serial"}', file=sys.stderr)
        return 1
    if not group or len(group) > 128:
        print('{"error": "treat needs a static group name"}', file=sys.stderr)
        return 1
    if action not in ("add", "remove"):
        print('{"error": "action must be add or remove"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(240)
    listed, list_err = optional("jamf_list_computer_groups", {"name": group, "static_only": True}, budget)
    if list_err == "unattached":
        print('{"error": "jamf_list_computer_groups is not attached"}', file=sys.stderr)
        return 1
    if list_err:
        print(json.dumps({"error": list_err[:200]}), file=sys.stderr)
        return 1
    group_id = None
    exact = group
    for raw in rows_from(listed or {}):
        name = blank(raw.get("name"))
        smart = raw.get("is_smart")
        if name and name.lower() == group.lower() and smart is not True:
            group_id = blank(raw.get("id"))
            exact = name
            break
    payload = {"confirm": True, "serial": serial, "action": action}
    if group_id:
        payload["group_id"] = group_id
    else:
        payload["group_name"] = exact
    body, err = call("jamf_set_computer_group_membership", payload, budget)
    if err:
        print(json.dumps({"error": err[:200]}), file=sys.stderr)
        return 1
    push_err = None
    push_body = None
    if action == "add":
        push_body, push_err = call("jamf_send_mdm_command", {"command": "BLANK_PUSH", "serial": serial}, budget)
    reply(
        {
            "plane": "operations",
            "treated": True,
            "serial": serial,
            "group": exact,
            "group_id": group_id,
            "action": action,
            "push": None if action != "add" else ("ok" if not push_err else push_err[:120]),
            "stamp": None,
        }
    )
    if push_err:
        print(json.dumps({"warning": f"group updated, blank push failed: {push_err[:160]}"}), file=sys.stderr)
    return 0


def cmd_annotate(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    meta = load_meta(ws)
    if not meta:
        print('{"error": "operations/metadata.json missing"}', file=sys.stderr)
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
    reply({"plane": "operations", "annotated": True, "stamp": stamp, "metadata": META_REL})
    return 0


def main():
    parser = argparse.ArgumentParser(description="Operations visit")
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--workspace", required=True)
    collect.add_argument("--serial", default="")
    collect.add_argument("--name", default="")
    collect.set_defaults(func=cmd_collect)
    treat = sub.add_parser("treat")
    treat.add_argument("--workspace", required=True)
    treat.add_argument("--serial", required=True)
    treat.add_argument("--group", required=True)
    treat.add_argument("--action", default="add")
    treat.set_defaults(func=cmd_treat)
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
