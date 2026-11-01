# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

| Agent | Version | Model |
|-------|---------|-------|
| jamf-inventory-agent | 0.2.0 | MiniMax |
| investigation-agent | 0.5.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.2.0 | Catalog for the Jamf stamp, the investigations stamp, and the SOAP notes. Visit helpers live in `scripts/visit_common.py`. |
| jamf-inventory | 0.2.0 | Whether a Jamf computer exists, who it belongs to, and its management level. |
| investigation | 0.5.0 | Lists until one endpoint is chosen, then consolidates it. The reply ends with a plain summary of the finding and what a ticket would still need. |
