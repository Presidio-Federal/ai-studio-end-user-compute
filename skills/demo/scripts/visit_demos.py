#!/usr/bin/env python3
"""Demo visit.

start runs under mcp_orchestration. It resolves one device, starts
workflow #mcp_investigate_on_consent, and writes the demo chart.
That workflow sends #mcp_fix_consent. It does not investigate.
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

STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "demo-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "demo-metadata.schema.json"
META_REL = "demo/metadata.json"
MATERIAL = ("campaign", "request_id", "campaign_status", "user_sid")
SID_RE = re.compile(r"^S-[0-9a-zA-Z-]+$")


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
        path = Path(ws) / "demo" / f"{ident}.json"
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
        current = visit_common.load_json(ws, f"demo/{prior_id}.json")
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
        "schema": "demo-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "demo",
        "evidence_ref": fields.get("evidence_ref"),
        "last_visit_id": fields.get("last_visit_id"),
        "last_collected_at": fields.get("last_collected_at"),
        "baseline_ref": fields.get("baseline_ref"),
        "status": fields["status"],
        "coverage": fields["coverage"],
        "delta": fields["delta"],
        "devices": fields["devices"],
        "campaign": fields.get("campaign"),
        "campaign_status": fields.get("campaign_status"),
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
        rel = f"demo/{ident}.json"
        base_ref = None if first else ((prior or {}).get("baseline_ref") or (meta or {}).get("baseline_ref"))
        stamp = {
            "keys": sorted({key for row in devices for key in row["keys"]}),
            "schema": "demo/v1",
            "source": "demo",
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
            "devices": devices if first else [row for row in devices if str(row["id"]) not in folded or any(c["id"] == str(row["id"]) for c in changes)],
            "unchanged": 0 if first else max(0, len(current_ids & set(folded)) - len({c["id"] for c in changes})),
            "removed": removed,
            "notes": note,
            "scope": scope or devices[0]["id"],
        }
        if not stamp["devices"]:
            stamp["devices"] = devices
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
            campaign=devices[0].get("campaign"),
            campaign_status=devices[0].get("campaign_status"),
            **soap,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    if path is not None:
        if first:
            stamp["baseline_ref"] = None
        write_json(path, stamp)
        print(f"demo wrote {rel}", file=sys.stderr)
    write_json(Path(ws) / META_REL, body)
    reply(
        {
            "plane": "demo",
            "status": body["status"],
            "coverage": body["coverage"],
            "stamp": body["evidence_ref"],
            "metadata": META_REL,
            "delta": delta,
            "devices": len(devices),
            "campaign": devices[0].get("campaign"),
            "campaign_status": devices[0].get("campaign_status"),
            "name": devices[0].get("name"),
            "serial": devices[0].get("serial"),
            "user_sid": devices[0].get("user_sid"),
            "request_id": devices[0].get("request_id"),
            "quiet": no_motion,
            "plan": soap["plan"],
        }
    )
    return 0


def call(tool, args, budget):
    if budget.exhausted():
        return None, "budget exhausted"
    print(f"demo call {tool}", file=sys.stderr)
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


def nql(query_id, parameters, budget):
    payload, err = optional("nexthink_nql_execute", {"query_id": query_id, "parameters": parameters}, budget)
    if err:
        return None, err
    return nql_rows(payload), None


def dicts_from(payload):
    found = []

    def walk(obj, depth):
        if depth > 6 or len(found) > 40:
            return
        if isinstance(obj, dict):
            if any(k in obj for k in ("requestId", "request_id", "userSid", "user_sid")):
                found.append(obj)
            for value in obj.values():
                walk(value, depth + 1)
        elif isinstance(obj, list):
            for item in obj[:40]:
                walk(item, depth + 1)

    walk(payload, 0)
    return found


def campaign_id(raw):
    text = blank(raw) or "#mcp_fix_consent"
    if not text.startswith("#"):
        text = f"#{text}"
    return text


def valid_sid(value):
    text = blank(value)
    if not text:
        return None
    if text == "*" or "," in text or " " in text:
        return None
    if SID_RE.match(text) or text.startswith("S-"):
        return text
    return text if len(text) >= 8 else None


def pick_request(payload):
    for hit in dicts_from(payload or {}):
        ident = cell(hit, "requestId", "request_id")
        if ident:
            return ident
    if isinstance(payload, dict):
        return cell(payload, "requestId", "request_id")
    return None


def lookup_user(name, budget):
    if not blank(name):
        return None, None, "no username"
    rows, err = nql("#mcp_user_lookup", {"user_name": name}, budget)
    if err == "unattached":
        return None, None, err
    if err:
        return None, None, err
    for row in rows or []:
        sid = cell(row, "user.sid", "sid")
        uname = cell(row, "user.name", "name") or name
        if valid_sid(sid):
            return uname, sid, None
    return name, None, None


def lookup_device(name, budget):
    rows, err = nql("#mcp_device_lookup", {"device_name": name, "user_name": "*"}, budget)
    if err:
        return {}, err
    for row in rows or []:
        hostname = cell(row, "device.name", "name") or name
        serial = cell(row, "device.hardware.bios_serial_number", "serial")
        user = cell(row, "device.login.last_login_user_name", "user")
        return {"name": hostname, "serial": serial, "user": user}, None
    return {"name": name}, None


def resolve_target(args, budget):
    hostname = strip_arg(args.name)
    username = strip_arg(args.user)
    serial = strip_arg(args.serial)
    sid = valid_sid(strip_arg(args.sid))
    device = {"name": hostname or "", "serial": serial, "user": username}
    if hostname:
        found, err = lookup_device(hostname, budget)
        if err and err != "unattached":
            print(f"demo device {err[:120]}", file=sys.stderr)
        elif found:
            device["name"] = found.get("name") or hostname
            device["serial"] = found.get("serial") or serial
            device["user"] = found.get("user") or username
            username = device.get("user") or username
    if not sid and username:
        uname, found_sid, err = lookup_user(username, budget)
        if err == "unattached":
            return None, "unattached"
        if err:
            print(f"demo user {err[:120]}", file=sys.stderr)
        device["user"] = uname or username
        sid = found_sid
    device["user_sid"] = sid
    if not sid and not device.get("name"):
        print('{"error": "no device name or user_sid for this endpoint"}', file=sys.stderr)
        return None, "no target"
    device["id"] = device.get("serial") or sid or device.get("name")
    return device, None


WORKFLOW_ID = "#mcp_investigate_on_consent"


def send_workflow(device, budget):
    payload = {"workflow_id": WORKFLOW_ID, "approved": True}
    if device.get("name"):
        payload["device_names"] = [device["name"]]
    elif device.get("user_sid"):
        payload["user_sids"] = [device["user_sid"]]
    else:
        return None, "no device"
    body, err = required("nexthink_trigger_workflow", payload, budget)
    if err:
        return None, err
    return pick_request(body), None


def send_campaign(campaign, sid, args, budget):
    if campaign == "#mcp_test_campaign":
        return None, "draft campaign"
    payload = {
        "campaign_nql_id": campaign,
        "user_sids": [sid],
        "approved": True,
    }
    ticket = strip_arg(args.ticket)
    details = strip_arg(args.details)
    if campaign == "#mcp_triage_result":
        if not ticket or not details:
            return None, "ticket_number and details required"
        payload["parameters"] = {"ticket_number": ticket, "details": details}
    body, err = required("nexthink_trigger_campaign", payload, budget)
    if err:
        return None, err
    return pick_request(body), None


def cmd_start(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    campaign = campaign_id(args.campaign)
    budget = visit_common.Budget(240)
    device, err = resolve_target(args, budget)
    if err == "unattached":
        print(json.dumps({"error": "nexthink_nql_execute is not attached"}), file=sys.stderr)
        return 1
    if device is None:
        return 1
    sid = device.get("user_sid")
    if campaign == "#mcp_fix_consent":
        request_id, send_err = send_workflow(device, budget)
        missing = "nexthink_trigger_workflow is not attached"
    else:
        if not sid:
            print('{"error": "no user_sid for this campaign"}', file=sys.stderr)
            return 1
        request_id, send_err = send_campaign(campaign, sid, args, budget)
        missing = "nexthink_trigger_campaign is not attached"
    if send_err == "unattached":
        status = "unknown"
        coverage = "unavailable"
        campaign_status = "unattached"
        print(json.dumps({"warning": missing}), file=sys.stderr)
    elif send_err:
        status = "degraded"
        coverage = "partial"
        campaign_status = "error"
        print(json.dumps({"warning": send_err[:200]}), file=sys.stderr)
    else:
        status = "ok"
        coverage = "complete"
        campaign_status = "sent"
    device.update(
        {
            "campaign": campaign,
            "request_id": request_id,
            "campaign_status": campaign_status,
            "created": campaign_status == "sent",
        }
    )
    hostname = device.get("name") or device.get("id")
    soap = {
        "subjective": sentence("Start the consent workflow for this demo."),
        "objective": sentence(
            f"{WORKFLOW_ID if campaign == '#mcp_fix_consent' else campaign} {campaign_status} for {hostname}."
            + (f" Request {request_id}." if request_id else "")
        ),
        "assessment": sentence(
            "The workflow sends #mcp_fix_consent. Fix now calls Investigation."
            if campaign == "#mcp_fix_consent" and campaign_status == "sent"
            else (
                "Engage should appear on that session."
                if campaign_status == "sent"
                else f"It was not sent ({campaign_status})."
            )
        ),
        "plan": sentence("The employee answers Fix now. Investigation runs from the workflow. This visit does not investigate."),
    }
    return save_record(
        ws,
        {
            "status": status,
            "coverage": coverage if coverage != "unavailable" else "partial",
            "headline": sentence(f"{campaign} {campaign_status} for {hostname}."),
            "devices": [device],
            "scope": device["id"],
        },
        soap,
    )


def cmd_annotate(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    meta = load_meta(ws)
    if not isinstance(meta, dict):
        print('{"error": "demo/metadata.json missing"}', file=sys.stderr)
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
    reply({"plane": "demo", "annotated": True, "stamp": stamp, "metadata": META_REL})
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("start")
    start.add_argument("--workspace", required=True)
    start.add_argument("--name")
    start.add_argument("--user")
    start.add_argument("--serial")
    start.add_argument("--sid")
    start.add_argument("--campaign", default="#mcp_fix_consent")
    start.add_argument("--ticket")
    start.add_argument("--details")
    start.set_defaults(func=cmd_start)
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
