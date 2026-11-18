# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

Nurses own a lifecycle role. Tools attached to that nurse are how it collects. They are not the identity.

| Agent | Version | Model |
|-------|---------|-------|
| onboarding-agent | 0.3.0 | MiniMax |
| jamf-inventory-agent | 0.2.0 | MiniMax |
| investigation-agent | 0.13.0 | MiniMax |
| ticket-agent | 0.3.2 | MiniMax |
| operations-agent | 0.6.0 | MiniMax |
| demo-agent | 0.3.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.6.0 | Catalog for onboarding, Jamf inventory, investigations, tickets, operations, and demo stamps plus SOAP notes. Visit helpers live in `scripts/visit_common.py`. |
| onboarding | 0.3.0 | Enrollment into MDM. Collect is read-only. Jamf 404 is a gap, not an unattached tool. Assigns a PreStage only when authorized. |
| jamf-inventory | 0.2.0 | Whether a Jamf computer exists, who it belongs to, and its management level. |
| investigation | 0.13.0 | Catalog paths only. After collect, start Ticket and wait for its INC reply, then `notify` sends `#mcp_triage_result`. Do not `get_folder_structure`. `--workspace` is the Studio `file_explorer` tree, not a copy. |
| ticket | 0.3.2 | Same catalog as Investigation. `tickets/metadata.json` missing is the first run. Copies the investigation pack onto the INC with `EUC_DEMO`. Company comes from `u_euc_demo` hardware. |
| operations | 0.6.0 | Reads open `EUC_DEMO` incidents. Ticket-authorized computer: collect, disk treat, then resolve the INC. |
| demo | 0.3.0 | `start` triggers workflow `#mcp_investigate_on_consent`. The campaign stays Workflow. Fix now calls Investigation. |

Refresh and retirement are the next roles. They are not in the catalog yet.
