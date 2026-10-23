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

`CLEANUP_SAFETY.md` (CODEOWNERS) is not edited in this rung. Proposed updates to `CLEANUP_SAFETY.md` lines 178-183:

- `[SAF-043]`: replace `[SAF-043] GCP/OCI match their regular VM label/tag helpers; empty filter still needs the age gate. GCP/OCI are opt-in via explicit --cloud (not --cloud all).` with:
  `[SAF-043] GCP/OCI match their regular VM label/tag helpers; GCP Spot also skips unlabelled Spot VMs when --filter_tags is empty (BUG-228), while OCI with an empty filter still relies on the age gate. GCP/OCI are opt-in via explicit --cloud (not --cloud all).`
- `[SAF-044]`: replace `[SAF-044] Leftover disks/volumes are skipped when their own exception/notags match (and Azure disks outside --resource_group).` with:
  `[SAF-044] Leftover disks/volumes are skipped when their own exception/notags match, when a GCP leftover disk's own custom age label is not yet reached, invalid, or has an unreadable creationTimestamp (BUG-242), and for Azure disks outside --resource_group.`

## New bugs

- `crc/gcp/spot_vm/disks.py` `remove_leftover_disk`: a disk delete response without `name`
  counts as deleted (parity case `disk-delete-no-op-name-counted`); exists on main: yes
  (`crc/gcp/spot_vm.py`, disk delete after `_delete_disk`). Not fixed.

## Round 1 (Argon)

### Findings

- **NIT** (`crc/gcp/spot_vm/README.md:37,41`, fixed in review): updated `Public API` entries for `reject_reason()` (added `unlabelled` skip reason) and `disk_ok_to_delete()` (added custom age label protection) to match the `Safety Invariants` section.
- **NIT** (`CLEANUP_SAFETY.md:178-183`, CODEOWNERS — not edited): added exact proposed text for `[SAF-043]` (BUG-228) and `[SAF-044]` (BUG-242) under `## Owner action` above.

### Verification

1. **Bug fixes & regression tests (`182466d..HEAD`)**:
   - **BUG-228**: `crc/gcp/spot_vm/instances.py` (`_label_and_age_reason`) returns `"unlabelled"` when `not settings.filter_labels and not _labels(instance)` after the age check, preserving all prior skip reasons (`state`, `not_spot`, `managed_or_gke`, `exception_tag`, `filter_mismatch`, `too_young`) and error paths while keeping unlabelled Spot VMs when `filter_labels` is empty. Locked test `tests/test_gcp_spot_vm.py::GcpSpotDetectTests::test_empty_filter_allows_unlabeled` (which tests `_has_matching_filter_label` directly) remains untouched and passing. Covered by 7 unit tests in `tests/test_gcp_spot_vm_fix.py` and 12 diverging parity cases + 4 `FIXED_QUIRKS` entries in `tests/test_gcp_spot_instances_parity.py`.
   - **BUG-229**: Left unfixed and documented under `## Owner decision`. On `182466d`, `SpotVMCleaner._delete_and_wait` already records a delete whose operation has no `name`, empty `name`, `error`, or poll timeout as failed (`logger.current().fail(...)`, not added to `succeeded` / `get_deleted`) and skips leftover disks per `SAF-039`. Deleting leftover disks after an incomplete instance-delete operation wait would either violate `SAF-039` / the direction rule or require a new `instances.get` SDK call (owner decision). Pinned by 5 tests in `tests/test_gcp_spot_vm_fix.py`.
   - **BUG-242**: `crc/gcp/spot_vm/disks.py` (`_custom_age_keeps`, `disk_ok_to_delete`) checks `core_age.validated_retention_age` on the leftover disk's own labels when `custom_age_tag_key` is set, keeping the disk (fail closed) on `disk_invalid_age_tag`, `disk_age_unknown` (missing/unparseable `creationTimestamp`), or `disk_too_young` (`core_age.is_old` against disk `creationTimestamp` using the injected clock). Disks without the custom age label or runs without `custom_age_tag_key` make identical SDK calls and decisions to `182466d`. The remaining parts of `BUG-242` (`filter_labels` and `users` on the disk) were outside the task prompt and are noted in the review. Covered by 18 unit tests in `tests/test_gcp_spot_vm_fix.py` and `test_bug_242_leftover_disk_custom_age_main_deletes_new_code_keeps` in `tests/test_gcp_spot_instances_parity.py`.
2. **Direction rule & parity**:
   - Fix only keeps more (unlabelled VMs when `filter_labels` is empty; leftover disks protected by their own custom age tag).
   - `tests/legacy/gcp_spot_vm.txt` is untouched. Every unmarked parity case asserts exact equality with the oracle; diverging cases are explicitly keyed in `DIVERGES` with `"BUG-228"`.
3. **Production commands**: None reach GCP Spot; no CLI flags or dependencies changed.
4. **Fail-closed paths**: Invalid `project_id` or `age` raises `ValueError` before any SDK call; invalid custom age tags or unreadable disk `creationTimestamp` skip the resource before any delete call.
5. **Protected files**: `tests/test_gcp_spot_vm.py`, `tests/archtest/safety_lock.json`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, and `CLEANUP_SAFETY.md` are untouched.

### Gates

- `make check` (`ruff check`, `ruff format --check`, `mypy`, `lint-imports`, `pytest`): **passed** (`42474 passed`).

VERDICT: APPROVE
