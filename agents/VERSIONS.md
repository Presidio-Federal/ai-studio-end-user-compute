# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

Nurses own a lifecycle role. Tools attached to that nurse are how it collects. They are not the identity.

| Agent | Version | Model |
|-------|---------|-------|
| onboarding-agent | 0.1.0 | MiniMax |
| jamf-inventory-agent | 0.2.0 | MiniMax |
| investigation-agent | 0.7.0 | MiniMax |
| operations-agent | 0.1.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.4.0 | Catalog for onboarding, Jamf inventory, investigations, and operations stamps plus SOAP notes. Visit helpers live in `scripts/visit_common.py`. |
| onboarding | 0.1.0 | Enrollment into MDM or the directory. Collect uses attached Jamf PreStage/wait and Intune/Entra tools. Does not assign. |
| jamf-inventory | 0.2.0 | Whether a Jamf computer exists, who it belongs to, and its management level. |
| investigation | 0.7.0 | The agent lists with MCP tools until one endpoint is chosen. `collect` then calls attached Jamf and Nexthink tools and fills the schema. |
| operations | 0.1.0 | In-life devices that are failing experience or compliance. Collect uses attached watchlist, vitals, MDM health, and Intune compliance tools. Read-only. |

Refresh and retirement are the next roles. They are not in the catalog yet.
