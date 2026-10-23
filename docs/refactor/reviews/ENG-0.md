## Coding summary

Lane ENG-0 (branch `eng/bridge`): the bridge from the CLI to `crc.core.engine`, with AWS `keypair` routed end to end as the pattern. Partial state, green: everything else keeps the legacy path.

**Routed**: `aws` / `keypair` only. `crc/cli/routes/aws.py` holds `ROUTES`; `azu.py`, `gcp.py`, `oci.py` exist with empty tables. `crc/cli/bridge.py` (`route_for`, `is_routed_kind`, `run_routed`, `build_registry`, `build_notifiers`) builds the `RunContext` and a one pair `Selection` from the parsed flags and calls `crc.core.engine.run` with the registered cleaner. `dispatch._run_handler` checks the route first, then the legacy handler; `logger.begin` / `finish` still wrap every pair, so RUN START / RESULT, validate_targets, the cloud-all skip and exit codes are unchanged. The Slack then Influx notifiers are the existing `crc.notify.SlackNotifier` (fail open False) and `InfluxNotifier` (fail open True); `build_notifiers` adds each only when its client is set, and none when `Route.notify` is False (the place for `vpc`, BUG-084).

**Adapters deleted or shimmed**: `crc/aws/keypairs/adapter.py` (`KeyPairs`), `KeyPairRuntime`, `CRC.delete_keypairs`, the `_keypair` handler and the `KeyPairs` re-export of `crc.py` are deleted. No shims: Disk, SpotInstanceRequests and the azure/gcp/oci SpotVM adapters are untouched, so the 5 hash-locked tests are untouched and pass. The keypair cleaner's `plan()` now logs the `would_delete` actions per region in a dry run (the engine never calls `apply()` then), which keeps the dry-run RESULT counters identical.

**How the CLI parity tests reach the cleaners**: `tests/helpers_cli_routes.py` (`FakeCleaners`) registers a recording fake cleaner for every routed pair in a `Registry` and patches `bridge.build_registry` (and `bridge.build_notifiers` to no notifiers), both looked up at call time. `test_cli_main_parity.py` (`ROUTED_CALLS`, `install_routed_fakes`) records the same `crc.delete_keypairs <cloud> [name_regex, exception_regex, age]` event from `context.options` and the same `crc_fail` error, so the oracle events compare equal and the table is not vacuous. `test_cli_logger.py`, `test_cli_logging_init.py`, `test_cli_dispatch_fix.py` and `test_core_selection.py` use the same seam. `tests/test_cli_bridge_parity.py` (new) runs the oracle `CRC.delete_keypairs` and `bridge.run_routed` on the same fake Slack and Influx clients over dry run x Slack mode x Influx mode x id sets and error cases: Slack calls, Influx calls, stdout and error are equal. `tests/test_aws_keypair_parity.py` now drives the Cleaner through `engine.run` against the oracle (`aws_keypairs.txt`); the delete order and delete calls are equal, later-region listing errors only ever delete less.

**Oracle note**: `tests/legacy/crc_main.txt` does `from crc.aws.keypairs import KeyPairs` at import. It cannot be edited, so the parity tests that load it call `tests.helpers_cli_routes.provide_legacy_keypairs()` (an empty stand-in class, replaced by fakes before use) and the subprocess `RUN_ORACLE` in `test_cli_main_parity.py` sets it. Every future adapter deletion needs the same stand-in for its name.

**BUGS.md / CLEANUP_SAFETY.md**: one new row BUG-383 (low group end, fixed in ENG-0) and one bullet under "Failure handling" in CLEANUP_SAFETY.md (there is no explicit plan/apply section); nothing else edited in either.

**Test count**: before 43075 (floor), after 43077; floor raised with `make raise-test-floor`.

**Owner actions**
- Review and swap in/relock the Cleaner-based copies of the 5 locked tests: not written in this lane (see "Left to do").
- Docs lane: `crc/core/README.md` still says the CLI runs the adapters and engine wiring is deferred; `docs/refactor/STATUS.md` lines about `KeyPairs` are stale; PLAN.md untouched.

## Left to do (not done in this lane, time)

- Route AWS `ip`, `kms`, `snapshot` (the "if time allows" part). Pattern: `crc/cli/README.md`, Extension Rules, item 3. Snapshot needs `Route.notify`/label handling: today's `Snapshot` branch prints a message and sends no Slack or Influx (BUG-009, BUG-084), so route it only with `notify=False` and the same print.
- The 5 `tests/test_<name>_engine.py` Cleaner copies of the locked safety tests (aws Disk, aws SpotInstanceRequests, azure/gcp/oci SpotVM). They are not needed yet because those adapters were not touched; the locked tests still build the adapters and pass.
- The disk route will need `Route.precheck` for the AWS opt-in gate, and a decision for `delete_disks`, which sends Slack and Influx before it re-raises a `delete()` error, while the engine skips notifiers when `apply()` raises (difference to resolve in the disk lane).
- The Azure VM route also sends the NIC Slack message after the VM message (`notify_deleted_vm_via_slack`); the engine report has to carry it.

## New bugs

- `crc/cli/notify.py:~113`: `CRC.notify_deleted_keypair_via_slack` is now dead code in production (kept only because `test_cli_crc_parity.py` still exercises it).
- No other new bugs found.
