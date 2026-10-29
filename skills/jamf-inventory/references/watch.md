# Jamf inventory visit

A line that asks for Jamf inventory, an enrolled Mac, a serial, or device status is authorization. Do not confirm.

This visit reads Jamf computers and writes the chart. It does not send an MDM command, assign a PreStage, change a Jamf account, or call ServiceNow.

## Run the script

One `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `jamf-inventory/scripts/visit_jamf.py`. Copy it. Do not retype a path from memory. The transcript may render it as `Internal directory`; that is the real path. Do not set `timeout`. The call is the command and `execution_type` only.

Each `execute_command` is a new container. In that container the workspace is the `file_explorer` folder beside `skills` on the path Studio shows for `visit_jamf.py`. Copy that directory. Pass it as `--workspace`. Do not pass the relative name `file_explorer`, and do not `cd`.

Pass `--serial` only when the task line names one. Omit it to list the computers.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory>
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial from the task line>"
```

The last stdout line is the summary. A line above it from the runtime is not the result. Do not open the stamp or the metadata to fill the reply.

Then one `execute_command` with `execution_type: "standard"`, same copied paths. This replaces the four SOAP sentences. It does not edit the stamp. Skip it when the summary `stamp` is null.

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp jamf/2026-01-01T00-00-00Z.json --subjective "<why this visit>" --objective "<what this visit found, and the proof path>" --assessment "<one verdict>" --plan "<next check, or none>"
```

`--stamp` is the summary field `stamp`, copied exactly. It starts with `jamf/` and ends with `.json`. The date in the example is the shape, not a path to reuse. Do not pass the bare `watch_id`. Do not put a quote on the end of `--stamp`.

Each SOAP argument is one sentence, under 400 characters, with no JSON. `--objective` names the proof path. On a quiet visit the proof path is the previous stamp.

If stderr says `hai_mcp unavailable`, stop. Do not collect by hand. Do not read `visit_jamf.py`.

## Reply

Use the summary line. No preamble.

```text
Visit: jamf
Result: <status>
Coverage: <coverage>
Proof: <stamp>
Summary: jamf/metadata.json
Trend: <delta>
Computers: <computers>
Live: <live_name> <serial> id <live_id> managed <managed> <severity>
Stub: <stubs, omit this line when stubs is empty>
Next: <plan>
```

When `quiet` is true, this visit added no stamp. Proof stays the previous path. When two records share the serial, Live is the managed checking-in id and Stub is the other id.
