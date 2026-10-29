# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. The script is the writer.

| Path | When |
|------|------|
| `jamf/<YYYY-MM-DDTHH-MM-SSZ>.json` | First visit, and any later visit whose computers changed. Written first. Never overwritten. Never deleted. A quiet visit does not add one. |
| `jamf/metadata.json` | Every visit, including a quiet visit and a failed read. SOAP only, plus `evidence_ref`. `keys` is `[]`. |

`read_file` filePath is the catalog path (`jamf/metadata.json`). Do not prefix `file_explorer/`. Do not list `/shared_workspace/HAI-ASSISTANTS-WORKSPACES`. `File not found` means that file has not been written.

The first stamp is a baseline of the computers in scope. A later stamp holds the computers that changed, `removed`, and `vs_prior.changed`. The script folds the earlier stamps through `evidence_ref` to know the estate. That fold is not written.

A failed Jamf read writes no stamp, leaves `evidence_ref` where it was, and does not advance `last_collected_at`.

Do not `write_file` these paths from the prompt. Do not write `state/`.
