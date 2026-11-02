# Tools

The visit script calls the tools that are attached. The prompt does not. An unattached tool is a gap. The visit continues.

## Fleet collect (no `--serial` or `--name`)

| Tool | Call |
|------|------|
| `nexthink_nql_execute` | `query_id` `#mcp_dex_watchlist`. No parameters. |
| `intune_list_intune_devices` | `compliance_state` `noncompliant`, `top` 25. |

Do not invent a `query_id`. Parameter keys have no `$`.

## Named device

| Tool | Call |
|------|------|
| `nexthink_nql_execute` | `#mcp_device_lookup` with `device_name` and `user_name` `"*"`, then `#mcp_device_vitals` with that hostname. `--serial` keeps the lookup row whose BIOS serial matches, then vitals on that hostname. Vitals does not take `"*"`. |
| `jamf_find_devices` | By serial or hostname. |
| `jamf_get_device_health` | The matching computer. |
| `intune_list_intune_devices` | `name` is the hostname. |

Do not call `nexthink_execute_remote_action`, `nexthink_trigger_workflow`, `nexthink_trigger_campaign`, `nexthink_enrich`, `jamf_send_mdm_command`, `jamf_list_prestages`, `jamf_assign_prestage_serial`, or any `snow_` tool.

## What the row holds

Experience supplies name, collector UID, BIOS serial, user, last seen, platform, free disk, crash count, DEX score, and custom fields when vitals ran. MDM supplies managed and health severity. Directory/Intune supplies compliance. `device:` is the chassis serial. A hostname is a column.

## What counts as a change

A later stamp is written when issue, serial, user, crash count, free disk, DEX score, compliance, managed, `lifecycle_stage`, or `snow_incident` moves, or a device appears or leaves the failing set.

`last_seen` is stored. A newer last-seen time alone does not open a stamp.

## Issue

| Issue | When |
|-------|------|
| `crashes` | Crash count is above zero. |
| `disk` | Free disk is the reason the device is failing. |
| `experience` | DEX score is under 70, or the watchlist included the device for score. |
| `compliance` | Intune compliance is not compliant. |
| `recorded` | A reading came back and none of those fired. |
| `unread` | An attached source failed. |
| `unknown` | No device row came back. |

## Stop

If stderr says `hai_mcp unavailable`, stop. Report that line. Do not call these tools yourself. Do not write the chart.

Any other failure: the last stdout line is the result when it is JSON. If `stamp` is null, do not annotate.
