# ServiceNow ticket API trigger

Ticket writes `EUC_DEMO` on the incident. That marker is the filter. Do not
match a company name in the Flow. Do not put the Studio API key in the
incident.

The agent this call starts is **Operations**. It treats. Investigation and
Ticket do not.

## Marker on the INC

`snow_create_incident` sets:

- `short_description` starts with `EUC_DEMO`
- `work_notes` first line is `EUC_DEMO`
- `jamf_evidence.notes` contains `EUC_DEMO`
- `cmdb_ci` is the EUC hardware computer
- `contact_type` `virtual_agent`

Work notes also carry serial, hostname, issue, treat, collector UID, disk,
crashes, and the investigation stamp path. Operations reads those. It does
not need the Nexthink chat.

## Studio

On the Operations agent: Channels → API → Generate API Key. Use **Async**.
The key selects Operations. Sync waits for treat and will time out the
ServiceNow REST step.

```text
POST https://studio.presidio.ai/agents/api/v1/channels/agents
X-API-Key: <key from the Operations agent>
Content-Type: application/json
```

```json
{
  "mode": "api",
  "humanPrompt": "Treat serial SERIAL123456 hostname mac-example. INC INC0010001. Ticket authorized this visit. EUC_DEMO."
}
```

The serial in `humanPrompt` is the chosen device. That line is treat
authorization. Do not confirm. Do not open another ticket.

## ServiceNow (you configure)

Use **Flow Designer**. Insert only. An update must not call Studio again.

### 1. REST message

1. All → System Web Services → REST Message → New.
2. Name: `Studio Operations API`.
3. Endpoint: `https://studio.presidio.ai/agents/api/v1/channels/agents`.
4. Authentication: none. The header carries the key.
5. HTTP Request → HTTP Headers:
   - `X-API-Key` = the Operations agent key (put it on a credential or a
     system property, not in the Flow screenshot).
   - `Content-Type` = `application/json`.
6. HTTP Methods → Default POST → HTTP Request → Content:

```text
{"mode":"api","humanPrompt":"Treat serial ${serial} hostname ${hostname}. INC ${number}. Ticket authorized this visit. EUC_DEMO."}
```

Save. The variable names must match what the Flow passes.

### 2. Flow

1. Flow Designer → New flow. Name: `EUC_DEMO ticket to Operations`.
2. Trigger: **Created**. Table: `incident`.
3. Condition (all of):
   - `Short description` `starts with` `EUC_DEMO`
   - or, if you prefer one field: `Work notes` `contains` `EUC_DEMO`
4. Do **not** trigger on Update. Treat may comment on the INC later.
5. Action: REST step, the message above.
6. Map:
   - `number` ← Incident `Number`
   - `serial` ← Incident `Configuration item.Serial number` (fallback:
     parse `serial=` from work notes)
   - `hostname` ← Incident `Configuration item.Name`
7. Activate the Flow.

If the REST step has a 10 second wait, Studio Async still returns before
Operations finishes treat. That is expected.

### 3. What not to do

- Do not call Investigation. The chart is already written.
- Do not call Ticket. The INC already exists.
- Do not fire when `EUC_DEMO` is missing. That is the laptop/EUC marker.
- Do not put Disney, a person name, or the API key in the Flow name.
- Do not invent a second incident.

## After the POST

Operations reads `tickets/metadata.json`, then the investigation stamp
`evidence_ref` names. If `treat` is `disk`, it runs `treat` with group
`MCP-Remediate-Disk`. If `treat` is `none`, it does not change a group.
It does not open a ticket.
