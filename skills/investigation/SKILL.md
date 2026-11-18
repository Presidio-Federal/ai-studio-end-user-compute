---
name: investigation
version: "0.13.0"
description: "v0.13.0 — Investigate one chosen endpoint. Wait for Ticket's INC, then notify sends the employee campaign."
---

# Investigation

**First tool:** `read_file` `investigations/metadata.json`. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search. Do not call `get_folder_structure`. Do not create a task plan.

Built-in `read_file` filePath is the catalog path `investigations/metadata.json`. Do not prefix `file_explorer/`. Do not pass `Internal directory` to built-in file tools. That string is only the python path Studio shows for `execute_command`.

A line that asks about an endpoint or its health is authorization. Do not confirm. An API `humanPrompt` that already names a serial, hostname, or username has chosen the endpoint. Collect. You do not open a ticket, send an MDM command, run a remote action, start a workflow, or send a campaign. Ticket opens the incident from this SOAP. After Ticket has **replied** with an INC, `notify` is the reply to the API caller.

The campaign-to-API contract is `references/campaign-api.md`. Ticket copies the stamp onto the INC. The ServiceNow outbound contract is `ticket` `references/snow-api.md`.

## Before an endpoint is chosen

Use the MCP tools attached to you. List calls are in `references/tools.md`. Show the choices and ask which one. Do not run the visit script. Skip this when the task line already named one.

## After one endpoint is chosen

**First collect tool:** `read_file` `investigations/metadata.json`. Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `investigation/scripts/visit_investigations.py`. Paste it. Do not retype a path from memory. Do not set `timeout`.

Each `execute_command` is a new container. `--workspace` is the `file_explorer` directory beside `skills` on that same Studio path. Paste that directory. Do not `cp` it. Do not make a second tree. Do not pass the relative name `file_explorer`. Do not `cd`. Built-in `read_file` and the script write the same tree.

A serial is `--serial`. A hostname is `--name`. A username or email is `--user`. Pass the one the person chose.

```text
python3 <script path Studio showed> collect --workspace <file_explorer directory Studio showed> --serial "<serial>"
python3 <script path Studio showed> collect --workspace <file_explorer directory Studio showed> --name "<hostname>"
python3 <script path Studio showed> collect --workspace <file_explorer directory Studio showed> --user "<username>"
```

The script calls Jamf and Nexthink, fills the schema, and writes the stamp and a factual SOAP note. The last stdout line is the result. You then say what it means. If stderr says `hai_mcp unavailable`, stop.

To replace the SOAP sentences with your opinion, one `execute_command`, `execution_type: "standard"`, same paths:

```text
python3 <script path Studio showed> annotate --workspace <file_explorer directory Studio showed> --stamp investigations/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what the record shows>" --assessment "<what it means>" --plan "<next, or none>"
```

`--stamp` is the summary field `stamp`. Each SOAP argument is one sentence, under 400 characters, with no JSON.

## After a campaign-authorized collect

Do not call `snow_create_incident`. If Ticket is attached as a subagent, start it with one line: open the incident from the investigations SOAP. Do not paste the device row. **Stop this turn.** Do not `read_file` `tickets/metadata.json` on this turn. Do not `notify` on this turn. "Subagent launched" is not a ticket.

When Ticket has replied with an INC number, `read_file` `tickets/metadata.json`. `File not found` means Ticket did not write. Stop. Do not search. Do not list the workspace.

When that SOAP has a `number`, one `execute_command`, `execution_type: "mcp_orchestration"`, same pasted paths:

```text
python3 <script path Studio showed> notify --workspace <file_explorer directory Studio showed>
```

`notify` sends `#mcp_triage_result` with `ticket_number` and `details`. The last stdout line is the ticket number. That line is your reply to the API caller. The employee sees campaign 2, not campaign 1 waiting.

## Files

| Path | Kind |
|------|------|
| `investigations/<stamp>.json` | The record. First run is a baseline. Later runs are the delta. Never overwrite. |
| `investigations/metadata.json` | SOAP note. `evidence_ref` names the latest stamp. |

Schema and example: `schemas/investigations-visit.schema.json`, `schemas/investigations-metadata.schema.json`, `examples/investigations-visit.example.json`, `examples/investigations-metadata.example.json`. `device:` is the chassis serial. A hostname is a column. A username is a column.

Do not `write_file` those paths. Do not write `state/`. Do not write `tickets/`. Do not call `get_folder_structure`.
