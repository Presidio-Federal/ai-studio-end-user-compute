# Investigation visit

A line that asks about health, devices, an endpoint, a serial, a hostname, a username, or an event is authorization. Do not confirm.

When no endpoint is chosen, call the list tools that are attached. Show hostname, id, user, and source. Ask which one. Stop. Do not run the script. Do not assume a platform.

When one endpoint is chosen, this visit reads Jamf and Nexthink and records that endpoint. It does not open a ticket, send an MDM command, or run a Nexthink fix.

A chassis serial is `--serial`. A hostname is `--name`. A person, username, or email is `--user`. An unlabeled token is `--query`.

## Run the script

One `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `investigation/scripts/visit_investigations.py`. Copy it. Do not retype a path from memory. The transcript may render it as `Internal directory`; that is the real path. Do not set `timeout`. The call is the command and `execution_type` only.

Each `execute_command` is a new container. In that container the workspace is the `file_explorer` folder beside `skills` on the path Studio shows for `visit_investigations.py`. Copy that directory. Pass it as `--workspace`. Do not pass the relative name `file_explorer`, and do not `cd`.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial from the task line>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --name "<hostname from the task line>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --user "<username from the task line>"
python3 <copied script path> collect --workspace <copied file_explorer directory> --query "<unlabeled token>"
```

The last stdout line is the summary. A line above it from the runtime is not the result. Do not open the stamp or the metadata to fill the reply.

Then one `execute_command` with `execution_type: "standard"`, same copied paths. This replaces the four SOAP sentences. It does not edit the stamp. Skip it when the summary `stamp` is null.

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp investigations/2026-01-01T00-00-00Z.json --subjective "<why this visit>" --objective "<what this visit found, and the proof path>" --assessment "<the endpoint state>" --plan "<next check, or none>"
```

`--stamp` is the summary field `stamp`, copied exactly. It starts with `investigations/` and ends with `.json`. The date in the example is the shape, not a path to reuse. Do not pass the bare `watch_id`. Do not put a quote on the end of `--stamp`.

Each SOAP argument is one sentence, under 400 characters, with no JSON. `--objective` names the proof path. `--assessment` says what state the endpoint is in. On a quiet visit the proof path is the previous stamp.

If stderr says `hai_mcp unavailable`, stop. Do not collect by hand. Do not read `visit_investigations.py`.

## Reply

Use the summary line. No preamble.

```text
Visit: investigations
Result: <status>
Coverage: <coverage>
Proof: <stamp>
Summary: investigations/metadata.json
Trend: <delta>
Device: <name> <serial>
Lookup: <lookup>
Matches: <matches>
Issue: <issue>
Crashes: <crash_count>
Process: <top_process>
Management: managed <managed>, user <user>
Next: <plan>
```

When `quiet` is true, this visit added no stamp. Proof stays the previous path.
