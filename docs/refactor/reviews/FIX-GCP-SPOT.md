## Coding summary

Rung FIX-GCP-SPOT (wave FIX-1), branch `fix/gcp-spot`. No production command uses GCP Spot.

- **Fixed BUG-228** (`crc/gcp/spot_vm/instances.py`): an instance with no labels at all is kept
  (skip reason `unlabelled`) when `filter_labels` is empty. The check runs last, after the age
  check, so every other reason, error and log line is unchanged; with an active filter the VM
  is still `filter_mismatch`. It only keeps more.
- **Fixed BUG-242, custom age part** (`crc/gcp/spot_vm/disks.py`, `cleaner.py`, `adapter.py`): a
  leftover disk that carries `custom_age_tag_key` is kept when it is younger than that age
  (disk `creationTimestamp`), when the label is invalid, or when the timestamp is missing or
  unreadable (skip reasons `disk_too_young`, `disk_invalid_age_tag`, `disk_age_unknown`, DEBUG
  line per disk). A disk without the label, or a run without `custom_age_tag_key`, behaves as
  before (same SDK calls). The clock is injected (`RunContext.now` or the adapter clock).
- **Not changed, BUG-229**: see "Owner decision".
- **BUG-242 rest, left**: the disk's own `filter_labels` and `users` are still not read. The task
  asked for the custom age tag only; reading `users` / `filter_labels` is a larger decision
  (a disk with no labels would then be kept whenever a filter is set).
- Files: `crc/gcp/spot_vm/{instances,disks,cleaner,adapter}.py`, `crc/gcp/spot_vm/README.md`,
  `tests/test_gcp_spot_vm_fix.py` (new, 30 tests), `tests/test_gcp_spot_instances_parity.py`
  (12 cases marked in `DIVERGES`, 4 quirk checks moved to `FIXED_QUIRKS`, BUG-242 parity test),
  `tests/test_gcp_spot_instances.py` (the `instance()` fixture now has a label by default, so the
  tests that delete a VM do not use an unlabelled one). `tests/test_gcp_spot_vm.py` untouched.
- Tests: `pytest -q` 42444 passed at 182466d, 42474 passed after (`make check` green).
- Owner actions: none. `CLEANUP_SAFETY.md` is not edited (see "Owner action").

Note: the task names `crc/gcp/spot_vm.py`; the code lives in the package `crc/gcp/spot_vm/`.

## Owner decision

**BUG-229 not fixed.** The task asks that a delete whose operation has no name, errors or does
not reach DONE is recorded as failed, not deleted. That is already what the code does:
`SpotVMCleaner._delete_and_wait` returns False, the VM is not added to the result, an error
line is logged and `logger.current().fail(...)` records the VM (`FAILED ... failed=1`). Only the
second half of the row remains: the leftover `autoDelete=false` disks are skipped because the VM
may in fact be gone. Deleting them anyway would delete more than today, which the wave rules and
`CLEANUP_SAFETY.md` SAF-039 (disks only after the instance-delete operation completed) forbid.
A safe version needs the owner to decide: after a failed wait, re-read the instance
(`instances.get`, a new SDK call) and delete the disks only when it is gone. I pinned the
current outcome with tests (`test_bug_229_*`: no name, empty name, operation error, never done;
VM not recorded, disks not read, failure recorded).

## Owner action

None. SAF-044 in `CLEANUP_SAFETY.md` could later read "Leftover disks are skipped when their own
exception_labels/notags match or their own custom age tag is not yet reached" (GCP Spot); not
required for this rung.

## New bugs

- `crc/gcp/spot_vm/disks.py` `remove_leftover_disk`: a disk delete response without `name`
  counts as deleted (parity case `disk-delete-no-op-name-counted`); exists on main: yes
  (`crc/gcp/spot_vm.py`, disk delete after `_delete_disk`). Not fixed.
