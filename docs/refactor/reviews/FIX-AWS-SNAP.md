## Coding summary

Rung FIX-AWS-SNAP (wave FIX-1): behaviour fix in `crc/aws/snapshot.py`.

- **Bugs fixed.**
  - BUG-144: exception tags are read for every snapshot (before the age check, decisions keep their order, so skip counts and logs of valid snapshots are unchanged) and tag entries are tolerated: an entry without `Key` is ignored (DEBUG line), a missing `Value` reads as `''`. A snapshot that carries a valid exception tag next to a malformed entry is still protected. Tags that are not a list of mappings (for example a dict) are not covered by the row and still raise as before, now caught by the BUG-149 per-region isolation.
  - BUG-149: any non-connectivity `Exception` while creating the client, listing a region (`describe_snapshots`, `describe_images`) or deciding its snapshots (malformed snapshot dict, naive `StartTime`, ...) is logged at ERROR (`Region <r>: skipped snapshot cleanup — error while listing (<Type>): <msg>`), recorded with `run.fail(region, "-", error)` and `region_skipped`, and the region is skipped; other regions continue. Connectivity errors keep their old warning and are not recorded as failures. `describe_regions` errors (SAF-004), an invalid `age_days` (raised before any call) and `delete_snapshot` errors (already swallowed) are unchanged. Both paths are covered: `Snapshot.delete()` (adapter, deletes as it goes, so snapshots listed before the failing one in the same region are already deleted, as on main) and `SnapshotCleaner.plan()` (decides the whole region first, so a failing region contributes no candidate).
- **Bugs left.** None.
- **Production command.** `crc.py --cloud aws --resource snapshot --age '{"days": 90}' --exception_tags '{"autoclean": [...], "auto_clean": [...]}'`: same flags, same selection for well-formed snapshots; only malformed tag entries and listing errors changed as above. Direction: a malformed tag entry no longer aborts the run, so later snapshots are processed (the run no longer fails there); the snapshot with the malformed entry is selected only when none of its well-formed tags is an exception tag, as for any other snapshot.
- **Files changed.** `crc/aws/snapshot.py`, `crc/aws/README.md` (quirk notes), `tests/test_aws_snapshot_parity.py` (15 diverging cases marked in `DIVERGES` with their bug ID and excluded from the equality tests; the 11 quirk checks and 2 `_is_protected` helper cases that asserted the old behaviour removed), `tests/test_aws_snapshot.py` (`test_adapter_deletes_as_it_goes` now asserts the region skip), new `tests/test_aws_snapshot_fix.py`, this file. `tests/legacy/aws_snapshot.txt` untouched.
- **Tests.** Before: 42444 passed (182466d). After: 42449 passed (+5); `make check` green (ruff, mypy, import-linter, pytest).
- **Owner actions.** None.

## Owner action

None. No hash-locked test is affected and `CLEANUP_SAFETY.md` needs no change (no SAF invariant mentions snapshot tag reading or per-region isolation of non-connectivity errors; SAF-004 for `describe_regions` still holds).

## Owner decision

None.

## New bugs

- `crc/aws/snapshot.py` `SnapshotCleaner.apply()` (`self._client_factory(region)` fallback when `plan()` was not run): a non-connectivity error there still propagates. Only reachable when `apply()` is called without `plan()`; the CLI uses the adapter. Exists on main: no (main has no `apply()`).
- Tags given as a non-list (for example a dict) or with non-mapping entries are not tolerated, only skipped with their region now. Exists on main: yes (`crc/aws/snapshot.py:29-32`).
