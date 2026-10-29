---
name: workspace-handoff
description: "v0.1.0 — Workspace catalog of who writes each path, with the Jamf stamp as the record and metadata as the SOAP note."
version: "0.1.0"
---

# Workspace handoff

The shared workspace is the state. This skill is the catalog: which files
exist, who writes each one, and which fields another agent may read.
The writer skill owns the schema, the example, and the procedure.
Load a schema only when you are that writer. Do not copy a schema
into this skill.

One writer per file. Source systems stay authoritative. The stamp is
derived facts and evidence refs.

The nurse script calls MCP tools through `scripts/visit_common.py`
`mcp_call` under `execution_type: "mcp_orchestration"`. It writes the
stamp, then the SOAP metadata. The prompt does not `write_file` those
paths.

| Path | Kind | Writer | Schema | What another agent may read |
|------|------|--------|--------|-----------------------------|
| `jamf/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Jamf Inventory | `jamf-inventory` `schemas/jamf-inventory-visit.schema.json` | First visit is the baseline. A later stamp is only the computers that changed, plus `removed` and `vs_prior.changed`. `keys` use `device:` for the chassis serial. A hostname is a column. A quiet visit does not add a stamp. |
| `jamf/metadata.json` | metadata | Jamf Inventory | `jamf-inventory` `schemas/jamf-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. Counts are fine. The computer rows are not. |

## Writing

1. Write only the catalog row you own.
2. Fill fields from your skill schema.
3. The visit script writes the file. Do not `write_file` the stamp or the metadata from the prompt.
