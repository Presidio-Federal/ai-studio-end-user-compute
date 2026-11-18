# Tools

The script calls these. The agent does not.

## `snow_query_table`

Read-only. Arguments: `table`, `query`, `fields`, `limit`, `offset`.

Computers are `alm_hardware` where `company.name` is Disney EUC, `u_euc_demo` is true, and `model_category.name` is Computer. Parts are the same company and flag with `u_parent_serial` set. Fields are `sys_id`, `serial_number`, `u_order_number`, `u_parent_serial`, and `model.model_number`.

The request is `sc_request` by `number`. Fields are `number`, `u_site`, and `u_warehouse`. The site name and coordinates come from `cmn_location` for `u_site`. The warehouse name comes from `alm_stockroom` for `u_warehouse`. The stockroom is not the site.

`sc_req_item` for that request supplies `u_pid`, `u_components`, and `price`. A component line is `pid|qty|unit_price|description`. The third field is the unit price. Zero stays.

## `jamf_find_devices` and `jamf_get_device`

One computer by serial. The detail sections are GENERAL, HARDWARE, OPERATING_SYSTEM, and USER_AND_LOCATION. Hostname, user, OS, last check-in, and managed come from that record. They do not replace serial, request, site, or warehouse.

## `intune_list_intune_devices`

`name` is the Jamf hostname. `top` is 25. A row counts only when `device_name` equals that hostname. It can fill OS and last check-in when Jamf did not, and it marks the device managed.

## `nexthink_nql_execute`

Two calls, both before `elasticsearch_bulk` or `elasticsearch_update`. `device_name` is the Jamf hostname. Do not pass `*`.

`#mcp_device_lookup` takes `device_name` and `user_name` `*`. A returned row adds Nexthink on `euc_sources`. It does not carry the DEX score.

`#mcp_device_vitals` takes `device_name` only. `dex_score` is the column `dex_score`, `dex.score`, or `score`. That value is written on the `euc_operations` document. It does not change the site or the request.

## `elasticsearch_search`

Read current documents before a later copy, and answer a question. Arguments: `index` `euc_operations` or `euc_sources`, `query` `{"ids": {"values": [...]}}`, `size` the number of ids. A question with no serial uses `{"term": {"stage": "in_service"}}` and `size` 20.

## `elasticsearch_bulk`

The first copy of serials that are not already in `euc_operations`. One call. Each item is `index` `euc_operations`, `id` the serial, and `doc`. `doc.stage` is `in_service`. `doc.request` is the REQ. `doc.site` is the request site. A later copy does not call this for an id that already exists.

## `elasticsearch_update`

One document. A later copy calls it when the source and the stored document differ. Fields left out stay. A missing `euc_sources` document is created with `sources` set to the feeds that named that serial. This does not create an index.

## `elasticsearch_append`

Add one feed name to `sources` on an existing `euc_sources` document. Arguments: `index` `euc_sources`, `id` the serial, `field` `sources`, `value` the feed name. `ServiceNow`, `Jamf`, `Intune`, and `Nexthink` stay once they are present. A part is not a sources document.
