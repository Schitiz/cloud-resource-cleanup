## Coding summary

Lane WA-1 (test only): the notification helper cases moved out of `tests/test_cli_crc_parity.py`
into `tests/test_notify_crc_parity.py`. No production file, oracle or locked test was edited.

- **What is routed.** The 15 case names that called `get_msg`, `slack_lookup_user_by_email`,
  `get_user_groups_list`, `write_influxdb` and `ping_on_slack` (4 `get_msg_*`, `lookup_known`,
  `lookup_unknown`, `groups`, 4 `write_*`, 4 `ping_*`) now compare main's `CRC` methods
  (`load_legacy_crc()`) with `crc.core.report.get_msg`, `SlackNotifier` (user lookup, groups,
  `ping_owners` from `crc.notify.slack_owners`) and `InfluxNotifier.write`. Same grid as before
  (3 Slack/Influx failure variants x dry run x 4 Slack modes x 6 Influx modes, 144 scenarios per
  name, 2160 cases). Slack calls, Influx points, stdout and the result or error are compared.
- **Adapters deleted or shimmed.** None. `tests/helpers_wa1_notify.py` is new: a small settings
  object (clients, channel, Influx bucket and suffix; named `CRC` because the BUG-030 text prints
  the class name), `execute_current`, `current_get_msg`, `current_ping` (the BUG-033 pre-loop of
  main) and `scenario_grid`. The new file does not import `crc.cli.runner`.
- **How the CLI parity tests reach the cleaners.** Unchanged: `bridge.run_routed` with the route of
  the pair and a recording fake cleaner. In `tests/test_cli_crc_parity.py` only the moved blocks
  were removed (their `DIRECT` rows, the matching `DIRECT_ACTIONS` rows, `_slack_notifier`, the
  `SlackNotifier` import, one docstring paragraph and one comment). Constructor and
  `scan_instances_with_tag` cases are untouched (WA-2). Grep
  `\.(get_msg|slack_lookup_user_by_email|get_user_groups_list|write_influxdb|ping_on_slack)\(` on
  that file finds nothing.
- **Asserted divergences.**
  - BUG-030: no `influxdb_conn`, the write prints `'CRC' object has no attribute
    'resource_suffix'` on both sides (explicit test).
  - BUG-033: `ping_on_slack({"alice": 3})` fetches the groups, then fails on `len()`; one
    `usergroups_list` call on both sides (explicit test).
  - `get_msg(None)`: main raises `TypeError: object of type 'NoneType' has no len()`, the report
    function raises `TypeError: 'NoneType' object is not iterable`. Production keeps main's text
    through `crc.cli.notify._section`. Asserted per side.
  - `get_msg` with the word "Gone": main prints it (also in dry run); the current side takes an
    `Operation` and raises `KeyError: 'Gone'` mapping the word. Unreachable in production.
- **Left in `tests/test_cli_crc_parity.py` on the current `CRC`.** The `nic_none` and `vm_none`
  rows still run `notify_deleted_nic_via_slack` / `notify_deleted_vm_via_slack` on the current
  `CRC` (their old current-side action was `get_msg`, which is gone, so they now compare the
  `notify_*` methods like any unrouted row). They are not among the five methods; a later lane that
  removes the `notify_*` methods should route them. Constructor and scan cases stay with WA-2.
- **Test count.** Before 44411, after 44414 (`make check`, 44414 passed); the 2160 moved cases are
  equal in both files, plus 3 new tests (BUG-030, BUG-033, non-vacuous guard). Floor raised to
  44414 with `make raise-test-floor`; if WA-2 raises it as well, the integrator takes the higher.
- **Owner actions.** None.

## New bugs

None found. (`get_msg(None)` text above is a message difference on an input production never
passes: `crc/core/report.py:178`.)
