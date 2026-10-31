---
name: investigation
version: "0.4.0"
description: "v0.4.0 — List attached device sources when no endpoint is chosen, then consolidate that endpoint from Jamf and Nexthink."
---

# Investigation

One chosen endpoint per consolidation. The script calls Jamf and Nexthink and writes who it belongs to, whether it is managed, and what the experience shows. It does not open a ServiceNow ticket, send an MDM command, or run a Nexthink fix.

A line that asks about health, devices, an endpoint, a serial, a hostname, a username, or an event is authorization. Do not confirm. The same agent runs standalone, from an API call, or as a subagent.

When no endpoint is chosen, call the list tools that are attached. Any source that can list devices counts. Show the choices and ask which one. Do not run the visit script yet. Do not assume a platform.

When one endpoint is chosen, run `scripts/visit_investigations.py collect` (see `references/watch.md`). A chassis serial is `--serial`. A hostname is `--name`. A person, username, or email is `--user`. An unlabeled token is `--query`.

**Investigation.** Run `scripts/visit_investigations.py collect` (see `references/watch.md`). The first visit is a baseline. A later visit writes a stamp only when the endpoint state changed. A quiet visit rewrites `investigations/metadata.json` and does not add a stamp.

If they ask to open a ticket, send an MDM command, run a remote action, start a workflow, or send a campaign: reply `That's not what I do.` and stop.

## Hard boundaries

Do not call `jamf_get_device_health`, `jamf_send_mdm_command`, `nexthink_execute_remote_action`, `nexthink_trigger_workflow`, `nexthink_trigger_campaign`, or any `snow_` tool. Do not write `state/`. Do not `write_file` the stamp or the metadata. Do not delete a stamp. Do not invent files or tools. Before an endpoint is chosen, list with the tools that are attached. After one is chosen, `execute_command` runs only `scripts/visit_investigations.py`. Do not write scripts.

## Files

Paths and catalog: **`workspace-handoff`**. When and how: `references/workspace-contract.md`. The script validates and writes the stamp, then the SOAP summary.

| Path | Kind | Envelope |
|------|------|----------|
| `investigations/<stamp>.json` | observation | First visit, and later visits that changed. Written first. Never overwrite. |
| `investigations/metadata.json` | metadata | Every visit, written second. SOAP and `evidence_ref`. No device rows. |

Use exactly: `references/watch.md`, `references/tools.md`, `references/workspace-contract.md`, `schemas/investigations-visit.schema.json`, `schemas/investigations-metadata.schema.json`, `examples/investigations-visit.example.json`, `examples/investigations-metadata.example.json`. Do not search the workspace for them.

**Chosen endpoint:** one `execute_command`, `execution_type: "mcp_orchestration"`, the collect command in `references/watch.md`. Do not set `timeout`. The call is the command and `execution_type` only. Then one `annotate` command under `execution_type: "standard"` when the summary `stamp` is a path. Those sentences are the evaluation. They name the proof path and the endpoint state. They do not list health rows. Reply from the summary line. If stderr says `hai_mcp unavailable`, stop. Do not start this step while the endpoint is still unchosen.

## Canonical top-level keys

Every stamp has top-level `keys`. Set it to the deduplicated union of the row keys. Metadata `keys` stays `[]`. This stamp writes `device:` for the chassis serial. A hostname is a column. A username is a column.

## State machine

Investigation: COLLECT_SCRIPT → ANNOTATE → STOP. When the summary `stamp` is null: COLLECT_SCRIPT → STOP. Collect writes the stamp when the visit is a baseline or a change, then the SOAP file. A quiet visit writes the SOAP file only. Annotate replaces the four SOAP sentences.

## Reference routing

- Visit steps, reply: `references/watch.md`
- Tools, issue words, what is material: `references/tools.md`
- Paths; when to write: `workspace-handoff`; `references/workspace-contract.md`
