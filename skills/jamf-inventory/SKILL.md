---
name: jamf-inventory
version: "0.1.0"
description: "v0.1.0 — Find an enrolled Jamf Mac by serial and record inventory, check-in, and device status."
---

# Jamf inventory

One Jamf visit per conversation. The script calls `jamf_find_devices`, `jamf_get_device`, and `jamf_get_device_health`. It writes the stamp, then the SOAP note.

A line that asks for Jamf inventory, an enrolled Mac, a serial, or device status is authorization. Do not confirm.

**Inventory.** Run `scripts/visit_jamf.py collect` (see `references/watch.md`). Pass `--serial` only when the task line names one. The first visit is a baseline. A later visit writes only the computers that changed since the last stamp. A quiet visit rewrites `jamf/metadata.json` and does not add a stamp. Check-in time and last IP alone do not open a stamp.

Two Jamf records can share one serial. The live record is the one that is managed and has a last check-in. The other stays on the stamp as its own id.

If they ask to send an MDM command, assign a PreStage, change a Jamf account, or open a ServiceNow record: reply `That's not what I do.` and stop.

## Hard boundaries

Do not call `jamf_send_mdm_command`, `jamf_list_prestages`, `jamf_assign_prestage_serial`, `jamf_manage_accounts`, or any ServiceNow tool. Do not call `jamf_get_device_dossier` or `jamf_get_device_history`. Do not write `state/`. Do not `write_file` the stamp or the metadata. Do not delete a stamp. Do not invent files. On this visit, `execute_command` runs only `scripts/visit_jamf.py`. Do not write scripts.

## Files

Paths and catalog: **`workspace-handoff`**. When and how: `references/workspace-contract.md`. The script validates and writes the stamp, then the SOAP summary.

| Path | Kind | Envelope |
|------|------|----------|
| `jamf/<stamp>.json` | observation | First visit, and later visits that changed. Written first. Never overwrite. |
| `jamf/metadata.json` | metadata | Every visit, written second. SOAP and `evidence_ref`. No computer rows. |

Use exactly: `references/watch.md`, `references/tools.md`, `references/workspace-contract.md`, `schemas/jamf-inventory-visit.schema.json`, `schemas/jamf-metadata.schema.json`, `examples/jamf-inventory-visit.example.json`, `examples/jamf-metadata.example.json`. Do not search the workspace for them.

**Inventory visit — first tool:** one `execute_command`, `execution_type: "mcp_orchestration"`, the collect command in `references/watch.md`. Do not set `timeout`. The call is the command and `execution_type` only. Then one `annotate` command under `execution_type: "standard"` when the summary `stamp` is a path. Those sentences are the evaluation. They name the proof path and the delta. They do not list the computers. Reply from the summary line. If stderr says `hai_mcp unavailable`, stop.

## Canonical top-level keys

Every stamp has top-level `keys`. Set it to the deduplicated union of the row keys. Metadata `keys` stays `[]`. Keys match `^(device|site|warehouse|request):[^ ].*$`. Use `device:` for the chassis serial. Use `site:` for the Jamf site name. A hostname is a column. A comment is not a site.

## State machine

Inventory: COLLECT_SCRIPT → ANNOTATE → STOP. When the summary `stamp` is null: COLLECT_SCRIPT → STOP. Collect writes the stamp when the visit is a baseline or a change, then the SOAP file. A quiet visit writes the SOAP file only. Annotate replaces the four SOAP sentences.

## Reference routing

- Visit steps, reply: `references/watch.md`
- Tools, live record, what is material: `references/tools.md`
- Paths; when to write: `workspace-handoff`; `references/workspace-contract.md`
