# Tools

## The agent, when no endpoint is chosen

Call the list tools that are attached. Do not invent a name filter.

| Tool | Call |
|------|------|
| `jamf_find_devices` | `page` 0, `page_size` 100. No `name`, `serial`, or `username`. |
| `nexthink_nql_execute` | `query_id` `#mcp_device_lookup`, `parameters` `device_name` `"*"`, `user_name` `"*"`. |
| `intune_list_entra_devices` | No name filter, when Intune is attached. |
| `intune_list_intune_devices` | No name filter, when Intune is attached. |

Show hostname, serial or other id, user, and which system. Ask which one.

## The visit script, after one endpoint is chosen

The prompt does not call these on the collect turn. `scripts/visit_investigations.py collect` does.

| Tool | When |
|------|------|
| `jamf_find_devices` | By the chosen serial, hostname, or username. |
| `jamf_get_device` | The matching computer. Sections GENERAL, HARDWARE, USER_AND_LOCATION. |
| `nexthink_nql_execute` | `#mcp_device_lookup` for a hostname. `#mcp_user_lookup` and `#mcp_device_lookup` for a username. Then `#mcp_device_health`, `#mcp_app_crashes` with `binary_name` `"*"`, and `#mcp_device_top_processes` for the device name found. |

`#mcp_device_health` and `#mcp_device_top_processes` take one real device name. Do not pass `"*"` for those.

Do not call `jamf_get_device_health`, `jamf_send_mdm_command`, `nexthink_execute_remote_action`, `nexthink_trigger_workflow`, `nexthink_trigger_campaign`, or any `snow_` tool.
