# Investigation

Read `investigations/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

Do not call `get_folder_structure`. Do not pass `Internal directory` to built-in file tools.

No endpoint yet: use the list calls in `references/tools.md`. Ask which one. Do not run `collect`. Skip the list when the task line already named a serial, hostname, or username.

One endpoint chosen: one `execute_command`, `execution_type: "mcp_orchestration"`, `collect` with `--serial`, `--name`, or `--user`. Then say what the record means. Use `annotate` under `execution_type: "standard"` for that opinion.

Campaign-authorized: after collect, Ticket opens the incident from this SOAP. Then `notify` under `execution_type: "standard"`. That last stdout line is the reply to the API caller.

```text
python3 <copied script path> notify --workspace <copied file_explorer directory>
```
