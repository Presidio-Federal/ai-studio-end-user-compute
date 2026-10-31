# Investigation tools

Before an endpoint is chosen, the agent calls whichever list tools are attached. It does not invent tools and it does not assume a platform.

After one endpoint is chosen, the visit script calls these. The prompt does not call them again on that turn.

| Tool | When the script calls it |
|------|--------------------------|
| `jamf_find_devices` | Every collect. `--serial` passes `serial` and also `filter` `hardware.serialNumber=="<serial>"`. `--name` passes `name`. `--user` passes `username`, or `email` when the value contains `@`. |
| `jamf_get_device` | Once, for the Jamf id that is managed and has checked in. Sections: GENERAL, HARDWARE, USER_AND_LOCATION. |
| `nexthink_nql_execute` | `#mcp_user_lookup` when the subject is a username. `#mcp_device_lookup` with `device_name` and `user_name`. Then `#mcp_device_health`, `#mcp_app_crashes` with `binary_name` `"*"`, and `#mcp_device_top_processes` for the device name that was found. |

A username lookup passes `device_name` `"*"` and the username as `user_name`. When that returns more than one device, the script keeps the one that matches the Jamf hostname, or the one seen most recently, and records the count in `matches`.

`#mcp_device_health` and `#mcp_device_top_processes` take one real device name. The script does not pass `"*"` for those.

`--query` is an unlabeled token for one chosen endpoint. The script tries it as a serial, then as a hostname, then as a username. The script does not list a fleet. Listing is the agent's job, with the tools attached to it, before this script runs.

The script does not call `jamf_get_device_health`, `jamf_send_mdm_command`, `nexthink_execute_remote_action`, `nexthink_trigger_workflow`, `nexthink_trigger_campaign`, or any `snow_` tool.

## What the row holds

Jamf supplies the chassis serial, the assigned user, and managed, supervised, user-approved MDM, and MDM capable. Nexthink supplies the Collector UID, platform, last seen, crash rows, the top process, and up to 12 health signals. `lookup` is `serial`, `name`, or `user`.

`device:` is the chassis serial. A hostname is a column. A username is a column. A comment is not a site.

## What counts as a change

A later stamp is written when the issue, serial, assigned user, managed flag, crash count, top process, or health signal text moves.

`last_seen` is stored. A newer last-seen time alone does not open a stamp.

## Issue

| Issue | When |
|-------|------|
| `application_crashes` | The crash query returned rows. |
| `experience_recorded` | Health returned rows and the crash query did not. |
| `experience_unread` | The device is in both systems and a Nexthink read failed. |
| `not_in_jamf` | Nexthink has the device and Jamf does not. |
| `not_in_nexthink` | Jamf has the device and Nexthink does not. |
| `no_signal` | Both systems have the device and neither crashes nor health rows came back. |
| `unknown` | Neither system has the device. |

## Stop

If stderr says `hai_mcp unavailable`, stop. Report that line. Do not call these tools yourself. Do not write the chart.

Any other failure: the last stdout line is the result when it is JSON. If `stamp` is null, do not annotate.
