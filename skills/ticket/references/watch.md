# Ticket visit

First tool: `read_file` `tickets/metadata.json`. `File not found` is the first run. Continue. Do not search. Do not call `get_folder_structure`. Do not create a task plan. Do not pass `Internal directory` to built-in file tools.

Then `read_file` `investigations/metadata.json`. `File not found` means Investigation has not written here. Stop.

This visit opens the incident. It does not investigate, enroll, or treat.

## Run the script

Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `ticket/scripts/visit_tickets.py`. Paste it. Do not set `timeout`.

`--workspace` is the `file_explorer` directory beside `skills` on that path. Paste it. Do not `cp` it. Do not make a second tree.

```text
python3 <script path Studio showed> open --workspace <file_explorer directory Studio showed>
python3 <script path Studio showed> open --workspace <file_explorer directory Studio showed> --serial "<serial from the investigation stamp>"
```

The last stdout line is the summary. Then `annotate` under `execution_type: "standard"` when `stamp` is a path.

```text
python3 <script path Studio showed> annotate --workspace <file_explorer directory Studio showed> --stamp tickets/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<ticket number and what it covers>" --assessment "<what it means>" --plan "<Investigation replies to the caller>"
```

If stderr says `hai_mcp unavailable`, stop. Do not open by hand.
