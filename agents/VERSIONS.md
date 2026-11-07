# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

Nurses own a lifecycle role. Tools attached to that nurse are how it collects. They are not the identity.

| Agent | Version | Model |
|-------|---------|-------|
| onboarding-agent | 0.3.0 | MiniMax |
| jamf-inventory-agent | 0.2.0 | MiniMax |
| investigation-agent | 0.12.0 | MiniMax |
| ticket-agent | 0.3.0 | MiniMax |
| operations-agent | 0.4.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.5.0 | Catalog for onboarding, Jamf inventory, investigations, tickets, and operations stamps plus SOAP notes. Visit helpers live in `scripts/visit_common.py`. |
| onboarding | 0.3.0 | Enrollment into MDM. Collect is read-only. Jamf 404 is a gap, not an unattached tool. Assigns a PreStage only when authorized. |
| jamf-inventory | 0.2.0 | Whether a Jamf computer exists, who it belongs to, and its management level. |
| investigation | 0.12.0 | After Ticket writes the INC, `notify` sends `#mcp_triage_result` with `ticket_number` and `details`. Campaign 1 is consent only. It does not wait for ServiceNow. |
| ticket | 0.3.0 | Copies the investigation pack onto the INC with an `EUC_DEMO` marker, on the EUC hardware CI. ServiceNow Flow uses that marker to POST Operations. Does not investigate or treat. |
| operations | 0.4.0 | In-life devices that are failing. Treats a Mac via `MCP-Remediate-Disk` when a person or an `EUC_DEMO` ticket API line authorizes it. |

Refresh and retirement are the next roles. They are not in the catalog yet.
