---
name: demo
version: "0.3.0"
description: "v0.3.0 — Start workflow #mcp_investigate_on_consent. It sends #mcp_fix_consent. Fix now calls Investigation."
---

# Demo

Read `demo/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

Do not call `get_folder_structure`. Do not create a task plan. Built-in `read_file` filePath is the catalog path `demo/metadata.json`. Do not prefix `file_explorer/`. Do not pass `Internal directory` to built-in file tools. That string is only the python path Studio shows for `execute_command`.

You start the consent workflow. You do not investigate. You do not open a ticket. You do not treat. A line that says start the demo, send the campaign, or names a hostname, username, or SID is authorization. Do not confirm.

The script calls `nexthink_trigger_workflow` for `#mcp_investigate_on_consent`. That workflow sends `#mcp_fix_consent`, which stays trigger **Workflow**. Do not switch that campaign to API. The prompt does not call the tool. The prompt does not `write_file` the chart.

## Before an endpoint is chosen

Use the MCP tools attached to you. List calls are in `references/tools.md`. Show hostname and last login. Ask which one. Do not run the visit script. Skip this when the task line already named a hostname, username, serial, or SID.

## After one endpoint is chosen

**First tool:** `read_file` `demo/metadata.json`. Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `demo/scripts/visit_demos.py`. Paste it. Do not retype a path from memory. Do not set `timeout`.

Each `execute_command` is a new container. `--workspace` is the `file_explorer` directory beside `skills` on that same Studio path. Paste that directory. Do not `cp` it. Do not make a second tree. Do not pass the relative name `file_explorer`. Do not `cd`. Built-in `read_file` and the script write the same tree.

```text
python3 <script path Studio showed> start --workspace <file_explorer directory Studio showed> --name "<hostname>"
python3 <script path Studio showed> start --workspace <file_explorer directory Studio showed> --user "<username>"
python3 <script path Studio showed> start --workspace <file_explorer directory Studio showed> --sid "<user SID>"
```

Pass the one the person chose. Optional `--serial`. Optional `--campaign` only for a published API campaign such as `#mcp_triage_result`. Do not pass `#mcp_fix_consent` as an API campaign. For `#mcp_triage_result` also pass `--ticket` and `--details`.

The script starts the workflow for that device and writes the stamp and a factual SOAP note. The employee still sees `#mcp_fix_consent`. Fix now calls Investigation. The last stdout line is the result. You then say what it means. If stderr says `hai_mcp unavailable`, stop.

To replace the SOAP sentences with your opinion, one `execute_command`, `execution_type: "standard"`, same paths:

```text
python3 <script path Studio showed> annotate --workspace <file_explorer directory Studio showed> --stamp demo/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what was sent>" --assessment "<what it means>" --plan "<next, or none>"
```

`--stamp` is the summary field `stamp`. Each SOAP argument is one sentence, under 400 characters, with no JSON.

## Files

| Path | Kind |
|------|------|
| `demo/<stamp>.json` | The record. First run is a baseline. Later runs are the delta. Never overwrite. |
| `demo/metadata.json` | SOAP note. `campaign` is the NQL id. `evidence_ref` names the latest stamp. |

Schema and example: `schemas/demo-visit.schema.json`, `schemas/demo-metadata.schema.json`, `examples/demo-visit.example.json`, `examples/demo-metadata.example.json`. `device:` is the chassis serial. A hostname is a column. A user SID is a column.

Do not `write_file` those paths. Do not write `state/`. Do not write `investigations/` or `tickets/`. Do not call `get_folder_structure`.
