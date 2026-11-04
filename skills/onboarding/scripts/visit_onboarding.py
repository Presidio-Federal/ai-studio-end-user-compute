#!/usr/bin/env python3
"""Onboarding visit.

collect runs under mcp_orchestration. It uses attached MDM and directory
tools to record enrollment. A missing tool is a gap. It does not assign
a PreStage, investigate health, or retire.
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

STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "onboarding-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "onboarding-metadata.schema.json"
META_REL = "onboarding/metadata.json"
MATERIAL = (
    "stage",
    "serial",
    "user",
    "jamf_enrolled",
    "jamf_managed",
    "prestage_name",
    "join_type",
    "intune_managed",
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
        path = Path(ws) / "onboarding" / f"{ident}.json"
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
        current = visit_common.load_json(ws, f"onboarding/{prior_id}.json")
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
        "schema": "onboarding-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "onboarding",
        "evidence_ref": fields.get("evidence_ref"),
        "last_visit_id": fields.get("last_visit_id"),
        "last_collected_at": fields.get("last_collected_at"),
        "baseline_ref": fields.get("baseline_ref"),
        "status": fields["status"],
        "coverage": fields["coverage"],
        "delta": fields["delta"],
        "devices": fields["devices"],
        "stage": fields.get("stage"),
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
    body["sources"] = sorted({item for item in sources if item in ("mdm", "directory")})
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
    stage = devices[0].get("stage") if devices else None
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
        rel = f"onboarding/{ident}.json"
        base_ref = None if first else ((prior or {}).get("baseline_ref") or (meta or {}).get("baseline_ref"))
        stamp = {
            "keys": sorted({key for row in devices for key in row["keys"]} | {key for item in removed for key in item["keys"]}),
            "schema": "onboarding/v1",
            "source": "onboarding",
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
            stage=stage,
            **soap,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    if path is not None:
        if first:
            stamp["baseline_ref"] = None
        write_json(path, stamp)
        print(f"onboarding wrote {rel}", file=sys.stderr)
    write_json(Path(ws) / META_REL, body)
    reply(
        {
            "plane": "onboarding",
            "status": body["status"],
            "coverage": body["coverage"],
            "stamp": body["evidence_ref"] if not no_motion else rel,
            "metadata": META_REL,
            "delta": delta,
            "devices": len(devices),
            "stage": stage,
            "quiet": no_motion,
            "plan": soap["plan"],
        }
    )
    return 0


def call(tool, args, budget):
    if budget.exhausted():
        return None, "budget exhausted"
    print(f"onboarding call {tool}", file=sys.stderr)
    return visit_common.tool_dict(visit_common.mcp_call(tool, args, retries=1))


def optional(tool, args, budget):
    body, err = call(tool, args, budget)
    if err and visit_common.tool_missing(err):
        return None, "unattached"
    return body, err


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


def section(raw, name):
    value = raw.get(name) if isinstance(raw, dict) else None
    return value if isinstance(value, dict) else {}


def rows_from(payload):
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, (dict, list)) and data is not payload:
        nested = rows_from(data)
        if nested:
            return nested
    for key in ("devices", "results", "computers", "value", "prestages", "computerPrestages"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            inner = value.get("computer") or value.get("device") or value.get("results")
            if isinstance(inner, list):
                return [item for item in inner if isinstance(item, dict)]
            if isinstance(inner, dict):
                return [inner]
    if payload.get("id") or payload.get("serial") or payload.get("serialNumber"):
        return [payload]
    return []


def jamf_fields(raw):
    general = section(raw, "general")
    hardware = section(raw, "hardware")
    located = section(raw, "userAndLocation")
    remote = section(general, "remoteManagement")
    return {
        "jamf_id": blank(raw.get("id") or general.get("id") or raw.get("computerId")),
        "name": blank(raw.get("name") or general.get("name") or raw.get("device_name")) or "",
        "serial": blank(
            raw.get("serial")
            or hardware.get("serialNumber")
            or general.get("serialNumber")
            or raw.get("serialNumber")
        ),
        "user": blank(raw.get("username") or located.get("username") or raw.get("user") or raw.get("email")),
        "jamf_managed": as_bool(
            raw.get("managed") if raw.get("managed") is not None else remote.get("managed") or general.get("managed")
        ),
    }


def walk_serials(obj, found):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if "serial" in str(key).lower() and isinstance(value, str) and value.strip():
                found.append(value.strip())
            else:
                walk_serials(value, found)
    elif isinstance(obj, list):
        for item in obj:
            walk_serials(item, found)


def empty_row(ident):
    return {
        "id": ident,
        "name": "",
        "serial": None,
        "user": None,
        "jamf_id": None,
        "jamf_enrolled": None,
        "jamf_managed": None,
        "prestage_id": None,
        "prestage_name": None,
        "entra_id": None,
        "join_type": None,
        "intune_id": None,
        "intune_managed": None,
        "stage": "unknown",
        "sources": [],
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


def stage_of(row):
    if row.get("intune_managed") is True or row.get("jamf_managed") is True:
        return "managed"
    if row.get("entra_id") and row.get("intune_managed") is not True:
        return "directory"
    if row.get("jamf_enrolled") is True:
        return "enrolled"
    if row.get("prestage_id") or row.get("prestage_name"):
        return "prestage"
    if row.get("sources"):
        return "not_seen"
    return "unknown"


def cmd_collect(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial)
    if serial and not serial.isalnum():
        print('{"error": "serial must be letters and digits"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(240)
    estate = {}
    attached = []
    errors = []
    gaps = []

    def take(tool, payload_args):
        body, err = optional(tool, payload_args, budget)
        if err == "unattached":
            gaps.append(f"{tool} unattached")
            print(f"onboarding skip {tool} unattached", file=sys.stderr)
            return None
        attached.append(tool)
        if err:
            gaps.append(f"{tool} {err[:80]}")
            errors.append(err)
            print(f"onboarding {tool} error {err[:200]}", file=sys.stderr)
            return None
        n = len(rows_from(body or {}))
        print(f"onboarding {tool} rows {n}", file=sys.stderr)
        return body

    fleet = not serial
    prestages = take("jamf_list_prestages", {"include_scope": True, "page": 0, "page_size": 100})
    prestage_hits = []
    for raw in rows_from(prestages or {}):
        ident = blank(raw.get("id") or raw.get("prestageId"))
        name = blank(raw.get("displayName") or raw.get("name")) or ""
        serials = []
        walk_serials(raw, serials)
        prestage_hits.append({"id": ident, "name": name, "serials": serials})
        if fleet:
            for item in serials[:20]:
                upsert(
                    estate,
                    item,
                    serial=item,
                    prestage_id=ident,
                    prestage_name=name,
                    source="mdm",
                )

    if serial:
        match = next((item for item in prestage_hits if serial in item["serials"]), None)
        if match:
            upsert(
                estate,
                serial,
                serial=serial,
                prestage_id=match["id"],
                prestage_name=match["name"],
                source="mdm",
            )
        waited = take(
            "jamf_wait_for_device",
            {"serial": serial, "device_type": "computer", "timeout_seconds": 0},
        )
        enrolled = as_bool((waited or {}).get("enrolled")) if waited else None
        host = blank((waited or {}).get("name") or (waited or {}).get("device_name"))
        upsert(
            estate,
            serial,
            serial=serial,
            name=host or "",
            jamf_enrolled=enrolled,
            jamf_id=blank((waited or {}).get("id") or (waited or {}).get("computer_id")),
            source="mdm" if waited else None,
        )
        found = take("jamf_find_devices", {"serial": serial, "page": 0, "page_size": 25})
        for raw in rows_from(found or {}):
            fields = jamf_fields(raw)
            host = fields["name"] or host
            upsert(
                estate,
                serial,
                serial=serial,
                name=host or "",
                user=fields["user"],
                jamf_id=fields["jamf_id"],
                jamf_enrolled=True,
                jamf_managed=fields["jamf_managed"],
                source="mdm",
            )
            break
        if host:
            entra = take("intune_list_entra_devices", {"name": host, "top": 25})
            entra_id = None
            device_id = None
            for raw in rows_from(entra or {}):
                entra_id = blank(raw.get("id") or raw.get("objectId"))
                device_id = blank(raw.get("deviceId"))
                upsert(
                    estate,
                    serial,
                    serial=serial,
                    name=blank(raw.get("displayName") or raw.get("name")) or host,
                    entra_id=entra_id,
                    join_type=blank(raw.get("joinType") or raw.get("trustType")),
                    source="directory",
                )
                break
            managed = take("intune_list_intune_devices", {"name": host, "top": 25})
            for raw in rows_from(managed or {}):
                upsert(
                    estate,
                    serial,
                    serial=serial,
                    name=blank(raw.get("deviceName") or raw.get("name")) or host,
                    intune_id=blank(raw.get("id")),
                    intune_managed=True,
                    user=blank(raw.get("userPrincipalName")),
                    source="directory",
                )
                break
            lookup = entra_id or device_id
            if lookup:
                status_payload = take("intune_get_device_management_status", {"device_identifier": lookup})
                if status_payload:
                    found_intune = as_bool(status_payload.get("intune_record_found"))
                    upsert(
                        estate,
                        serial,
                        serial=serial,
                        intune_managed=found_intune,
                        source="directory",
                    )
        if serial not in estate and not any(row.get("serial") == serial for row in estate.values()):
            upsert(estate, serial, serial=serial)
    else:
        found = take("jamf_find_devices", {"page": 0, "page_size": 100})
        for raw in rows_from(found or {})[:40]:
            fields = jamf_fields(raw)
            ident = fields["serial"] or fields["name"]
            if not ident:
                continue
            upsert(
                estate,
                ident,
                name=fields["name"],
                serial=fields["serial"],
                user=fields["user"],
                jamf_id=fields["jamf_id"],
                jamf_enrolled=True,
                jamf_managed=fields["jamf_managed"],
                source="mdm",
            )
        managed = take("intune_list_intune_devices", {"top": 25})
        for raw in rows_from(managed or {})[:25]:
            host = blank(raw.get("deviceName") or raw.get("name")) or ""
            serial_value = blank(raw.get("serialNumber") or raw.get("serial"))
            ident = serial_value or host or blank(raw.get("id"))
            if not ident:
                continue
            upsert(
                estate,
                ident,
                name=host,
                serial=serial_value,
                intune_id=blank(raw.get("id")),
                intune_managed=True,
                user=blank(raw.get("userPrincipalName")),
                source="directory",
            )

    devices = list(estate.values())[:40]
    for row in devices:
        row["stage"] = stage_of(row)
        if not attached:
            row["stage"] = "unknown"
    waiting = {"not_seen", "prestage", "unknown"}
    mdm_rows = [row for row in devices if "mdm" in (row.get("sources") or [])]
    jamf_gap = any(item.startswith("jamf_") for item in gaps)
    status = "unknown" if (not attached or jamf_gap) else "degraded" if any(row["stage"] in waiting for row in devices) else "ok"
    coverage = "partial" if errors or gaps or not attached else "complete"
    stage = devices[0]["stage"] if devices else None
    gap_text = gaps[0] if gaps else ""
    if serial and devices:
        stage = devices[0]["stage"]
        headline = f"{serial} {devices[0].get('name') or 'unnamed'} stage {stage}."
    elif mdm_rows:
        headline = f"{len(mdm_rows)} enrolled or waiting in MDM. Stage {stage}."
    elif jamf_gap:
        headline = f"Jamf unread. {gap_text}."
    elif devices:
        headline = f"{len(devices)} device(s). Stage {stage}."
    else:
        headline = "No enrollment rows in scope."
    if gap_text and "Jamf" not in headline:
        headline = f"{headline} {gap_text}."
    record = {
        "status": status,
        "headline": headline[:400],
        "coverage": coverage,
        "scope": serial or "fleet",
        "devices": devices,
    }
    soap = {
        "subjective": sentence(f"Onboarding check for {serial or 'fleet'}."),
        "objective": sentence(
            f"{len(devices)} in scope, {len(mdm_rows)} MDM. Stage {stage or 'none'}. Coverage {coverage}. {gap_text}".strip()
        ),
        "assessment": sentence(f"Status {status}. Stage {stage or 'none'}." + (f" {gap_text}." if jamf_gap else "")),
        "plan": sentence("Operations starts after enrolled or managed. This visit does not assign a PreStage."),
    }
    return save_record(ws, record, soap, fleet=fleet)


def cmd_assign(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial)
    prestage_name = strip_arg(args.prestage_name)
    prestage_id = strip_arg(args.prestage_id)
    action = strip_arg(args.action) or "assign"
    if not serial or not serial.isalnum():
        print('{"error": "assign needs a chassis serial"}', file=sys.stderr)
        return 1
    if action not in ("assign", "unassign"):
        print('{"error": "action must be assign or unassign"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(240)
    payload = {"serial_number": serial, "action": action}
    if prestage_id:
        payload["prestage_id"] = prestage_id
    elif prestage_name:
        payload["prestage_name"] = prestage_name
    body, err = call("jamf_assign_prestage_serial", payload, budget)
    if err:
        print(json.dumps({"error": err[:200]}), file=sys.stderr)
        return 1
    reply(
        {
            "plane": "onboarding",
            "assigned": action == "assign",
            "serial": serial,
            "prestage_name": prestage_name or None,
            "prestage_id": prestage_id or None,
            "action": action,
            "stamp": None,
        }
    )
    return 0


def cmd_annotate(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    meta = load_meta(ws)
    if not meta:
        print('{"error": "onboarding/metadata.json missing"}', file=sys.stderr)
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
    reply({"plane": "onboarding", "annotated": True, "stamp": stamp, "metadata": META_REL})
    return 0


def main():
    parser = argparse.ArgumentParser(description="Onboarding visit")
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--workspace", required=True)
    collect.add_argument("--serial", default="")
    collect.set_defaults(func=cmd_collect)
    assign = sub.add_parser("assign")
    assign.add_argument("--workspace", required=True)
    assign.add_argument("--serial", required=True)
    assign.add_argument("--prestage-name", default="")
    assign.add_argument("--prestage-id", default="")
    assign.add_argument("--action", default="assign")
    assign.set_defaults(func=cmd_assign)
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
