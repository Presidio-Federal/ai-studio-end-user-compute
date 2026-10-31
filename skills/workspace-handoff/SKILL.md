---
name: workspace-handoff
description: "v0.2.0 — Workspace catalog of who writes each path. Jamf and investigations stamps are the records. Metadata is the SOAP note."
version: "0.2.0"
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
| `jamf/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Jamf Inventory | `jamf-inventory` `schemas/jamf-inventory-visit.schema.json` | Whether the computer exists, who it is assigned to, and managed, supervised, user-approved MDM, and MDM capable. `keys` use `device:` for the chassis serial. A later stamp is only the computers whose owner or management level changed. |
| `jamf/metadata.json` | metadata | Jamf Inventory | `jamf-inventory` `schemas/jamf-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. Counts are fine. The computer rows are not. |
| `investigations/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Investigation | `investigation` `schemas/investigations-visit.schema.json` | The consolidated state of one endpoint found by serial, hostname, or username: owner, management, and the experience reading. `keys` use `device:` for the chassis serial. A later stamp is only that endpoint when the state changed. |
| `investigations/metadata.json` | metadata | Investigation | `investigation` `schemas/investigations-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. `issue` is the verdict word. The device row is not. |

## Writing

1. Write only the catalog row you own.
2. Fill fields from your skill schema.
3. The visit script writes the file. Do not `write_file` the stamp or the metadata from the prompt.
