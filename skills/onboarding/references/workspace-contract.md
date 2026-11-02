# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. `scripts/visit_onboarding.py collect` writes the stamp. It uses attached tools. It does not assign a PreStage.

| Path | When |
|------|------|
| `onboarding/<YYYY-MM-DDTHH-MM-SSZ>.json` | First run, and any later run whose record changed. Never overwritten. Never deleted. A quiet run does not add one. |
| `onboarding/metadata.json` | Every run. SOAP only, plus `evidence_ref`. The device rows are not here. |

`read_file` filePath is the catalog path (`onboarding/metadata.json`). Do not prefix `file_explorer/`. `File not found` means that file has not been written. Do not search for it.

The next nurse reads this SOAP note. Operations and Investigation start after `stage` is `enrolled` or `managed`.

Do not `write_file` these paths. Do not write `state/`. Do not write another nurse's folder.
