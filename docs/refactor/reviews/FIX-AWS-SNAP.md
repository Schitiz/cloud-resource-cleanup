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

## Round 1 (Argon)

Scope reviewed: `git diff 182466d..HEAD` (`crc/aws/snapshot.py`, `crc/aws/README.md`, `tests/test_aws_snapshot_parity.py`, `tests/test_aws_snapshot.py`, `tests/test_aws_snapshot_fix.py`, `docs/refactor/reviews/FIX-AWS-SNAP.md`).

### Checklist verification

1. **Fixed bugs (`BUG-144`, `BUG-149`)**:
   - `BUG-144`: `_read_tags` reads `Tags` for every snapshot before the age check when `exception_tags` is set, ignores entries without `Key` (logging a DEBUG line), and defaults a missing `Value` to `""`. Decision order (`too_young` -> `exception_tag` -> `used_by_ami`) is preserved so skip counts and logs on well-formed snapshots are unchanged.
   - `BUG-149`: Non-connectivity `Exception`s during client creation, `describe_snapshots`, `describe_images`, or snapshot decision in a region are caught by `_skip_failed_region`, which calls `_regionlog.region_skipped(region, e)`, logs at ERROR (`Region <r>: skipped snapshot cleanup — error while listing (<Type>): <msg>`), records `logger.current().fail(region, "-", e)`, and continues to the remaining regions. `CONNECTIVITY_ERRORS`, `describe_regions` errors (`SAF-004`), and `check_age` before listing are unchanged.
   - Both fixes are covered by `tests/test_aws_snapshot_fix.py`, which fails on `182466d` and passes now.
2. **Direction rule and parity tests**:
   - No snapshot kept on `182466d` is deleted; failing regions keep all undecorated/undecided snapshots (`SnapshotCleaner.plan()` keeps the entire failing region; `Snapshot.delete()` stops the failing region immediately).
   - `tests/legacy/aws_snapshot.txt` is untouched (`git diff 182466d..HEAD -- tests/legacy/` is empty). All 54 non-diverging parity cases run with full equality assertions in `tests/test_aws_snapshot_parity.py`; all 15 diverging cases are marked in `DIVERGES` with `"BUG-144"` or `"BUG-149"` and assert both the oracle error and the exact new outcome (`calls`, `deleted`, `count`, `logs`, `stdout`, `error`) in `tests/test_aws_snapshot_fix.py`.
3. **Production command**:
   - `python3 crc.py --cloud aws --resource snapshot --age '{"days": 90}' --exception_tags '{"autoclean": ["false", "False", "FALSE"], "auto_clean": ["false", "False", "FALSE"]}' --slack_channel yba-crc-cleanup-notifications` runs with identical CLI flags and identical selection for well-formed snapshots.
4. **Fail-closed before SDK mutation**:
   - `check_age(now)` runs before `list_regions()` and any client call; `describe_regions` non-connectivity errors propagate before any per-region client or `delete_snapshot` call; `SnapshotCleaner.plan()` evaluates the full region before adding candidates.
5. **Protected files**:
   - None of `tests/archtest/safety_lock.json`, locked safety tests, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, `CLEANUP_SAFETY.md`, `AGENTS.md`, `ARCHITECTURE.md`, `.cursor/**`, or `tests/archtest/**` was edited.
6. **README sync (`ARCH-002`)**:
   - `crc/aws/README.md` Safety Invariants and Public API match `crc/aws/snapshot.py` and pass `ARCH-002`.
7. **Unfixed bugs**:
   - None (`## Owner decision` is `None.`).

### Findings (fixed in review)

1. **`_read_tags` returned `None` on non-list `Tags`, deferring the `TypeError` past the age check and calling `_read_tags` twice** (`crc/aws/snapshot.py:107-137`):
   - Made `_read_tags` fall back to `{t["Key"]: t["Value"] for t in tags}` directly when `tags` is not a list of `Mapping`s so non-list `Tags` also raise before the age check on young snapshots and `_is_protected` does not call `_read_tags` twice.
2. **`test_diverging_case_has_the_fixed_outcome` did not pin `calls`, `stdout`, or exact `logs`** (`tests/test_aws_snapshot_fix.py:36-89`, `:214-257`):
   - Updated `test_diverging_case_has_the_fixed_outcome` to assert exact `old.error` type, `new.calls`, `new.logs`, `new.deleted`, `new.count`, `new.stdout`, and `new.error` for all 15 `DIVERGES` cases on both `ADAPTER` and `CLEANER` paths (`BEHAVIOUR_FIX.md` section 3). Also asserted the `DEBUG` log for a missing-`Key` tag on a young snapshot and the oracle `KeyError` in `test_is_protected_tolerates_malformed_entries`.
3. **Stale sentence at the end of `crc/aws/README.md` `Snapshots (AWS-2)` invariant** (`crc/aws/README.md:72`, `:78`):
   - Updated the trailing sentence that still said a listing error in a later region is raised in the Cleaner path, and noted that `BUG-144` and `BUG-149` are fixed in `FIX-AWS-SNAP`.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` (`crc`, `tests`) | Success: no issues found in 229 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 42449 passed |

Test count: 42444 before (`182466d`), 42449 after (+5).

VERDICT: APPROVE
