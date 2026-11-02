# Tools

The visit script calls the tools that are attached. The prompt does not. An unattached tool is a gap. The visit continues.

## Fleet collect (no `--serial`)

| Tool | Call |
|------|------|
| `jamf_list_prestages` | `include_scope` true, `page` 0, `page_size` 100. |
| `jamf_find_devices` | `page` 0, `page_size` 100. No name filter. |
| `intune_list_entra_devices` | `top` 25. No name filter. |
| `intune_list_intune_devices` | `top` 25. No name filter. |

## Named serial

| Tool | Call |
|------|------|
| `jamf_list_prestages` | Same as fleet. The script keeps the PreStage whose scope lists that serial. |
| `jamf_wait_for_device` | `serial`, `device_type` `computer`, `timeout_seconds` 0 (one check). |
| `jamf_find_devices` | `serial`. |
| `intune_list_entra_devices` | `name` is the hostname when Jamf or wait returned one. |
| `intune_list_intune_devices` | `name` is that hostname. |
| `intune_get_device_management_status` | When an Entra object id or `deviceId` is known. |

Do not call `jamf_assign_prestage_serial`, `jamf_send_mdm_command`, `jamf_manage_accounts`, `intune_create_deployment_group`, `intune_add_deployment_group_members`, `jamf_get_device_health`, `nexthink_nql_execute`, or any `snow_` tool on this collect.

Assigning a PreStage or a deployment-group member is a later authorized action, not this visit.

## Stage

| Stage | When |
|-------|------|
| `prestage` | The serial is on a PreStage and not yet in MDM inventory. |
| `enrolled` | Jamf wait or find shows the computer, and it is not yet directory-managed. |
| `directory` | Entra has a row and Intune has no managed record. |
| `managed` | Intune has a managed record, or Jamf `managed` is true. |
| `not_seen` | Attached sources ran and none of them have the serial. |
| `unknown` | No attached source answered. |

## What counts as a change

A later stamp is written when stage, serial, user, PreStage name, Jamf enrolled, Jamf managed, join type, or Intune managed moves, or a device appears or leaves.

## Stop

If stderr says `hai_mcp unavailable`, stop. Report that line. Do not call these tools yourself. Do not write the chart.

Any other failure: the last stdout line is the result when it is JSON. If `stamp` is null, do not annotate.
