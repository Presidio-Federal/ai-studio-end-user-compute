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
  "mode": "fire_and_forget",
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
   disk, crashes, and `user_sid`.
3. `notify` `#mcp_ops_working` with `--details` one sentence. Same
   `execute_command` / `mcp_orchestration` paths as collect.
4. If `recommended_treat` is `disk`, `treat` with `--serial` and `--group`
   `MCP-Remediate-Disk`.
5. If `recommended_treat` is `crash`, `treat` with `--serial` and `--group`
   `MCP-Remediate-Crash`. That is the same kind of fix as disk: add the Mac
   to the static group and blank-push it so the Jamf policy runs. Do not use
   a Nexthink remote action for this. Those remediation scripts are Windows-only.
6. `notify` `#mcp_ops_update` after a fix has started.
7. `close` only after that fix. The script resolves the INC only when the
   short description starts with `EUC_DEMO` and that serial is an EUC demo
   asset. A model category other than Computer is refused. Close code is
   `Solution provided`.
8. `notify` `#mcp_ops_closed`.

```text
python3 <copied script path> notify --workspace <copied file_explorer directory> --campaign "#mcp_ops_working" --details "Operations is treating disk on this Mac."
python3 <copied script path> treat --workspace <copied file_explorer directory> --serial "SERIAL123456" --group "MCP-Remediate-Disk"
python3 <copied script path> notify --workspace <copied file_explorer directory> --campaign "#mcp_ops_update" --details "The disk group was updated. The ticket is still open."
python3 <copied script path> close --workspace <copied file_explorer directory> --incident "INC0010001" --serial "SERIAL123456"
python3 <copied script path> notify --workspace <copied file_explorer directory> --campaign "#mcp_ops_closed" --details "The disk treat finished."
```

Do not call `snow_create_incident`. Do not run a Nexthink remote action for a crash.
Create the three campaigns with `references/campaigns.md` before the first
send. One user SID. Skip the send when that SID is missing.
