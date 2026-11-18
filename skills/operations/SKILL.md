---
name: operations
version: "0.9.0"
description: "v0.9.0 — Ticket-authorized disk or crash fix via a Jamf group, then resolve the INC."
---

# Operations

Read `operations/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

Do not call `get_folder_structure`. Built-in `read_file` filePath is the catalog path `operations/metadata.json`. Do not prefix `file_explorer/`. Do not pass `Internal directory` to built-in file tools.

You own devices already in the fleet that are failing, and the open EUC demo incidents on them. A line that asks who is sick, DEX, compliance, in-life health, or which tickets are open is authorization. Do not confirm. You do not enroll a device. You do not open a new ticket, start a workflow, or run a Nexthink remote action. Ticket-authorized visits may send `#mcp_ops_working`, `#mcp_ops_update`, and `#mcp_ops_closed` through `notify`. Follow `references/campaigns.md`. You do not change a computer group or send MDM unless the person authorizes that treat, or an API `humanPrompt` names a serial and says the ticket authorized this visit.

Open tickets: `snow_find_incidents` with `search` `EUC_DEMO` and `active_only` true. One INC: `snow_get_incident`. Do not refuse that read. Do not name another agent.

The ticket-to-API contract is `references/ticket-api.md`.

## Collect

**First tool:** `read_file` `operations/metadata.json`. Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `operations/scripts/visit_operations.py`. Copy it. Do not retype a path from memory. The transcript may render it as `Internal directory`; that string is the python path, not a folder to list. Do not set `timeout`.

Each `execute_command` is a new container. In that container the workspace is the `file_explorer` folder beside `skills` on the path Studio shows for `visit_operations.py`. Copy that directory. Pass it as `--workspace`. Do not pass the relative name `file_explorer`, and do not `cd`.

Omit filters for the failing fleet. Pass `--serial` or `--name` when the task line names one device.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory>
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --name "<hostname>"
```

The script uses the tools attached to this agent. A missing tool is a gap, not a halt. It fills the schema and writes the stamp and a factual SOAP note. The last stdout line is the result. You then say what it means. If stderr says `hai_mcp unavailable`, stop.

To replace the SOAP sentences with your opinion, one `execute_command`, `execution_type: "standard"`, same paths:

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp operations/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what the record shows>" --assessment "<what it means>" --plan "<next nurse, or none>"
```

`--stamp` is the summary field `stamp`. Each SOAP argument is one sentence, under 400 characters, with no JSON.

## Treat

Only when the person names a serial and authorizes a fix, or the API line is ticket-authorized. Read `tickets/metadata.json` and the investigation stamp first. If `recommended_treat` is `disk`, use the group below. If it is `crash`, follow `references/ticket-api.md`. Do not close the INC when no fix ran. One `execute_command`, `execution_type: "mcp_orchestration"`, same copied paths. `--group` is the exact static group name.

```text
python3 <copied script path> treat --workspace <copied file_explorer directory> --serial "<serial>" --group "MCP-Remediate-Disk"
python3 <copied script path> treat --workspace <copied file_explorer directory> --serial "<serial>" --group "MCP-Remediate-Disk" --action remove
```

The script adds or removes that computer on the group, then `BLANK_PUSH` on add. It does not write a stamp. Collect again after check-in to record whether the issue moved.

## Notify

Only on a ticket-authorized visit. One `execute_command`, `execution_type: "mcp_orchestration"`, same copied paths. `--campaign` is one of `#mcp_ops_working`, `#mcp_ops_update`, `#mcp_ops_closed`. The script reads the INC from `tickets/metadata.json` unless you pass `--incident`. `--details` is one sentence for the popup. It sends to the one `user_sid` on the investigation stamp. Never `"*"`. If that SID is missing, it skips the send.

```text
python3 <copied script path> notify --workspace <copied file_explorer directory> --campaign "#mcp_ops_working" --details "Operations is treating disk on this Mac."
python3 <copied script path> notify --workspace <copied file_explorer directory> --campaign "#mcp_ops_update" --details "The disk group was updated. The ticket is still open."
python3 <copied script path> notify --workspace <copied file_explorer directory> --campaign "#mcp_ops_closed" --details "The disk treat finished."
```

When: `#mcp_ops_working` at the start of the ticket-authorized visit. `#mcp_ops_update` after treat (or after you decide there is nothing to treat) while the INC is still open. `#mcp_ops_closed` after `close`. Collect still must not send a campaign.

## Files

| Path | Kind |
|------|------|
| `operations/<stamp>.json` | The record. First run is a baseline. Later runs are the delta. Never overwrite. |
| `operations/metadata.json` | SOAP note. `evidence_ref` names the latest stamp. |

Schema and example: `schemas/operations-visit.schema.json`, `schemas/operations-metadata.schema.json`, `examples/operations-visit.example.json`, `examples/operations-metadata.example.json`. `device:` is the chassis serial. A hostname is a column. A username is a column.

Do not `write_file` those paths. Do not write `state/`. Do not write `onboarding/` or `investigations/`. Do not call `get_folder_structure`.
