---
name: workspace-handoff
description: "v0.5.0 — Workspace catalog of who writes each path. Lifecycle nurses own a folder. Ticket writes the incident number from the investigation SOAP."
version: "0.5.0"
---

# Workspace handoff

The shared workspace is the state. This skill is the catalog: which files
exist, who writes each one, and which fields another agent may read.
The writer skill owns the schema, the example, and the procedure.
Load a schema only when you are that writer. Do not copy a schema
into this skill.

One writer per file. Source systems stay authoritative. The stamp is
derived facts and evidence refs.

A nurse owns a lifecycle role, not a product. Tools attached to that
nurse are how it collects. They are not the identity. The next nurse
starts from the SOAP note, and from the stamp `evidence_ref` names
when it needs the rows.

The nurse script calls MCP tools through `scripts/visit_common.py`
`mcp_call` under `execution_type: "mcp_orchestration"`. It writes the
stamp, then the SOAP metadata. The prompt does not `write_file` those
paths.

| Path | Kind | Writer | Schema | What another agent may read |
|------|------|--------|--------|-----------------------------|
| `onboarding/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Onboarding | `onboarding` `schemas/onboarding-visit.schema.json` | Whether a device is in a PreStage, in MDM inventory, in the directory, or managed. `keys` use `device:` for the chassis serial. A later stamp is only devices whose enrollment stage changed. |
| `onboarding/metadata.json` | metadata | Onboarding | `onboarding` `schemas/onboarding-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. Counts are fine. The device rows are not. |
| `jamf/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Jamf Inventory | `jamf-inventory` `schemas/jamf-inventory-visit.schema.json` | Whether the computer exists, who it is assigned to, and managed, supervised, user-approved MDM, and MDM capable. `keys` use `device:` for the chassis serial. A later stamp is only the computers whose owner or management level changed. |
| `jamf/metadata.json` | metadata | Jamf Inventory | `jamf-inventory` `schemas/jamf-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. Counts are fine. The computer rows are not. |
| `investigations/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Investigation | `investigation` `schemas/investigations-visit.schema.json` | The consolidated state of one endpoint found by serial, hostname, or username: owner, management, and the experience reading. `keys` use `device:` for the chassis serial. A later stamp is only that endpoint when the state changed. |
| `investigations/metadata.json` | metadata | Investigation | `investigation` `schemas/investigations-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. `issue` is the verdict word. The device row is not. |
| `tickets/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Ticket | `ticket` `schemas/tickets-visit.schema.json` | The ServiceNow incident opened from the investigation SOAP: number, state, serial, hostname. `keys` use `device:` for the chassis serial. A later stamp is only that incident when the number or state changed. |
| `tickets/metadata.json` | metadata | Ticket | `ticket` `schemas/tickets-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. `number` is the INC. Concise details are in the SOAP sentences. The incident row is not. |
| `operations/<YYYY-MM-DDTHH-MM-SSZ>.json` | observation | Operations | `operations` `schemas/operations-visit.schema.json` | In-life devices that are failing experience or compliance, plus serial and collector UID when known. `keys` use `device:` for the chassis serial. A later stamp is only devices whose issue or vitals changed. |
| `operations/metadata.json` | metadata | Operations | `operations` `schemas/operations-metadata.schema.json` | SOAP note. `evidence_ref` is the latest stamp. Counts are fine. The device rows are not. |

## Writing

1. Write only the catalog row you own.
2. Fill fields from your skill schema.
3. The visit script writes the file. Do not `write_file` the stamp or the metadata from the prompt.
