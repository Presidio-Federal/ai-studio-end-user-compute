# Workspace contract

Catalog: **`workspace-handoff`**. This skill owns the schema and the example. The script is the writer.

| Path | When |
|------|------|
| `endpoint-operations/<YYYY-MM-DDTHH-MM-SSZ>.json` | First copy, and any later copy whose computers changed. Written first. Never overwritten. Never deleted. A quiet copy does not add one. |
| `endpoint-operations/metadata.json` | Every copy, including a quiet copy and a failed read. SOAP only, plus `evidence_ref`. `keys` is `[]`. |

`read_file` filePath is the catalog path (`endpoint-operations/metadata.json`). Do not prefix `file_explorer/`. `File not found` means that file has not been written.

The first stamp is a baseline of the computers in scope. A later stamp holds the computers that changed and `vs_prior.changed`. The rows are not copied onto the metadata note.

A failed ServiceNow or Elasticsearch read writes no stamp and does not advance `last_collected_at`.

Do not `write_file` these paths from the prompt. The Elasticsearch documents are not a second copy of the stamp.
