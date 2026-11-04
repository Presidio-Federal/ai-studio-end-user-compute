# Ticket visit

Read `tickets/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

Then read `investigations/metadata.json`. That SOAP is the source. Read the stamp `evidence_ref` names when you need the serial or hostname. `File not found` means Investigation has not written. Stop.

Do not call `get_folder_structure`. Do not pass `Internal directory` to built-in file tools.

This visit opens the incident. It does not investigate, enroll, or treat.

## Run the script

**First tool:** `read_file` `investigations/metadata.json`. Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `ticket/scripts/visit_tickets.py`. Copy it. The transcript may render it as `Internal directory`; that string is the python path, not a folder to list. Do not set `timeout`.

Each `execute_command` is a new container. In that container the workspace is the `file_explorer` folder beside `skills` on the path Studio shows for `visit_tickets.py`. Copy that directory. Pass it as `--workspace`. Do not pass the relative name `file_explorer`, and do not `cd`.

```text
python3 <copied script path> open --workspace <copied file_explorer directory>
python3 <copied script path> open --workspace <copied file_explorer directory> --serial "<serial from the investigation stamp>"
```

The last stdout line is the summary. Then `annotate` under `execution_type: "standard"` when `stamp` is a path.

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp tickets/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<ticket number and what it covers>" --assessment "<what it means>" --plan "<Investigation replies to the caller>"
```

If stderr says `hai_mcp unavailable`, stop. Do not open by hand.
