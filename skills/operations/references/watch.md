# Operations visit

Read `operations/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

Do not call `get_folder_structure`. Do not pass `Internal directory` to built-in file tools.

This visit records in-life devices that are failing. Collect does not enroll, investigate one chosen endpoint, open a ticket, or treat. Treat runs only when the person authorizes it.

## Run the script

**First tool:** `read_file` `operations/metadata.json`. Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `operations/scripts/visit_operations.py`. Copy it. The transcript may render it as `Internal directory`; that string is the python path, not a folder to list. Do not set `timeout`.

Each `execute_command` is a new container. In that container the workspace is the `file_explorer` folder beside `skills` on the path Studio shows for `visit_operations.py`. Copy that directory. Pass it as `--workspace`. Do not pass the relative name `file_explorer`, and do not `cd`.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory>
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial from the task line>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --name "<hostname from the task line>"
```

The last stdout line is the summary. Then `annotate` under `execution_type: "standard"` when `stamp` is a path.

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp operations/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what the record shows>" --assessment "<what it means>" --plan "<next nurse, or none>"
```

If stderr says `hai_mcp unavailable`, stop. Do not collect by hand.

## Treat

Only when the person names a serial and authorizes a fix, or the API line is ticket-authorized. Read `tickets/metadata.json` and the investigation stamp first. If `recommended_treat` is not `disk`, stop. One `execute_command`, `execution_type: "mcp_orchestration"`, same copied paths.

```text
python3 <copied script path> treat --workspace <copied file_explorer directory> --serial "<serial>" --group "MCP-Remediate-Disk"
python3 <copied script path> treat --workspace <copied file_explorer directory> --serial "<serial>" --group "MCP-Remediate-Disk" --action remove
```

`--group` is the exact static group name. The script does not write a stamp. Collect again after check-in.
