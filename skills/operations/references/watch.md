# Operations visit

Read `operations/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

This visit records in-life devices that are failing. It does not enroll, investigate one chosen endpoint, open a ticket, or treat.

## Run the script

One `execute_command`, `execution_type: "mcp_orchestration"`. Copy the path Studio shows for `scripts/visit_operations.py`. Pass the `file_explorer` directory beside `skills` as `--workspace`. Do not set `timeout`.

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
