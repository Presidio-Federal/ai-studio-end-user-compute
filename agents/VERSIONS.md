# Prompt versions

Deployed model is **MiniMax** unless a row says otherwise. Sonnet only when the operator asks, or for sizing, risk, or intel — and the reason is recorded here.

| Agent | Version | Model |
|-------|---------|-------|
| jamf-inventory-agent | 0.1.0 | MiniMax |

## Skills

| Skill | Version | Note |
|-------|---------|------|
| workspace-handoff | 0.1.0 | Catalog for the Jamf stamp and the SOAP note. Visit helpers live in `scripts/visit_common.py`. |
| jamf-inventory | 0.1.0 | Read-only Jamf computer inventory. One orchestration script writes the stamp, then the SOAP note. |
