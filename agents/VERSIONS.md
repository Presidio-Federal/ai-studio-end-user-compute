# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

Nurses own a lifecycle role. Tools attached to that nurse are how it collects. They are not the identity.

| Agent | Version | Model |
|-------|---------|-------|
| onboarding-agent | 0.3.0 | MiniMax |
| jamf-inventory-agent | 0.2.0 | MiniMax |
| investigation-agent | 0.14.0 | MiniMax |
| ticket-agent | 0.3.2 | MiniMax |
| operations-agent | 0.9.1 | MiniMax |
| demo-agent | 0.3.0 | MiniMax |
| endpoint-pipeline-agent | 1.1.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.7.0 | Catalog for onboarding, Jamf inventory, investigations, tickets, operations, demo, and endpoint-operations stamps plus SOAP notes. Visit helpers live in `scripts/visit_common.py`. |
| onboarding | 0.3.0 | Enrollment into MDM. Collect is read-only. Jamf 404 is a gap, not an unattached tool. Assigns a PreStage only when authorized. |
| jamf-inventory | 0.2.0 | Whether a Jamf computer exists, who it belongs to, and its management level. |
| investigation | 0.15.1 | `collect` opens the EUC_DEMO incident. `recommended_treat` allows `crash`. |
| ticket | 0.3.2 | Same catalog as Investigation. `tickets/metadata.json` missing is the first run. Copies the investigation pack onto the INC with `EUC_DEMO`. Company comes from `u_euc_demo` hardware. |
| operations | 0.9.1 | Ticket-authorized disk uses `MCP-Remediate-Disk`. A crash uses `MCP-Remediate-Crash`. Treat passes `computer_id` when a serial matches more than one Jamf computer. Close only after that group update. |
| demo | 0.3.0 | `start` triggers workflow `#mcp_investigate_on_consent`. The campaign stays Workflow. Fix now calls Investigation. |
| endpoint-pipeline | 1.1.0 | Copies Disney EUC computers onto `euc_operations`. `#mcp_device_vitals` supplies `dex_score` before the Elasticsearch write. |

Refresh and retirement are the next roles. They are not in the catalog yet.
