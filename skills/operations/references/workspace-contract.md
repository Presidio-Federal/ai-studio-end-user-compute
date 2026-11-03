# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. `scripts/visit_operations.py collect` writes the stamp. Treat changes Jamf only when authorized and does not write a stamp.

| Path | When |
|------|------|
| `operations/<YYYY-MM-DDTHH-MM-SSZ>.json` | First run, and any later run whose record changed. Never overwritten. Never deleted. A quiet run does not add one. |
| `operations/metadata.json` | Every run. SOAP only, plus `evidence_ref`. The device rows are not here. |

`read_file` filePath is the catalog path (`operations/metadata.json`). Do not prefix `file_explorer/`. `File not found` means that file has not been written. Do not search for it.

The next nurse reads this SOAP note. Investigation reads it when a failing device needs a deeper look. Refresh reads it when the plan is a replacement.

Do not `write_file` these paths. Do not write `state/`. Do not write another nurse's folder.
