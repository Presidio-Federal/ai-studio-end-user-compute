# Endpoint updates

These three campaigns do not exist on the instance yet. Create them in
Nexthink. Operations then sends them with `nexthink_trigger_campaign`.
They are **API** campaigns. They are not `#mcp_fix_consent`. Do not add
them to the workflow.

The employee sees them on the logged-in Mac. Operations sends **one**
user SID from the investigation stamp. Never `"*"`.

Parameters on every campaign, exact ids:

- `ticket_number`
- `details`

| NQL id | When Operations sends it | Body |
|--------|--------------------------|------|
| `#mcp_ops_working` | The ticket-authorized visit starts | We are working on {{ticket_number}}. {{details}} |
| `#mcp_ops_update` | A step finishes and the ticket is still open | Update for {{ticket_number}}. {{details}} |
| `#mcp_ops_closed` | The incident is resolved | {{ticket_number}} is resolved. {{details}} |

`nexthink_trigger_campaign` needs `approved` true. If `user_sid` is missing,
do not send. The Screen Sharing session has to be logged in or Engage does
not appear.

Do not edit `#mcp_fix_consent` or `#mcp_triage_result`.

## Create each campaign (repeat three times)

NQL ID cannot change after the first save.

### 1. Open the editor

Campaigns → **Manage campaigns** → **New campaign**

### 2. General — save these, then Save once so the NQL ID sticks

| Campaign | Name | NQL ID (type without `#`) | Trigger | Priority |
|----------|------|---------------------------|---------|----------|
| 1 | `MCP ops working` | `mcp_ops_working` | Check **API**. Do **not** check Workflow. Do **not** check Schedule. | **Urgent** |
| 2 | `MCP ops update` | `mcp_ops_update` | Check **API**. Do **not** check Workflow. Do **not** check Schedule. | **Urgent** |
| 3 | `MCP ops closed` | `mcp_ops_closed` | Check **API**. Do **not** check Workflow. Do **not** check Schedule. | **Urgent** |

Nexthink stores `#mcp_ops_working`, `#mcp_ops_update`, `#mcp_ops_closed`.

### 3. Parameters — exact ids

Add two parameters on each campaign:

- `ticket_number`
- `details`

### 4. One question

One question only. Question text is the body for that row in the table
above, including the `{{ticket_number}}` and `{{details}}` placeholders.
Do not retype those names.

### 5. One answer

Fill **two boxes**. Leave everything else.

| Field | Value |
|-------|--------|
| Choice text | `OK` |
| Choice label | `ok` |

**Do not touch**

- Do **not** click **Add new question**. One question only.
- Do **not** click **Add choice**. One OK only.
- Leave **Advanced settings** off.
- Leave **Add comment** off.
- Do **not** click **Cancel**.
- Do **not** edit the green `{{ticket_number}}` / `{{details}}` text.

### 6. Publish

1. **Save campaign** (blue button).
2. **Publish** on the top bar. Save is not Publish. Status must say **Published**.

Do not add these campaigns to the workflow. Operations `notify` sends them.

## Studio

On Operations, attach `nexthink_trigger_campaign`. Collect still must not
send a campaign. Ticket-authorized visits call `notify` under
`execution_type: "mcp_orchestration"`.
