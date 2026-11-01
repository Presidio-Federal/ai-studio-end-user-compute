---
name: investigation
version: "0.7.0"
description: "v0.7.0 — Investigate one chosen endpoint. The visit script calls Jamf and Nexthink and fills the schema."
---

# Investigation

Read `investigations/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

A line that asks about an endpoint or its health is authorization. Do not confirm. You do not open a ticket, send an MDM command, run a remote action, start a workflow, or send a campaign.

## Before an endpoint is chosen

Use the MCP tools attached to you. List calls are in `references/tools.md`. Show the choices and ask which one. Do not run the visit script.

## After one endpoint is chosen

One `execute_command`, `execution_type: "mcp_orchestration"`. Copy the path Studio shows for `scripts/visit_investigations.py`. Pass the `file_explorer` directory beside `skills` as `--workspace`. Do not set `timeout`.

A serial is `--serial`. A hostname is `--name`. A username or email is `--user`. Pass the one the person chose.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --name "<hostname>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --user "<username>"
```

The script calls Jamf and Nexthink, fills the schema, and writes the stamp and a factual SOAP note. The last stdout line is the result. You then say what it means. If stderr says `hai_mcp unavailable`, stop.

To replace the SOAP sentences with your opinion, one `execute_command`, `execution_type: "standard"`, same paths:

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp investigations/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what the record shows>" --assessment "<what it means>" --plan "<next, or none>"
```

`--stamp` is the summary field `stamp`. Each SOAP argument is one sentence, under 400 characters, with no JSON.

## Files

| Path | Kind |
|------|------|
| `investigations/<stamp>.json` | The record. First run is a baseline. Later runs are the delta. Never overwrite. |
| `investigations/metadata.json` | SOAP note. `evidence_ref` names the latest stamp. |

Schema and example: `schemas/investigations-visit.schema.json`, `schemas/investigations-metadata.schema.json`, `examples/investigations-visit.example.json`, `examples/investigations-metadata.example.json`. `device:` is the chassis serial. A hostname is a column. A username is a column.

Do not `write_file` those paths. Do not write `state/`.
