# Jamf tools

The visit script calls these. The prompt does not.

| Tool | When the script calls it |
|------|--------------------------|
| `jamf_find_devices` | Every collect. With `--serial`, it passes `serial`. It also passes `filter` `hardware.serialNumber=="<serial>"` and merges the two results by Jamf id. Without `--serial`, it pages `page_size` 100. |
| `jamf_get_device` | Once per computer id. Sections: GENERAL, HARDWARE, USER_AND_LOCATION. |

The script does not call `jamf_get_device_health`. FileVault, disk, and OS health are outside this visit.

`jamf_wait_for_device` answers only whether a serial has appeared. It is not this management check. The script does not call it.

`jamf_list_mdm_commands` is out of this visit. The script does not call it.

## Which record is live

Serial is `hardware.serialNumber`. A filter on `general.serialNumber` is rejected by Jamf.

Two inventory records can share one serial. The live record has `managed` true and a last check-in. When several do, the latest check-in is the live one. The other record stays on the stamp. Its Jamf `id` is the stub. A hostname is a column. The relationship tag is `device:` plus the chassis serial.

A Jamf site name is a column the script does not store. A comment is not a site.

## What counts as a change

A later stamp is written when one of these moves: name, serial, assigned user, managed, supervised, user-approved MDM, MDM capable, or a computer appearing, disappearing, or gaining its first check-in.

`last_contact` is stored so a live record can be told from a stub. A newer check-in time alone does not open a stamp.

## Stop

If stderr says `hai_mcp unavailable`, stop. Report that line. Do not call these tools yourself. Do not write the chart.

Any other failure: the last stdout line is the result when it is JSON. If `stamp` is null, do not annotate.
