# Tools

## The agent, when no endpoint is chosen

Call the list tools that are attached. Do not invent a name filter.

| Tool | Call |
|------|------|
| `nexthink_nql_execute` | `query_id` `#mcp_device_lookup`, `parameters` `device_name` `"*"`, `user_name` `"*"`. |

Show hostname and last login. Ask which one. Do not run `start`.

## The visit script, after one endpoint is chosen

The prompt does not call these on the start turn. `scripts/visit_demos.py start` does.

| Tool | When |
|------|------|
| `nexthink_nql_execute` | `#mcp_device_lookup` for a hostname. `#mcp_user_lookup` for a username. |
| `nexthink_trigger_workflow` | `approved` true. `workflow_id` `#mcp_investigate_on_consent`. `device_names` is the one hostname. This sends `#mcp_fix_consent`. Do not switch that campaign to API. |
| `nexthink_trigger_campaign` | Only when `--campaign` is an API campaign such as `#mcp_triage_result`. `approved` true. `user_sids` is one SID. Never `"*"`. |

Do not call `nexthink_execute_remote_action`, `nexthink_enrich`, or any `snow_`, `jamf_`, or `intune_` tool.

`nexthink_nql_execute` cannot send a campaign or start a workflow. Do not add a saved NQL query for this.
