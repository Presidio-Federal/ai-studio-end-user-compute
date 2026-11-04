# Tools

The visit script calls the tools that are attached. The prompt does not. An unattached tool is a gap. The visit continues.

## Fleet collect (no `--serial`)

| Tool | Call |
|------|------|
| `jamf_list_prestages` | `include_scope` true, `page` 0, `page_size` 100. |
| `jamf_find_devices` | `page` 0, `page_size` 100. No name filter. |
| `intune_list_intune_devices` | `top` 25. No name filter. Intune managed records only. Do not list the Entra directory on a fleet collect. |

## Named serial

| Tool | Call |
|------|------|
| `jamf_list_prestages` | Same as fleet. The script keeps the PreStage whose scope lists that serial. |
| `jamf_wait_for_device` | `serial`, `device_type` `computer`, `timeout_seconds` 0 (one check). |
| `jamf_find_devices` | `serial`. |
| `intune_list_entra_devices` | `name` is the hostname when Jamf or wait returned one. |
| `intune_list_intune_devices` | `name` is that hostname. |
| `intune_get_device_management_status` | When an Entra object id or `deviceId` is known. |

Do not call `jamf_assign_prestage_serial`, `jamf_send_mdm_command`, `jamf_manage_accounts`, `jamf_list_computer_groups`, `jamf_set_computer_group_membership`, `jamf_api_get`, `jamf_api_post`, `jamf_api_put`, `jamf_api_delete`, `intune_create_deployment_group`, `intune_add_deployment_group_members`, `jamf_get_device_health`, `nexthink_nql_execute`, or any `snow_` tool on this collect.

## Assign (only when authorized)

The person must name a serial and authorize the PreStage write. Collect does not assign.

| Tool | Call |
|------|------|
| `jamf_assign_prestage_serial` | `serial_number`, optional `prestage_name` or `prestage_id`. `action` `assign` or `unassign`. Omit the prestage only when one exists. |

Do not call `jamf_api_get`, `jamf_api_post`, `jamf_api_put`, or `jamf_api_delete`. Those need a path this skill does not supply.

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
