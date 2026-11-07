# Campaign API intake

The first campaign does **not** wait for ServiceNow. The employee already
answered. A second campaign is how they see the ticket number.

Flow:

1. Campaign `#mcp_fix_consent` asks Fix now / Later.
2. On `fix_now`, the workflow POSTs Investigation (Async).
3. Investigation collects, Ticket opens the INC, Investigation `notify`
   sends campaign `#mcp_triage_result` with `ticket_number` and `details`.
4. Engage shows that second popup.

Do not edit `#mcp_fix_consent` to accept INC fields. That campaign is only
consent.

## Studio

On the Investigation agent: Channels → API → Generate API Key. Use **Async**.
The key selects this agent. Sync waits for the whole visit and will time out
the Nexthink thinklet.

Attach Ticket as a **subagent** of Investigation. Ticket is the only writer of
`tickets/`. Investigation does not call `snow_`. Investigation `notify` may
call `nexthink_trigger_campaign`.

```text
POST https://studio.presidio.ai/agents/api/v1/channels/agents
X-API-Key: <key from this agent>
Content-Type: application/json
```

```json
{
  "mode": "api",
  "humanPrompt": "Investigate hostname mac-example. Serial SERIAL123456. The employee answered Fix now. Campaign authorized this visit."
}
```

The hostname or serial in `humanPrompt` is the chosen endpoint. Collect with
`--name` or `--serial`. Do not list devices. Do not confirm.

Then start Ticket with one line: open the incident from the investigations
SOAP. Do not paste the device row. Ticket copies the stamp onto the INC with
an `EUC_DEMO` marker. Read `tickets/metadata.json`. Then `notify` under
`execution_type: "mcp_orchestration"`.

```text
python3 <copied script path> notify --workspace <copied file_explorer directory>
```

`notify` reads the INC from `tickets/metadata.json` and sends `#mcp_triage_result`
to **one** user SID: the `user_sid` on that investigation stamp. That is the
same employee who clicked Fix now. Parameters: `ticket_number`, `details`.
It does not target a device list. It does not pass `"*"`. If the stamp has
no SID, it does not send the campaign. Your last stdout line is still the
ticket number for the API caller.

A later ServiceNow Flow may POST Operations. That contract is `ticket`
`references/snow-api.md`. This agent does not treat.

## Nexthink (you configure)

### Campaign 1 — already built: `#mcp_fix_consent`

Used **in workflows**. One question. Confirmed answer NQL id is `fix_now`
(not the button label `Fix now`). Later does not call Studio. Do not add
ticket parameters to this campaign.

### Campaign 2 — create: `#mcp_triage_result`

This is the ticket popup. Investigation sends it. It is not campaign 1
waiting.

1. Campaigns → New campaign.
2. Name: `mcp_triage_result`. NQL id must be `mcp_triage_result` (shown as
   `#mcp_triage_result`).
3. Trigger: **API**. Check API. Publish. Do not use “in workflows” unless you
   also keep API on. `nexthink_trigger_campaign` needs API targeting. The
   script targets one user SID, not the whole tenant.
4. Priority: urgent (so it shows on the Mac).
5. Parameters (exact ids):
   - `ticket_number`
   - `details`
6. One message or one question. Body:

```text
Your ticket {{ticket_number}} is open. {{details}}
```

7. One answer, for example OK, NQL id `ok`.
8. Publish.

### Workflow `#mcp_investigate_on_consent`

Keep:

1. Campaign thinklet `#mcp_fix_consent` (wait for the answer).
2. Condition: that campaign → `decision` → Is → `fix_now`.
3. Service/API: POST Studio Investigation, Async, `humanPrompt` with device
   name or serial.

Do **not** add a Wait thinklet unless you have a Wait callback. Studio Async
already returned HTTP. Investigation telling the user is campaign 2, sent by
`notify`, not a Wait listener.

Do not call Studio when the employee says Later. Do not put the API key in
the campaign question text.
