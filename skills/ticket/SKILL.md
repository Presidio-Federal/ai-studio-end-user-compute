---
name: ticket
version: "0.3.2"
description: "v0.3.2 — Open a ServiceNow incident from the investigation pack. Marks it EUC_DEMO for the Operations API trigger."
---

# Ticket

**First tool:** `read_file` `tickets/metadata.json`. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Continue. Do not search. Do not call `get_folder_structure`. Do not create a task plan.

Then `read_file` `investigations/metadata.json`. That SOAP is the source. `evidence_ref` on it names the investigation stamp. Read that stamp when you need the serial, hostname, and user. `File not found` means Investigation has not written in this catalog. Stop. Do not invent an endpoint. Do not collect Jamf or Nexthink. Do not list the workspace.

Built-in `read_file` filePath is the catalog path. Do not prefix `file_explorer/`. Do not pass `Internal directory` to built-in file tools. That string is only the python path Studio shows for `execute_command`. This is the same catalog Investigation just wrote.

You open the incident. You do not investigate. You do not enroll. You do not treat. A campaign-authorized investigation SOAP, or a line that asks to open a ticket, is authorization. Do not confirm. Copy the investigation stamp onto the INC: serial, hostname, issue, treat, disk, crashes, collector UID, and the proof path. First line of work notes is `EUC_DEMO`. That marker is how ServiceNow starts Operations. The outbound contract is `references/snow-api.md`.

## Open

Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `ticket/scripts/visit_tickets.py`. Paste it. Do not retype a path from memory. Do not set `timeout`.

Each `execute_command` is a new container. `--workspace` is the `file_explorer` directory beside `skills` on that same Studio path. Paste that directory. Do not `cp` it. Do not make a second tree. Do not pass the relative name `file_explorer`. Do not `cd`. Built-in `read_file` and the script write the same tree.

```text
python3 <script path Studio showed> open --workspace <file_explorer directory Studio showed>
python3 <script path Studio showed> open --workspace <file_explorer directory Studio showed> --serial "<serial from the investigation stamp>"
```

The script reads the investigation chart, finds or writes the endpoint as an EUC hardware asset, reuses an active INC when one already matches, otherwise calls `snow_create_incident` on that CI, and writes the stamp and a factual SOAP note. The last stdout line is the result. You then say the ticket number and one concise sentence. If stderr says `hai_mcp unavailable`, stop.

To replace the SOAP sentences with your opinion, one `execute_command`, `execution_type: "standard"`, same paths:

```text
python3 <script path Studio showed> annotate --workspace <file_explorer directory Studio showed> --stamp tickets/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<ticket number and what it covers>" --assessment "<what it means>" --plan "<Investigation replies to the caller>"
```

`--stamp` is the summary field `stamp`. Each SOAP argument is one sentence, under 400 characters, with no JSON.

## Files

| Path | Kind |
|------|------|
| `tickets/<stamp>.json` | The record. First run is a baseline. Later runs are the delta. Never overwrite. |
| `tickets/metadata.json` | SOAP note. `number` is the INC. `evidence_ref` names the latest stamp. |

Schema and example: `schemas/tickets-visit.schema.json`, `schemas/tickets-metadata.schema.json`, `examples/tickets-visit.example.json`, `examples/tickets-metadata.example.json`. `device:` is the chassis serial. A hostname is a column. An INC is `number`, not a `request:` tag.

Do not `write_file` those paths. Do not write `state/`. Do not write `investigations/`. Do not call `get_folder_structure`.
