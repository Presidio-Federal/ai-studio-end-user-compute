#!/usr/bin/env python3
"""Copy EUC demo computers onto euc_operations.

ServiceNow is the asset. The serial is the document id. Jamf, Intune,
and Nexthink add hostname, user, last check-in, OS, and management.
A part is not a document. The script writes the stamp and the SOAP note.

  python3 <skill>/scripts/visit_endpoints.py sync --workspace <file_explorer>
  python3 <skill>/scripts/visit_endpoints.py sync --workspace <file_explorer> --serial SERIAL123456
  python3 <skill>/scripts/visit_endpoints.py ask --workspace <file_explorer>
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

FOLDER = "endpoint-operations"
META_REL = f"{FOLDER}/metadata.json"
INDEX = "euc_operations"
SOURCE_INDEX = "euc_sources"
STAMP_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "endpoint-operations-visit.schema.json"
META_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "endpoint-operations-metadata.schema.json"
SYS_ID = re.compile(r"^[0-9a-f]{32}$", re.I)
REQ = re.compile(r"REQ[0-9]+")
PAGE = 50
ASSET_FIELDS = (
    "sys_id,serial_number,u_order_number,u_parent_serial,model.model_number"
)
COMPUTER_QUERY = "company.name=Disney EUC^u_euc_demo=true^model_category.name=Computer"
PART_QUERY = "company.name=Disney EUC^u_euc_demo=true^u_parent_serialISNOTEMPTY"
OWNED = (
    "serial",
    "request",
    "stage",
    "site",
    "warehouse",
    "target_site",
    "target_warehouse",
    "pid",
    "unit_price",
    "components",
    "hostname",
    "user",
    "os",
    "last_check_in",
    "last_seen",
    "@timestamp",
    "management_state",
    "dex_score",
    "location",
)
MATERIAL = ("request", "site", "warehouse", "hostname", "user", "os", "last_check_in", "management_state", "dex_score")


def strip_arg(value):
    text = "" if value is None else str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1].strip()
    return text


def blank(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return value


def checked_at(now):
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def watch_id(now):
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")


def sentence(text):
    cleaned = " ".join(str(text).replace("{", "(").replace("}", ")").split())
    if len(cleaned) > 399:
        cleaned = cleaned[:398].rstrip() + "."
    return cleaned


def call(tool, args, budget):
    if budget.exhausted():
        return None, "budget exhausted"
    print(f"endpoints call {tool}", file=sys.stderr)
    return visit_common.tool_dict(visit_common.mcp_call(tool, args, retries=1))


def ref_parts(value):
    if isinstance(value, dict):
        sys_id = blank(value.get("sys_id") or value.get("value"))
        name = blank(value.get("display") or value.get("display_value") or value.get("name"))
        if isinstance(sys_id, str) and not SYS_ID.match(sys_id):
            sys_id = None
        if isinstance(name, str) and SYS_ID.match(name):
            sys_id = sys_id or name
            name = None
        return sys_id, name if isinstance(name, str) else None
    text = blank(value)
    if not isinstance(text, str):
        return None, None
    if SYS_ID.match(text):
        return text, None
    return None, text


def cell(value):
    sys_id, name = ref_parts(value)
    return name or sys_id or ""


def bare_request(value):
    match = REQ.search(cell(value))
    return match.group(0) if match else ""


def chassis(value):
    text = cell(value)
    if text and re.fullmatch(r"[A-Za-z0-9]+", text):
        return text
    return ""


def money(value):
    text = cell(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def component_prices(text):
    """Each line is pid|qty|unit_price|description. Zero is a price."""
    prices = {}
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.count("|") < 2:
            continue
        pid, _qty, price_text = [part.strip() for part in line.split("|", 2)]
        price_text = price_text.split("|", 1)[0].strip()
        if not pid:
            continue
        price = money(price_text)
        if price is not None:
            prices[pid] = price
    return prices


def put(doc, field, value):
    if value in (None, "", []):
        return
    doc[field] = value


def snow_page(table, query, fields, offset, budget):
    payload, err = call(
        "snow_query_table",
        {"table": table, "query": query, "fields": fields, "limit": PAGE, "offset": offset},
        budget,
    )
    if err:
        return None, err
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None, "snow rows missing"
    return [row for row in rows if isinstance(row, dict)], None


def snow_all(table, query, fields, budget):
    rows = []
    offset = 0
    while offset < 2000:
        chunk, err = snow_page(table, query, fields, offset, budget)
        if err:
            return None, err
        rows.extend(chunk)
        if len(chunk) < PAGE:
            return rows, None
        offset += PAGE
    return None, "snow page limit reached"


def place(value, table, budget, cache):
    """Name from the request reference. A stockroom city is not a site."""
    sys_id, name = ref_parts(value)
    if name:
        return name, sys_id, None
    if not sys_id:
        return None, None, None
    key = f"{table}:{sys_id}"
    if key in cache:
        return cache[key]
    fields = "name,latitude,longitude" if table == "cmn_location" else "name"
    rows, err = snow_page(table, f"sys_id={sys_id}", fields, 0, budget)
    if err:
        return None, sys_id, err
    found = cell((rows[0] if rows else {}).get("name")) or None
    cache[key] = (found, sys_id, None)
    return found, sys_id, None


def site_geo(sys_id, budget, cache):
    if not sys_id:
        return None, None
    key = f"geo:{sys_id}"
    if key in cache:
        return cache[key]
    rows, err = snow_page("cmn_location", f"sys_id={sys_id}", "latitude,longitude", 0, budget)
    if err:
        return None, err
    row = rows[0] if rows else {}
    lat = money(row.get("latitude"))
    lon = money(row.get("longitude"))
    point = {"lat": lat, "lon": lon} if lat is not None and lon is not None else None
    cache[key] = (point, None)
    return point, None


def orders(numbers, budget):
    found = {}
    cache = {}
    for req in numbers:
        rows, err = snow_page("sc_request", f"number={req}", "number,u_site,u_warehouse", 0, budget)
        if err:
            return None, err
        row = rows[0] if rows else {}
        site, site_id, site_err = place(row.get("u_site"), "cmn_location", budget, cache)
        if site_err:
            return None, site_err
        room, _room_id, room_err = place(row.get("u_warehouse"), "alm_stockroom", budget, cache)
        if room_err:
            return None, room_err
        point, geo_err = site_geo(site_id, budget, cache)
        if geo_err:
            return None, geo_err
        items, item_err = snow_all(
            "sc_req_item",
            f"request.number={req}",
            "number,u_pid,u_components,price",
            budget,
        )
        if item_err:
            return None, item_err
        prices = {}
        units = {}
        for item in items:
            prices.update(component_prices(cell(item.get("u_components"))))
            pid = cell(item.get("u_pid"))
            unit = money(item.get("price"))
            if pid and unit is not None:
                units[pid] = unit
        found[req] = {"site": site, "site_id": site_id, "warehouse": room, "prices": prices, "units": units, "location": point}
    return found, None


def parents_and_parts(budget, serial):
    query = COMPUTER_QUERY
    if serial:
        query = f"{COMPUTER_QUERY}^serial_number={serial}"
    computers, err = snow_all("alm_hardware", query, ASSET_FIELDS, budget)
    if err:
        return None, None, err
    parts, part_err = snow_all("alm_hardware", PART_QUERY, ASSET_FIELDS, budget)
    if part_err:
        return None, None, part_err
    return computers, parts, None


def components_for(parts, prices_for):
    grouped = {}
    for asset in parts:
        serial = chassis(asset.get("serial_number"))
        parent = chassis(asset.get("u_parent_serial"))
        if not serial or not parent or parent == serial:
            continue
        req = bare_request(asset.get("u_order_number"))
        pid = cell(asset.get("model.model_number"))
        prices = (prices_for.get(req) or {}).get("prices") or {}
        entry = {"serial": serial}
        if pid:
            entry["pid"] = pid
        if pid and pid in prices:
            entry["price"] = prices[pid]
        grouped.setdefault(parent, []).append(entry)
    for parent, items in grouped.items():
        grouped[parent] = sorted(items, key=lambda item: item["serial"])
    return grouped


def section(raw, name):
    value = raw.get(name) if isinstance(raw, dict) else None
    return value if isinstance(value, dict) else {}


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
        return [
            {str(headers[i]): item[i] if i < len(item) else None for i in range(len(headers))}
            for item in data
            if isinstance(item, list)
        ]
    return []


def first(*values):
    for value in values:
        text = blank(value)
        if isinstance(text, str) and text:
            return text
    return None


def jamf_of(raw):
    general = section(raw, "general")
    located = section(raw, "userAndLocation")
    hardware = section(raw, "hardware")
    operating = section(raw, "operatingSystem")
    remote = section(general, "remoteManagement")
    serial = first(hardware.get("serialNumber"), raw.get("serial"), general.get("serialNumber"))
    managed = remote.get("managed")
    if managed is None:
        managed = general.get("managed", raw.get("managed"))
    if isinstance(managed, str):
        managed = managed.strip().lower() == "true"
    if not isinstance(managed, bool):
        managed = None
    return {
        "id": first(raw.get("id"), general.get("id")),
        "serial": serial,
        "hostname": first(general.get("name"), raw.get("name")),
        "user": first(located.get("username"), located.get("realname"), raw.get("username")),
        "os": first(operating.get("version"), operating.get("name"), general.get("osVersion")),
        "last_check_in": first(general.get("lastContactTime"), raw.get("lastContactTime")),
        "managed": managed,
    }


def pick_jamf(rows, serial):
    matched = [jamf_of(raw) for raw in rows if jamf_of(raw).get("serial") == serial]
    if not matched:
        return None
    checked = [row for row in matched if row.get("managed") is True and row.get("last_check_in")]
    if not checked:
        checked = [row for row in matched if row.get("last_check_in")]
    checked = checked or matched
    checked.sort(key=lambda row: row.get("last_check_in") or "")
    return checked[-1]


def nql_value(row, *names):
    if not isinstance(row, dict):
        return None
    folded = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        text = blank(folded.get(name.lower()))
        if isinstance(text, str) and text:
            return text
    return None


def dex_score_from(rows):
    for row in rows:
        score = nql_value(row, "dex_score", "dex.score", "score")
        if score:
            return score
    return None


def enrich(serial, budget):
    """Hostname, user, OS, check-in, management, and DEX score. These do not set site or request."""
    facts = {"feeds": []}
    gaps = []
    found, err = call("jamf_find_devices", {"serial": serial, "page": 0, "page_size": 25}, budget)
    if err:
        if not visit_common.tool_missing(err):
            gaps.append("jamf")
    else:
        chosen = pick_jamf(rows_from(found), serial)
        if chosen and chosen.get("id"):
            detail, detail_err = call(
                "jamf_get_device",
                {
                    "computer_id": str(chosen["id"]),
                    "sections": ["GENERAL", "HARDWARE", "OPERATING_SYSTEM", "USER_AND_LOCATION"],
                },
                budget,
            )
            if not detail_err:
                detailed = rows_from(detail)
                if detailed:
                    chosen = pick_jamf(detailed, serial) or jamf_of(detailed[0])
            facts["feeds"].append("Jamf")
            for field in ("hostname", "user", "os", "last_check_in"):
                if chosen and chosen.get(field):
                    facts[field] = chosen[field]
            if chosen and isinstance(chosen.get("managed"), bool):
                facts["managed"] = chosen["managed"]
    host = facts.get("hostname")
    if host:
        managed, intune_err = call("intune_list_intune_devices", {"name": host, "top": 25}, budget)
        if intune_err:
            if not visit_common.tool_missing(intune_err):
                gaps.append("intune")
        else:
            for raw in rows_from(managed):
                name = first(raw.get("device_name"), raw.get("deviceName"), raw.get("name"))
                if not name or name.lower() != host.lower():
                    continue
                facts["feeds"].append("Intune")
                facts["managed"] = True
                if not facts.get("os"):
                    facts["os"] = first(raw.get("operating_system"), raw.get("operatingSystem"))
                if not facts.get("last_check_in"):
                    facts["last_check_in"] = first(raw.get("last_check_in"), raw.get("lastSyncDateTime"))
                break
        payload, nql_err = call(
            "nexthink_nql_execute",
            {"query_id": "#mcp_device_lookup", "parameters": {"device_name": host, "user_name": "*"}},
            budget,
        )
        if nql_err:
            if not visit_common.tool_missing(nql_err):
                gaps.append("nexthink")
        elif nql_rows(payload) and "Nexthink" not in facts["feeds"]:
            facts["feeds"].append("Nexthink")
        vitals, vitals_err = call(
            "nexthink_nql_execute",
            {"query_id": "#mcp_device_vitals", "parameters": {"device_name": host}},
            budget,
        )
        if vitals_err:
            if not visit_common.tool_missing(vitals_err) and "nexthink" not in gaps:
                gaps.append("nexthink")
        else:
            rows = nql_rows(vitals)
            if rows and "Nexthink" not in facts["feeds"]:
                facts["feeds"].append("Nexthink")
            score = dex_score_from(rows)
            if score:
                facts["dex_score"] = score
    if "managed" in facts:
        facts["management_state"] = "managed" if facts["managed"] else "unmanaged"
    facts["gaps"] = gaps
    return facts


def documents(computers, parts, order_rows):
    prices_for = order_rows
    grouped = components_for(parts, prices_for)
    docs = []
    seen = set()
    for asset in computers:
        serial = chassis(asset.get("serial_number"))
        parent = chassis(asset.get("u_parent_serial"))
        req = bare_request(asset.get("u_order_number"))
        if not serial or serial in seen or parent:
            continue
        seen.add(serial)
        order = order_rows.get(req) or {}
        doc = {"serial": serial, "stage": "in_service"}
        put(doc, "request", req)
        put(doc, "site", order.get("site"))
        put(doc, "target_site", order.get("site"))
        put(doc, "warehouse", order.get("warehouse"))
        put(doc, "target_warehouse", order.get("warehouse"))
        if order.get("location"):
            doc["location"] = order["location"]
        pid = cell(asset.get("model.model_number"))
        put(doc, "pid", pid)
        units = order.get("units") or {}
        if pid and pid in units:
            doc["unit_price"] = units[pid]
        children = grouped.get(serial) or []
        if children:
            doc["components"] = children
        docs.append(doc)
    docs.sort(key=lambda doc: doc["serial"])
    return docs


def apply_facts(doc, facts):
    for field in ("hostname", "user", "os", "last_check_in", "management_state", "dex_score"):
        put(doc, field, facts.get(field))
    if facts.get("last_check_in"):
        doc["last_seen"] = facts["last_check_in"]
        doc["@timestamp"] = facts["last_check_in"]
    return doc


def elastic_hits(index, serials, budget):
    found = {}
    for start in range(0, len(serials), 100):
        chunk = [serial for serial in serials[start:start + 100] if serial]
        if not chunk:
            continue
        body, err = call(
            "elasticsearch_search",
            {"index": index, "query": {"ids": {"values": chunk}}, "size": len(chunk)},
            budget,
        )
        if err or not isinstance(body, dict):
            return None, err or "elastic search failed"
        for hit in body.get("hits") or []:
            if not isinstance(hit, dict):
                continue
            source = hit.get("source") if isinstance(hit.get("source"), dict) else {}
            serial = hit.get("id") or source.get("serial")
            if serial:
                found[str(serial)] = source
    return found, None


def same_clock(left, right):
    return str(left or "")[:19] == str(right or "")[:19]


def same_place(left, right):
    if not isinstance(left, dict) or not isinstance(right, dict):
        return left == right
    try:
        return round(float(left["lat"]), 4) == round(float(right["lat"]), 4) and round(float(left["lon"]), 4) == round(float(right["lon"]), 4)
    except (KeyError, TypeError, ValueError):
        return False


def packed(items):
    rows = []
    for item in items or []:
        if isinstance(item, dict):
            rows.append({key: item.get(key) for key in ("serial", "pid", "price") if key in item})
    return sorted(rows, key=lambda item: item.get("serial") or "")


def differs(doc, source):
    source = source or {}
    for field in OWNED:
        wanted = doc.get(field)
        if wanted in (None, "", []):
            continue
        have = source.get(field)
        if field in ("@timestamp", "last_seen", "last_check_in"):
            if not same_clock(wanted, have):
                return True
            continue
        if field == "location":
            if not same_place(wanted, have):
                return True
            continue
        if field == "components":
            if packed(wanted) != packed(have if isinstance(have, list) else []):
                return True
            continue
        if wanted != have:
            return True
    return False


def write_operations(docs, budget):
    serials = [doc["serial"] for doc in docs]
    current, err = elastic_hits(INDEX, serials, budget)
    if err:
        return None, None, err
    missing = [doc for doc in docs if doc["serial"] not in current]
    changed = [doc for doc in docs if doc["serial"] in current and differs(doc, current[doc["serial"]])]
    failed = []
    written = []
    if missing:
        body, bulk_err = call(
            "elasticsearch_bulk",
            {"items": [{"index": INDEX, "id": doc["serial"], "doc": doc} for doc in missing]},
            budget,
        )
        if bulk_err or not isinstance(body, dict):
            return written, [doc["serial"] for doc in missing], bulk_err or "elastic bulk failed"
        by_id = {doc["serial"]: doc for doc in missing}
        for item in body.get("items") or []:
            if not isinstance(item, dict):
                continue
            serial = str(item.get("id") or "")
            if item.get("ok") is False or serial not in by_id:
                if serial:
                    failed.append(serial)
                continue
            written.append(serial)
        failed.extend(serial for serial in by_id if serial not in written and serial not in failed)
    for doc in changed:
        _body, update_err = call(
            "elasticsearch_update",
            {"index": INDEX, "id": doc["serial"], "doc": doc},
            budget,
        )
        if update_err:
            failed.append(doc["serial"])
        else:
            written.append(doc["serial"])
    return written, failed, None


def write_sources(docs, facts_for, written, budget):
    wanted = {}
    for doc in docs:
        if doc["serial"] not in written:
            continue
        names = ["ServiceNow"]
        for name in (facts_for.get(doc["serial"]) or {}).get("feeds") or []:
            if name not in names:
                names.append(name)
        wanted[doc["serial"]] = names
    current, err = elastic_hits(SOURCE_INDEX, list(wanted), budget)
    if err:
        return err
    for serial, names in wanted.items():
        have = current.get(serial) or {}
        existing = have.get("sources") if isinstance(have.get("sources"), list) else []
        if serial not in current:
            _body, update_err = call(
                "elasticsearch_update",
                {"index": SOURCE_INDEX, "id": serial, "doc": {"sources": names}},
                budget,
            )
            if update_err:
                return update_err
            continue
        for name in names:
            if name in existing:
                continue
            _body, append_err = call(
                "elasticsearch_append",
                {"index": SOURCE_INDEX, "id": serial, "field": "sources", "value": name},
                budget,
            )
            if append_err:
                return append_err
            existing.append(name)
    return None


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
    print(f"endpoints workspace={resolved}", file=sys.stderr)
    return resolved


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def stamp_path(ws, now):
    moment = now
    for _ in range(5):
        ident = watch_id(moment)
        path = Path(ws) / FOLDER / f"{ident}.json"
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
        current = visit_common.load_json(ws, f"{FOLDER}/{prior_id}.json")
        if not isinstance(current, dict):
            return None, None
        guard += 1
    chain.reverse()
    estate = {}
    for stamp in chain:
        for row in stamp.get("devices") or []:
            if isinstance(row, dict) and row.get("serial"):
                estate[row["serial"]] = row
    return estate, chain[-1] if chain else None


def show(value):
    if value is None:
        return ""
    return str(value)


def row_view(doc, facts):
    return {
        "serial": doc["serial"],
        "request": doc.get("request"),
        "site": doc.get("site"),
        "warehouse": doc.get("warehouse"),
        "hostname": doc.get("hostname"),
        "user": doc.get("user"),
        "os": doc.get("os"),
        "last_check_in": doc.get("last_check_in"),
        "management_state": doc.get("management_state"),
        "dex_score": doc.get("dex_score"),
        "sources": ["ServiceNow"] + [name for name in facts.get("feeds") or [] if name != "ServiceNow"],
    }


def metadata(now, **fields):
    body = {
        "keys": [],
        "schema": "endpoint-operations-metadata/v1",
        "updated_at": checked_at(now),
        "source_agent": "endpoint-pipeline",
        "evidence_ref": fields.get("evidence_ref"),
        "last_visit_id": fields.get("last_visit_id"),
        "last_collected_at": fields.get("last_collected_at"),
        "baseline_ref": fields.get("baseline_ref"),
        "status": fields["status"],
        "coverage": fields["coverage"],
        "delta": fields["delta"],
        "devices": fields["devices"],
        "written": fields["written"],
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
            devices=(meta or {}).get("devices") or 0,
            written=0,
            subjective="Copy EUC demo computers onto euc_operations.",
            objective=sentence(f"The copy stopped. {reason}."),
            assessment="Nothing was written. The prior stamp stands.",
            plan="Run the copy again after the source answers.",
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    save_meta(ws, body)
    reply({"plane": "endpoint-operations", "status": "unknown", "error": reason[:300], "stamp": body["evidence_ref"]})
    return 1


def emit(view, note):
    keys = [f"device:{view['serial']}"]
    if view.get("request"):
        keys.append(f"request:{view['request']}")
    if view.get("site"):
        keys.append(f"site:{view['site']}")
    if view.get("warehouse"):
        keys.append(f"warehouse:{view['warehouse']}")
    body = {
        "keys": keys,
        "serial": view["serial"],
        "request": view["request"],
        "site": view.get("site"),
        "warehouse": view.get("warehouse"),
        "hostname": view.get("hostname"),
        "user": view.get("user"),
        "os": view.get("os"),
        "last_check_in": view.get("last_check_in"),
        "management_state": view.get("management_state"),
        "dex_score": view.get("dex_score"),
        "sources": view.get("sources") or ["ServiceNow"],
        "note": note[:200],
    }
    return body


def cmd_sync(args):
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
    computers, parts, err = parents_and_parts(budget, serial)
    if err:
        return fail(ws, meta, now, err)
    numbers = []
    for asset in computers + parts:
        req = bare_request(asset.get("u_order_number"))
        if req and req not in numbers:
            numbers.append(req)
    order_rows, order_err = orders(numbers, budget)
    if order_err:
        return fail(ws, meta, now, order_err)
    docs = documents(computers, parts, order_rows)
    facts_for = {}
    gaps = []
    for doc in docs:
        facts = enrich(doc["serial"], budget)
        facts_for[doc["serial"]] = facts
        gaps.extend(facts.get("gaps") or [])
        apply_facts(doc, facts)
    written, failed, write_err = write_operations(docs, budget)
    if write_err:
        return fail(ws, meta, now, write_err)
    source_err = write_sources(docs, facts_for, set(written), budget)
    if source_err:
        return fail(ws, meta, now, source_err)
    views = {doc["serial"]: row_view(doc, facts_for.get(doc["serial"]) or {}) for doc in docs}
    changed_serials = []
    changes = []
    for ident, view in views.items():
        old = folded.get(ident)
        if old is None or ident in written:
            if old is None or any(show(old.get(field)) != show(view.get(field)) for field in MATERIAL):
                changed_serials.append(ident)
                if old is not None:
                    for field in MATERIAL:
                        if show(old.get(field)) != show(view.get(field)):
                            changes.append(
                                {
                                    "id": ident,
                                    "field": field,
                                    "prior": show(old.get(field))[:80],
                                    "current": show(view.get(field))[:80],
                                }
                            )
    changes = changes[:40]
    first = prior is None
    no_motion = (not first) and (not changed_serials) and (not failed)
    coverage = "partial" if gaps or failed else "complete"
    status = "degraded" if failed else "ok"
    rel = (meta or {}).get("evidence_ref")
    if no_motion:
        delta = "unchanged"
        collected = checked_at(now) if coverage == "complete" else (meta or {}).get("last_collected_at")
        base_ref = (meta or {}).get("baseline_ref")
        last_visit = (meta or {}).get("last_visit_id")
        path = None
    else:
        delta = "first" if first else "changed"
        ident, path = stamp_path(ws, now)
        if ident is None:
            return 1
        rel = f"{FOLDER}/{ident}.json"
        kept = []
        if first:
            for doc in docs:
                kept.append(emit(views[doc["serial"]], "Baseline."))
            notes = "Baseline."
            unchanged = 0
            prior_watch = None
            base_ref = None
        else:
            for ident_row in changed_serials:
                kept.append(emit(views[ident_row], "Changed."))
            notes = "Changed."
            unchanged = len([doc for doc in docs if doc["serial"] not in changed_serials])
            prior_watch = prior.get("watch_id")
            base_ref = (meta or {}).get("baseline_ref") or (meta or {}).get("evidence_ref")
        stamp = {
            "keys": sorted({key for row in kept for key in row["keys"]}),
            "schema": "endpoint-operations/v1",
            "source": "endpoint-operations",
            "watch_id": ident,
            "checked_at": checked_at(now),
            "ok": status == "ok",
            "status": status,
            "headline": sentence(f"{len(docs)} computers. {len(written)} written to {INDEX}."),
            "coverage": coverage,
            "baseline_ref": base_ref,
            "vs_prior": {"prior_watch_id": prior_watch, "delta": delta, "changed": changes},
            "devices": kept,
            "unchanged": unchanged,
            "written": len(written),
            "failed": failed,
            "notes": notes,
            "scope": serial or None,
        }
        if first:
            base_ref = rel
        try:
            visit_common.validate(stamp, STAMP_SCHEMA)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
            return 1
        write_json(path, stamp)
        collected = checked_at(now) if coverage == "complete" else (meta or {}).get("last_collected_at")
        last_visit = ident
    objective = sentence(
        f"{len(docs)} computers in scope. {len(written)} written. {len(failed)} failed. Proof {rel}."
    )
    assessment = "The endpoint copy matches ServiceNow." if not failed else "Some serials were not written."
    if gaps:
        assessment = sentence(assessment + " A feed did not answer.")
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
            devices=len(docs),
            written=len(written),
            subjective="Copy EUC demo computers onto euc_operations." if not serial else f"Copy serial {serial} onto euc_operations.",
            objective=objective,
            assessment=sentence(assessment),
            plan="The next copy writes a serial only when the source and the document differ.",
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)[:500]}), file=sys.stderr)
        return 1
    save_meta(ws, body)
    reply(
        {
            "plane": "endpoint-operations",
            "status": status,
            "coverage": coverage,
            "stamp": body["evidence_ref"],
            "metadata": META_REL,
            "delta": delta,
            "devices": len(docs),
            "written": len(written),
            "failed": failed,
            "quiet": no_motion,
            "index": INDEX,
        }
    )
    return 0 if not failed else 1


def cmd_ask(args):
    ws = resolve_workspace(args.workspace)
    if ws is None:
        return 1
    serial = strip_arg(args.serial) if args.serial else ""
    if serial and not serial.isalnum():
        print('{"error": "serial must be letters and digits"}', file=sys.stderr)
        return 1
    budget = visit_common.Budget(60)
    if serial:
        query = {"ids": {"values": [serial]}}
        size = 1
    else:
        query = {"term": {"stage": "in_service"}}
        size = 20
    body, err = call("elasticsearch_search", {"index": INDEX, "query": query, "size": size}, budget)
    if err or not isinstance(body, dict):
        print(json.dumps({"error": err or "elastic search failed"}), file=sys.stderr)
        return 1
    rows = []
    for hit in body.get("hits") or []:
        if not isinstance(hit, dict):
            continue
        source = hit.get("source") if isinstance(hit.get("source"), dict) else {}
        rows.append(
            {
                "serial": hit.get("id") or source.get("serial"),
                "request": source.get("request"),
                "site": source.get("site"),
                "warehouse": source.get("warehouse"),
                "hostname": source.get("hostname"),
                "dex_score": source.get("dex_score"),
                "stage": source.get("stage"),
            }
        )
    reply({"plane": "endpoint-operations", "status": "ok", "index": INDEX, "devices": rows})
    return 0


def main():
    parser = argparse.ArgumentParser(description="Endpoint operations copy")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync")
    sync.add_argument("--workspace", required=True)
    sync.add_argument("--serial", default="")
    sync.set_defaults(func=cmd_sync)
    ask = sub.add_parser("ask")
    ask.add_argument("--workspace", required=True)
    ask.add_argument("--serial", default="")
    ask.set_defaults(func=cmd_ask)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
