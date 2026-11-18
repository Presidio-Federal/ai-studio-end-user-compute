---
name: endpoint-pipeline
version: "1.0.0"
description: "v1.0.0 — Copy EUC demo computers onto euc_operations. The serial is the document id."
---

# Endpoint pipeline

`euc_operations` is the operations record. The document id is the serial. A computer and a network chassis share that index. This skill writes the computer. It does not create an index and it does not delete `euc_asn`, `euc_warehouse`, `euc_dispatch`, or `euc_deployment`.

ServiceNow is the asset. The estate is `alm_hardware` for company Disney EUC, `u_euc_demo` true, and model category Computer. A serial with `u_parent_serial` is a part. It is not a document and it is not an `euc_sources` document. The parent lists each part in `components` with the child serial, the part number, and the unit price. The unit price is the third field of `u_components`. Zero stays.

`request` is `u_order_number`. `site` and `target_site` are the request `u_site`. `warehouse` and `target_warehouse` are the request `u_warehouse`. `location` is that site's coordinates when both exist. Do not take the site from a warehouse city, a stockroom, or a guessed address.

`stage` is `in_service`. The first copy of missing serials is one `elasticsearch_bulk`. A later copy uses `elasticsearch_update` only when the source and the document differ. Fields left out of the update stay. Jamf and Intune supply hostname, user, last check-in, OS, and management state. Nexthink is recorded when the hostname lookup returns a row. Those feeds do not replace the serial, the request, the site, or the warehouse. A feed that names the serial is added on `euc_sources`. The other names stay.

A question reads `euc_operations`. A sync copies what ServiceNow already has. It does not enroll a device, ship one, or install one.

The script reads the last stamp in `endpoint-operations` before it writes. It writes the stamp and rewrites the SOAP note. A quiet copy writes no stamp.

## Hard boundaries

Only these tools, and only from `scripts/visit_endpoints.py`: `snow_query_table`, `jamf_find_devices`, `jamf_get_device`, `intune_list_intune_devices`, `nexthink_nql_execute`, `elasticsearch_search`, `elasticsearch_bulk`, `elasticsearch_update`, `elasticsearch_append`. The script calls them through `visit_common.mcp_call`.

Do not call `snow_update_asset`, `snow_upsert_asset`, `jamf_send_mdm_command`, `jamf_assign_prestage_serial`, or any Intune write. Do not create an index. Do not delete a document.

## Files

Use exactly: `references/watch.md`, `references/tools.md`, `references/workspace-contract.md`, `schemas/endpoint-operations-metadata.schema.json`, `schemas/endpoint-operations-visit.schema.json`, `examples/endpoint-operations-metadata.example.json`, `examples/endpoint-operations-visit.example.json`.

One `execute_command`, `execution_type: "mcp_orchestration"`. The command is in `references/watch.md`. Reply from the last stdout line.
