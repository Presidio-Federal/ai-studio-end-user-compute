# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

| Agent | Version | Model |
|-------|---------|-------|
| jamf-inventory-agent | 0.2.0 | MiniMax |
| investigation-agent | 0.7.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.2.0 | Catalog for the Jamf stamp, the investigations stamp, and the SOAP notes. Visit helpers live in `scripts/visit_common.py`. |
| jamf-inventory | 0.2.0 | Whether a Jamf computer exists, who it belongs to, and its management level. |
| investigation | 0.7.0 | The agent lists with MCP tools until one endpoint is chosen. `collect` then calls Jamf and Nexthink and fills the schema. |
