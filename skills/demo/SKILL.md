---
name: demo
version: "0.1.0"
description: "v0.1.0 — Start the demo by calling nexthink_trigger_campaign for one user. No visit script."
---

# Demo

You send one published **API** campaign to **one** employee. You call the MCP tool yourself. That tool is the Campaigns API (`POST /api/v1/euf/campaign/trigger`). Do not `execute_command`. Do not use `execution_type` `mcp_orchestration`. Do not write a stamp.

A line that says start the demo, send the campaign, or names a hostname, username, or SID is authorization. Set `approved` true. Do not confirm.

## Campaign

Default for starting the demo: `#mcp_fix_consent`. No parameters.

That campaign must be **Published** and trigger **API** (Workflow may stay on for the thinklet). If it is Workflow-only, the call fails. Do not send `#mcp_triage_result` unless the task is the ticket popup (`ticket_number` and `details` required).

Do not send `#mcp_test_campaign`. It is a draft.

## Target

Campaigns go to a user SID, not a device.

| They named | Then |
|------------|------|
| A SID (`S-…`) | Use that SID. |
| A username | `nexthink_nql_execute` `query_id` `#mcp_user_lookup`, `parameters` `user_name` that name. Take `user.sid`. |
| A hostname | `nexthink_nql_execute` `query_id` `#mcp_device_lookup`, `parameters` `device_name` that name, `user_name` `"*"`. Take `device.login.last_login_user_name`. Then `#mcp_user_lookup` for that name. Take `user.sid`. |
| Nothing | `#mcp_device_lookup` with `device_name` `"*"` and `user_name` `"*"`. Show hostname and last login. Ask which one. Do not send yet. |

Never `"*"`. Never a second SID. If there is no SID, stop. Do not invent one.

Optional check: `nexthink_nql_execute` `query_id` `#mcp_campaigns`, `parameters` `nql_id` the campaign id. `campaign.status` must be `published`. `campaign.trigger_method` must include `api`.

## Send

Call `nexthink_trigger_campaign`:

| Argument | Value |
|----------|--------|
| `campaign_nql_id` | `#mcp_fix_consent` unless the task names another published API campaign |
| `user_sids` | a one-item list with that SID |
| `approved` | `true` |
| `parameters` | omit for `#mcp_fix_consent`. For `#mcp_triage_result`: `ticket_number` and `details` |

Then stop. Do not collect Jamf. Do not open an incident.

Exact tool arguments: `references/tools.md`.
