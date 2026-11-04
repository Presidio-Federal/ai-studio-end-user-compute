# Campaign API intake

Nexthink detects a bad endpoint and shows a campaign. Only a confirmed-problem
answer calls this agent. The campaign does not collect. This skill does not
send the campaign. Ticket opens the incident from the SOAP this visit writes.

## Studio

On the Investigation agent: Channels → API → Generate API Key. Use **Async**.
The key selects this agent. Sync waits for the whole visit and will time out
the Nexthink thinklet.

Attach Ticket as a **subagent** of Investigation. Ticket is the only writer of
`tickets/`. Investigation does not call `snow_`.

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
an `EUC_DEMO` marker. Read `tickets/metadata.json`. Then `notify`.
The last stdout line is the ticket number and concise details. That is your
reply to this API call.

A later ServiceNow Flow may POST Operations. That contract is `ticket`
`references/snow-api.md`. This agent does not treat.

## Nexthink (you configure)

1. Campaign used **in workflows**. One single-answer question. The confirmed
   answer NQL id is `fix_now` (not the button label `Fix now`). Other answers
   (`Later`) do not call Studio.
2. Monitor or alert on the bad condition starts a **workflow** on that device.
3. Workflow: Campaign thinklet (wait for the answer) → branch → on the
   confirmed-problem branch a **Service/API** thinklet.
4. Service/API: POST the URL above. Header `X-API-Key` from a connector
   credential. Header `Content-Type` `application/json`. Body `mode` `api` and
   `humanPrompt` with the device name or serial and the answer text from the
   campaign thinklet.

Do not call Studio when the employee says Later. Do not put the API key in the
campaign question text.

Studio Async already returned HTTP before this visit finished. Your last reply
is still the visit result the caller should receive. There is no MCP tool for a
Nexthink Wait callback. Do not invent a POST.
