# Investigation

First tool: `read_file` `investigations/metadata.json`. `File not found` is the first run. Do not search. Do not call `get_folder_structure`. Do not create a task plan. Do not pass `Internal directory` to built-in file tools.

`--workspace` is the `file_explorer` directory beside `skills` on the path Studio shows for the script. Paste it. Do not `cp` it.

No endpoint yet: use the list calls in `references/tools.md`. Ask which one. Do not run `collect`. Skip the list when the task line already named a serial, hostname, or username.

One endpoint chosen: one `execute_command`, `execution_type: "mcp_orchestration"`, `collect` with `--serial`, `--name`, or `--user`. Then say what the record means. Use `annotate` under `execution_type: "standard"` for that opinion.

Campaign-authorized: after collect, start Ticket, then **stop**. When Ticket has replied with an INC, `read_file` `tickets/metadata.json`, then `notify`. Do not read that file on the same turn you start Ticket.

```text
python3 <script path Studio showed> notify --workspace <file_explorer directory Studio showed>
```
