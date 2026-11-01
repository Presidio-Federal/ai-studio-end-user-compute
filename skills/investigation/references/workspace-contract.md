# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. `scripts/visit_investigations.py collect` calls Jamf and Nexthink for one chosen endpoint and writes the stamp. It does not choose the endpoint.

| Path | When |
|------|------|
| `investigations/<YYYY-MM-DDTHH-MM-SSZ>.json` | First run, and any later run whose record changed. Never overwritten. Never deleted. A quiet run does not add one. |
| `investigations/metadata.json` | Every run. SOAP only, plus `evidence_ref`. The device rows are not here. |

`read_file` filePath is the catalog path (`investigations/metadata.json`). Do not prefix `file_explorer/`. `File not found` means that file has not been written. Do not search for it.

Do not `write_file` these paths. Do not write `state/`.
