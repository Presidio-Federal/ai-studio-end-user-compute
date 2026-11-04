# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. `scripts/visit_tickets.py open` reads the investigation SOAP and stamp, finds or writes the EUC hardware asset, opens or reuses the incident on that CI, and writes the ticket stamp.

| Path | When |
|------|------|
| `tickets/<YYYY-MM-DDTHH-MM-SSZ>.json` | First run, and any later run whose incident number or state changed. Never overwritten. Never deleted. A quiet run does not add one. |
| `tickets/metadata.json` | Every run. SOAP only, plus `number` and `evidence_ref`. The incident row is not here. |

`read_file` filePath is the catalog path (`tickets/metadata.json`, `investigations/metadata.json`). Do not prefix `file_explorer/`. Do not call `get_folder_structure`. Do not pass `Internal directory` to built-in file tools. `File not found` means that file has not been written. Do not search for it.

Investigation reads this SOAP note, then replies to the API caller with the ticket number and the concise details. It does not open the incident.

Do not `write_file` these paths. Do not write `state/`. Do not write `investigations/`.
