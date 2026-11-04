# Ticket API intake

ServiceNow opens an `EUC_DEMO` incident. A Flow POSTs this agent. Ticket
already wrote the INC. This skill does not open another one.

The contract on the ServiceNow side is `ticket` `references/snow-api.md`.

## Studio

On the Operations agent: Channels → API → Generate API Key. Use **Async**.

```text
POST https://studio.presidio.ai/agents/api/v1/channels/agents
X-API-Key: <key from this agent>
Content-Type: application/json
```

```json
{
  "mode": "api",
  "humanPrompt": "Treat serial SERIAL123456 hostname mac-example. INC INC0010001. Ticket authorized this visit. EUC_DEMO."
}
```

The serial is the chosen device. That line is treat authorization. Do not
confirm. Do not collect the whole fleet first.

## After the API line

1. `read_file` `tickets/metadata.json`. `File not found` means Ticket has
   not written. Stop.
2. `read_file` `investigations/metadata.json`, then the stamp `evidence_ref`
   names. That row has `recommended_treat`, serial, hostname, collector UID,
   disk, and crashes.
3. If `recommended_treat` is `disk`, one `execute_command`,
   `execution_type: "mcp_orchestration"`, `treat` with `--serial` and
   `--group` `MCP-Remediate-Disk`.
4. If `recommended_treat` is `none` or `unknown`, do not treat. Reply that
   this INC has no static-group fix.

Do not call `snow_create_incident`. Do not send a campaign. Do not run a
Nexthink remote action.
