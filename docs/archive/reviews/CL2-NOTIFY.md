## Coding summary

Lane CL2-NOTIFY (test-only): `tests/test_notify_parity.py` no longer runs the current legacy CLI
notify code. No production file, oracle, locked test or other test file was edited.

- **What is routed.** Every Slack and Influx assertion of the file now reaches the notifiers the
  way production does. `tests/helpers_cl2_notify.py` builds the real `crc.cli.runner.CRC` only as the
  context object, asks `crc.cli.bridge.build_notifiers` for `SlackNotifier` / `InfluxNotifier`, and
  `routed_run` lets `crc.core.engine.run` build the report from a stub cleaner's plan and result
  (`Report.from_plan` / `from_result`: related NIC and disk sections, the Azure VM `slack_ids`,
  `link_names` on disks, by-owner pings). `routed_call` runs a bare notifier call (user lookup,
  group list, one `InfluxNotifier.write`) where the oracle method has no engine counterpart.
- **Legacy side.** `tests.helpers_oracle.load_legacy_crc()` (`tests/legacy/crc_main.txt`) replaces
  `crc.py` loaded from the working tree. `tests/legacy_crc_notify_reference.txt` is no longer read by
  this file (other docs still mention it; I did not touch them).
- **Adapters deleted or shimmed.** None; nothing under `crc/` changed.
- **How the parity tests reach the cleaners.** They do not drive any cleaner: the stub cleaner
  returns the ids of each case, so only the report and notifier path is compared. The CRC
  `notify_*`, `ping_on_slack`, `write_influxdb`, `slack_lookup_user_by_email`,
  `get_user_groups_list` and `get_msg` methods are no longer called on the current `CRC`.
- **Run-log lines.** This file asserts none of RUN START, REGION, ACTION, SKIPPED, ERRORS, RESULT
  (the engine is called directly, not `run_routed`), so no frozen run-log data was needed.
- **Inputs the engine cannot produce.** The oracle outcome is asserted against frozen data
  (`UNROUTED` in the test file, plus explicit values in the tests):
  - `disk-tuple`, `disk-none` (silently not notified), `vm-without-ids` (`TypeError ... has no len()`);
  - `get_msg(..., None)` (`TypeError: object of type 'NoneType' has no len()`), compared to
    `crc.core.report.get_msg` for every list case (text plus the printed newline);
  - bad owner groups (`None`, `int`, a list): oracle error and the single `usergroups_list` call are
    asserted as before; the routed run fails earlier, when the `Plan` freezes the groups, with a
    `TypeError`/`AttributeError`, no Slack call and no output (fail closed, unreachable from real
    cleaners). The exact routed message differs from the oracle's, so only its type is asserted.
- **Fixed-bug divergences.** None found: every compared case is equal to the oracle. BUG-028,
  BUG-030, BUG-033, BUG-034 quirks stay visible in the equal outcomes (asserted as before).
- **Test count.** Before 44400 (995 in this file), after 44400 (995 in this file); floor unchanged,
  `make raise-test-floor` not needed. `make check` green.
- **Owner actions.** None. Once no other test reads `tests/legacy_crc_notify_reference.txt` it can
  be removed by an owner (it is a hash-locked/oracle-style file I must not edit).
- **Lint note.** The only place left that names the current CRC is `context_crc` in the helper,
  as the context object the bridge reads.

## New bugs

None.
