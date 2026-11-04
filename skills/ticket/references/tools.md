# Tools

The visit script calls the tools that are attached. The prompt does not. A missing ServiceNow write tool is a halt.

## Open

| Tool | When |
|------|------|
| `snow_find_companies` | `u_euc_demo` true. The EUC company on the hardware asset. Unattached is a gap. |
| `snow_find_assets` | `serial_number` from the investigation stamp. Prefer `u_euc_demo` true. |
| `snow_upsert_asset` | When that serial is not yet an EUC hardware asset. `install_status` `in_use`. `company` from the EUC company find. Comments mark it `EUC_DEMO`. Unattached is a gap. |
| `snow_find_cis` | `serial_number` from the investigation stamp. A hit becomes `cmdb_ci` on the incident. Unattached is a gap. |
| `snow_find_incidents` | Search the hostname, then the serial, `active_only` true, `limit` 25. Reuse a matching active INC. |
| `snow_get_incident` | When the last ticket stamp already has a number, or a find hit needs a state. |
| `snow_create_incident` | When no active matching INC exists. `short_description` starts with `EUC_DEMO`. `work_notes` is the investigation pack, first line `EUC_DEMO`. `description` is SOAP plus that pack. `jamf_evidence` from the stamp columns. `cmdb_ci` from the computer CI. `contact_type` `virtual_agent`. |

Do not call `jamf_`, `intune_`, or `nexthink_` tools. Do not call `snow_update_incident`. Do not call catalog writes. Serial comes from the investigation stamp, which already resolved Jamf `hardware.serialNumber` against Nexthink `device.hardware.bios_serial_number`.

## What counts as a change

A later stamp is written when the INC number, state, or asset tag for that serial moves, or a device appears.

## Stop

If stderr says `hai_mcp unavailable`, stop. Report that line. Do not call these tools yourself. Do not write the chart.

Any other failure: the last stdout line is the result when it is JSON. If `stamp` is null, do not annotate.
