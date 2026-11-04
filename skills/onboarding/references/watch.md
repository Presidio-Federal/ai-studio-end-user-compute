# Onboarding visit

Read `onboarding/metadata.json` first. `evidence_ref` is the last stamp. Read it. `File not found` is the first run. Do not search.

Do not call `get_folder_structure`. Do not pass `Internal directory` to built-in file tools.

This visit records enrollment. Collect does not assign a PreStage, investigate health, or retire. Assign runs only when the person authorizes it.

## Run the script

**First tool:** `read_file` `onboarding/metadata.json`. Then one `execute_command`, `execution_type: "mcp_orchestration"`. Use the path Studio shows for the attached `onboarding/scripts/visit_onboarding.py`. Copy it. The transcript may render it as `Internal directory`; that string is the python path, not a folder to list. Do not set `timeout`.

Each `execute_command` is a new container. In that container the workspace is the `file_explorer` folder beside `skills` on the path Studio shows for `visit_onboarding.py`. Copy that directory. Pass it as `--workspace`. Do not pass the relative name `file_explorer`, and do not `cd`.

```text
python3 <copied script path> collect --workspace <copied file_explorer directory>
python3 <copied script path> collect --workspace <copied file_explorer directory> --serial "<serial from the task line>"
```

The last stdout line is the summary. Then `annotate` under `execution_type: "standard"` when `stamp` is a path.

```text
python3 <copied script path> annotate --workspace <copied file_explorer directory> --stamp onboarding/2026-01-01T00-00-00Z.json --subjective "<why>" --objective "<what the record shows>" --assessment "<what it means>" --plan "<next nurse, or none>"
```

If stderr says `hai_mcp unavailable`, stop. Do not collect by hand.

## Assign

Only when the person names a serial and authorizes a PreStage assignment. One `execute_command`, `execution_type: "mcp_orchestration"`, same copied paths.

```text
python3 <copied script path> assign --workspace <copied file_explorer directory> --serial "<serial>"
python3 <copied script path> assign --workspace <copied file_explorer directory> --serial "<serial>" --prestage-name "<prestage>"
python3 <copied script path> assign --workspace <copied file_explorer directory> --serial "<serial>" --action unassign
```

The script does not write a stamp. Collect again to record the stage.
