# FIX-AZU-DISK review

## Coding summary

Rung FIX-AZU-DISK (wave FIX-1): behaviour fixes in `crc/azu/disk.py`. Status: complete.

- Bugs fixed: BUG-172, BUG-174.
  - BUG-172: `AzureDiskCleaner.list_disks()` calls `disks.list_by_resource_group(Base.resource_group)`
    instead of the subscription-wide `disks.list()`. The delete still uses the same configured
    group, so a disk is only ever listed and deleted in the group the job targets. The group is not
    derived from the listed disk's id. The production commands (`--resource_group "$RESOURCE_GROUP"`,
    same filters) keep the same flags and the same selection inside that group.
  - BUG-174: `delete_disk()` waits for the `begin_delete` poller (`.result()`) before the disk is
    recorded as deleted, and catches `Exception` per disk: it logs
    `Error occurred while deleting disk <name>: <error>` at ERROR, records `_logger.failed(...)` in
    the run log (RESULT `failed=N`), returns the error text and the caller (`apply()` and
    `Disk.delete()`) goes on with the next disk. `apply()` returns `Result.failed`. Dry runs call no
    delete and no poller. Listing errors still propagate.
- Bugs left: none of the two. Part of the BUG-174 row stays as today on purpose: errors while
  deciding a disk (`time_created` None `AttributeError`, naive `time_created` `TypeError`,
  `disk_state` None `TypeError`) and mid-listing paging errors still propagate (task: "listing
  errors still propagate as today"; they happen before any delete in `plan()`). See "Owner decision".
- Files changed: `crc/azu/disk.py`, `crc/azu/README.md` (Safety Invariants / quirk note),
  `tests/helpers_azure_disk.py` (fake: `list_by_resource_group`, poller with `result()`),
  `tests/test_azure_disk_parity.py` (cases marked `diverges="BUG-174"` plus new
  `poller-error-not-deleted` and `begin-delete-error-every-disk`; the oracle `("list",)` call is
  mapped to the new group listing for every case; two quirk checks that asserted the old
  propagation are replaced by the `DIVERGING` table), `tests/test_azure_disk.py` (listing call;
  the `apply propagates delete error` test is replaced by the isolation tests), new
  `tests/test_azure_disk_fix.py`. Oracles in `tests/legacy/` and the hash-locked tests are untouched.
- Test count (`pytest --collect-only`): 42444 at 182466d, 42454 now. `make check` green.
- Owner actions: none required.

## Owner decision

- Decision/selection errors (BUG-174 sub-cases `created-none-error`, `state-none-error`, naive
  `time_created`) are not isolated: in the registered path they abort `plan()` before any delete, and
  `Disk.delete()` (legacy adapter) still stops mid-loop after earlier disks were deleted, as today.
  Isolating them means skipping a disk whose age or state cannot be read; that is a selection change
  that was not in the approved scope. Tests: `test_bug_174_selection_errors_still_propagate`.
- Exit code: a failed delete no longer raises, so the process no longer exits non-zero because of it
  (the failure appears in the RESULT line `failed=N` and the ERRORS list). If Jenkins must still go
  red on a failed delete, the CLI exit-code rule belongs to the CLI layer (not changed here).

## New bugs

- `crc/azu/disk.py` `Disk.delete()` / `apply()`: a disk named `None` is deleted by Azure with
  `begin_delete(rg, None)` semantics unclear; with the fix the later `"Deleted disk: " + name`
  `TypeError` is caught and reported as a failure. Exists on main: yes (it raised there). Not fixed.
