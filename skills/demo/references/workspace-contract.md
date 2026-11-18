# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. `scripts/visit_demos.py start` resolves one device, starts `#mcp_investigate_on_consent`, and writes the demo stamp. That workflow sends `#mcp_fix_consent`.

| Path | When |
|------|------|
| `demo/<YYYY-MM-DDTHH-MM-SSZ>.json` | First run, and any later run whose request id or campaign status changed. Never overwritten. Never deleted. A quiet run does not add one. |
| `demo/metadata.json` | Every run. SOAP only, plus `campaign` and `evidence_ref`. The device row is not here. |

`read_file` filePath is the catalog path (`demo/metadata.json`). Do not prefix `file_explorer/`. Do not call `get_folder_structure`. Do not create a task plan. Do not pass `Internal directory` to built-in file tools. `File not found` means that file has not been written. Do not search for it. `--workspace` is this same tree. Do not `cp` it.

Do not `write_file` these paths. Do not write `state/`. Do not write `investigations/` or `tickets/`.
