---
name: onboarding
version: "0.1.0"
description: "v0.1.0 — Get a device into management (Jamf PreStage/wait or Intune/Entra). Writes onboarding stamps. Does not assign, investigate, or retire."
---

# Onboarding

Read `onboarding/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

You own enrollment: pull a device into MDM or the directory. A line that asks for onboarding, PreStage, ADE, Autopilot, Intune, Entra, or whether a serial has enrolled is authorization. Do not confirm. You do not investigate health. You do not refresh or retire. You do not open a ticket. You do not assign a PreStage or change a deployment group unless the person authorizes it. This collect does not assign.

## Collect

One `execute_command`, `execution_type: "mcp_orchestration"`. Copy the path Studio shows for `scripts/visit_onboarding.py`. Pass the `file_explorer` directory beside `skills` as `--workspace`. Do not set `timeout`.

Omit filters to record what is waiting and what is already enrolled. Pass `--serial` when the task line names one chassis.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory>
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial>"
```

The script uses the tools attached to this agent. A missing tool is a gap, not a halt. It fills the schema and writes the stamp and a factual SOAP note. The last stdout line is the result. You then say what it means. If stderr says `hai_mcp unavailable`, stop.

To replace the SOAP sentences with your opinion, one `execute_command`, `execution_type: "standard"`, same paths:

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp onboarding/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what the record shows>" --assessment "<what it means>" --plan "<next nurse, or none>"
```

`--stamp` is the summary field `stamp`. Each SOAP argument is one sentence, under 400 characters, with no JSON.

## Files

| Path | Kind |
|------|------|
| `onboarding/<stamp>.json` | The record. First run is a baseline. Later runs are the delta. Never overwrite. |
| `onboarding/metadata.json` | SOAP note. `evidence_ref` names the latest stamp. |

Schema and example: `schemas/onboarding-visit.schema.json`, `schemas/onboarding-metadata.schema.json`, `examples/onboarding-visit.example.json`, `examples/onboarding-metadata.example.json`. `device:` is the chassis serial. A hostname is a column. A username is a column.

Do not `write_file` those paths. Do not write `state/`. Do not write `operations/` or `investigations/`.
