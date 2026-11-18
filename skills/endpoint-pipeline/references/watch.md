# Endpoint operations

A request to sync, update, refresh, or copy endpoints is authorization. The sentence does not have to match one line. A question is a read of what is already on `euc_operations`. Do not confirm. Do not enroll, ship, or install.

Do not `read_file` the note or a stamp. A catalog path resolves to `/app/<path>` and is denied. The script reads the stamp from `--workspace`.

One `execute_command`, `execution_type: "mcp_orchestration"`. Do not pass timeout. Copy the path Studio shows for `endpoint-pipeline/scripts/visit_endpoints.py`. The workspace is the `file_explorer` directory beside `skills` on that path. Pass it as `--workspace`. Do not `cd`.

A question:

```text
python3 <copied script path> ask --workspace <copied file_explorer directory>
```

Add `--serial` when the question names one.

A sync, with no serial, copies the computers ServiceNow already has:

```text
python3 <copied script path> sync --workspace <copied file_explorer directory>
```

When the task names one serial:

```text
python3 <copied script path> sync --workspace <copied file_explorer directory> --serial SERIAL123456
```

Reply from the last stdout line. If stderr says `hai_mcp unavailable`, report that line and stop.
