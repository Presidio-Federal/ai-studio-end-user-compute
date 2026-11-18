# Tools

Call these on the agent. Do not `execute_command`. Do not invent NQL.

| Tool | When |
|------|------|
| `nexthink_nql_execute` | Look up. `query_id` `#mcp_device_lookup` with `device_name` and `user_name`. `query_id` `#mcp_user_lookup` with `user_name`. Optional: `query_id` `#mcp_campaigns` with `nql_id` to confirm published + `api`. |
| `nexthink_trigger_campaign` | Send. `campaign_nql_id`, `user_sids` (one SID), `approved` true. `parameters` only when that campaign has parameter ids. |

Do not call `nexthink_trigger_workflow`, `nexthink_execute_remote_action`, `nexthink_enrich`, or any `snow_`, `jamf_`, or `intune_` tool.

`nexthink_nql_execute` cannot send a campaign. Do not add a saved NQL query for this.
