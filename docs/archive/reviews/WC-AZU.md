## Coding summary

Lane WC-AZU: delete the dead Azure adapter classes `IP`, `NIC` and `Disk`.

- **Routed:** nothing new to route. `ip`, `nic` and `disk` already run through `crc/cli/bridge.py`, `crc/cli/routes/azu.py` and the registered cleaners (`azure`/`ip`, `azure`/`nic`, `azure`/`disk`).
- **Deleted:** `crc/azu/ip/adapter.py` (`IP`), `crc/azu/nic/adapter.py` (`NIC`), `crc/azu/disk/adapter.py` (`Disk`), their package re-exports and their README Public API lines. `git grep` showed no production user: only tests built them (`crc/cli/scan.py` uses the VM adapters, which stay). The VM and SpotVM classes and the five hash-locked safety tests are untouched.
- **Tests retargeted (no case dropped, no comparison loosened):** `test_azure_{ip,nic,disk}_parity.py`, `test_azure_{ip,nic,disk}.py`, `test_azure_{ip,nic,disk}_fix.py` and `test_azure_logger.py` now drive the registered Cleaner through `crc.core.engine.run` (new helper `tests/helpers_wc_azu_engine.py`: `engine_run`, `candidate_ids`). Every parity case still runs against the frozen oracle in `tests/legacy/azu_{ip,nic,disk}.txt` and asserts SDK calls (per kind), results, log lines, stdout and errors. BUG-NNN divergences (BUG-013/074/076/077 for IP, BUG-111/113/114 for NIC, BUG-172/174 for disk) are asserted as before. The direct-protocol tests (`test_cleaner_protocol_matches_main`) stay and now share one assertion helper with the engine test for disk.
- **Constructor/attribute cases ported:** the adapter-only tests (`get_deleted`, `count`, `delete_count`, `Disk.default_disk_state`, `adapter.clock`, repeated `delete()` accumulation) now assert the engine outcome: `candidate_ids`, report section ids, `DEFAULT_DISK_STATES`, `now` passed in the `RunContext`, and two engine runs giving the same calls and log lines as the oracle's two `delete()` calls (the oracle accumulates names, the engine starts afresh each run).
- **READMEs trimmed:** `crc/azu/README.md`, `ip/`, `nic/`, `disk/` (adapter wording, rung names, refactor history, `FILTER_VARIANTS.md` and `PLAN.md` links removed); `spot_vm/` and `vm/` READMEs text only (rung names, history, `FILTER_VARIANTS.md` link, "as on main" removed; the `VM` and `SpotVM` API lines stay because those classes still exist).
- **Test count:** floor 44415 before, 44415 after (ARCH-008 green; tests were renamed or retargeted one for one, none added or removed). `make check` is green (ruff, mypy, lint-imports, ARCH rules, SAF-LOCK).
- **CLI parity tests:** not touched in this lane.

## Allowed behaviour change, seen in the retargeted tests

The cleaner plans every resource before it mutates, so a listing or selection error raised mid-listing (IP `iteration-error-mid-listing`, NIC `iteration-error-mid-listing` and `name-none-after-earlier-delete`, disk `iteration-error-mid-listing` and `created-none-error`) now stops the pair before any delete. Each is asserted in an `ENGINE_QUIRKS` table next to the oracle outcome. Fewer deletes, never more.

## Log line order (not in the allowed list, flagged for the owner)

On the engine path the `REGION` line is logged before the `ACTION` lines for NIC and disk (and in a dry run for IP), because `plan()` logs it; the adapters logged `ACTION` lines first. `tests/test_azure_logger.py` now pins the engine order exactly. The text of every line is unchanged, only the order of `REGION` against `ACTION`. This was already the production order since the Azure routing landed; the adapter tests were the only place that still showed the old order.

## Owner actions

- Nothing to relock: no hash-locked test was touched.
- `AzureIpCleaner.list_ips/decide/delete_candidate`, `AzureNicCleaner.prepare/list_nics/decide/attempt_delete` and `AzureDiskCleaner.list_disks/decide/delete_disk` were public helpers for the adapters; they are still used by each cleaner's own `plan()`/`apply()`, so they stay.

## What is left

Nothing for this lane. The `VM` and `SpotVM` adapters stay (scan.py and the locked SpotVM test).

## New bugs

None found.
