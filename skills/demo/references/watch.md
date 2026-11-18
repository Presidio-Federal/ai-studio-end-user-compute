# Demo visit

First tool: `read_file` `demo/metadata.json`. `File not found` is the first run. Do not search. Do not call `get_folder_structure`. Do not create a task plan. Do not pass `Internal directory` to built-in file tools.

`--workspace` is the `file_explorer` directory beside `skills` on the path Studio shows for the script. Paste it. Do not `cp` it.

No endpoint yet: use the list calls in `references/tools.md`. Ask which one. Do not run `start`. Skip the list when the task line already named a hostname, username, serial, or SID.

One endpoint chosen: one `execute_command`, `execution_type: "mcp_orchestration"`, `start` with `--name`, `--user`, `--serial`, or `--sid`. Then say what the record means. Use `annotate` under `execution_type: "standard"` for that opinion.

```text
python3 <script path Studio showed> start --workspace <file_explorer directory Studio showed> --name "<hostname>"
```
