# FIX-OCI-SPOT review

## Coding summary

- Bug fixed: BUG-255. After a preemptible instance is terminated, a leftover block volume is deleted only when it was created at or after the instance's `time_created` and no other instance has it attached. Otherwise it is kept with skip reason `not_owned` (DEBUG log with the cause). The instance is still terminated.
- Bugs left: none of the rung's list. BUG-255's other half (`filter_tags` and `age` are not applied to the volume) is not part of the task text and stays as is.
- Rules for the new check (all fail closed): a volume or instance creation time that is missing, not a `datetime` or not comparable keeps the volume; a failed `list_volume_attachments(compartment_id, volume_id=...)` read keeps the volume (logged as an error and recorded as a failure); an attachment that is not `DETACHED` (including `DETACHING`) and whose `instance_id` differs from the terminated instance, or is missing, keeps the volume. The terminated instance's own attachment is ignored. Exception tags and notags are still checked first (reason `leftover_exception_tag`), so no new read happens for a volume they protect.
- Dry run: `plan()` runs the same read-only check, so the reported volume list matches what `apply()` deletes.
- Direction rule: only extra reads were added (one `get_volume` already existed, plus one `list_volume_attachments` per tag-passing volume). Nothing is deleted that was not deleted before. No new flag, dependency or log level; no production command uses OCI spot.
- Files changed:
  - `crc/oci/spot_vm/leftovers.py` (`VolumeOwner`, `volume_owned`, owner argument of `volume_passes_tag_check` / `checked_volumes`), `adapter.py`, `cleaner.py` (build the owner from the instance), `client.py` (`SdkVolume.time_created`), `README.md` (Public API, Safety Invariants).
  - `tests/test_oci_spot_vm_fix.py` (new, 18 tests), `tests/test_oci_spot_instances_parity.py` (BUG-255 diverging table with 8 cases, 2 new equal cases, ownership reads filtered by `_without_ownership_reads` for the unmarked cases), `tests/test_oci_spot_instances.py` and `tests/test_oci_logger.py` (fakes only: volume `time_created` and by-volume attachment listing; one expected call order gained the new read).
  - `crc/oci/spot_vm.py` named in the task is now the package `crc/oci/spot_vm/`; the old import path still works.
- Locked test `tests/test_oci_spot_vm.py` is untouched and green: it mocks `_volume_ok_to_delete` and `_delete_volume`, and `_volume_ok_to_delete(client, volume_id)` keeps working with two arguments (the owner is an optional third one).
- Parity: every unmarked case still asserts equality with the oracle (calls, order, logs, volumes, stdout). The only filter is the new ownership read and its pager call, removed from the new calls before comparison. Cases that diverge are `test_bug_255_volume_not_owned_is_kept` (BUG-255): volume older than the instance, creation time missing, attached to another instance, attachment read fails; each in live and dry-run mode and through both the adapter and the cleaner, asserting the oracle still deletes `v1`.
- Test count: 42444 before (`pytest -q --co` at 182466d), 42474 after (`make check` green).
- Owner actions: none.

## Owner action

None. No destructive invariant text needs to change for the listed IDs (SAF-044 still holds); optionally add to `CLEANUP_SAFETY.md` under SAF-044: "A leftover volume is deleted only when it was created at or after the instance's creation time and no other instance has it attached; anything uncertain keeps it."

## Owner decision

None.

## New bugs

- `crc/oci/spot_vm/leftovers.py:attached_volume_ids`: the leftover list is taken before terminate, so a volume that another instance attaches between the read and the delete is only caught by the new ownership read, which is a narrow race that cannot be closed without a lock. Exists on main: yes. Not fixed.
- The ownership read lists attachments only in the run's compartment (`compartment_id`); a volume attached to an instance of another compartment is not seen. OCI volumes and their attachments normally share the compartment of the instance. Exists on main: yes (it was never checked). Not fixed.

## Round 1 (Argon)

### Findings

1. **BUG-255 fix verified**: `crc/oci/spot_vm/leftovers.py` (`VolumeOwner`, `volume_owned`, `volume_passes_tag_check`, `checked_volumes`), `crc/oci/spot_vm/adapter.py`, and `crc/oci/spot_vm/cleaner.py` verify that after a preemptible instance is selected/terminated and a leftover block volume passes the tag check (`exception_tags` / `notags`), the volume is deleted only when its `time_created` is a `datetime` greater than or equal to the instance's `time_created` and `list_volume_attachments(compartment_id, volume_id=...)` shows no non-`DETACHED` attachment to any other instance. Otherwise the volume is kept with skip reason `not_owned` and a `DEBUG` log line (and `_logger.record_failure` + `ERROR` log when `list_volume_attachments` raises).
2. **Protocol completeness (fixed in review)**: Added `instance_id` property to `SdkAttachment` and updated `ComputeClient.list_volume_attachments` signature in `crc/oci/spot_vm/client.py` to accept optional `instance_id` and `volume_id` parameters matching the new ownership lookup, and asserted `_logger.record_failure` on attachment read failure in `tests/test_oci_spot_vm_fix.py`.
3. **Direction rule & parity**: Only keep-more conditions and read-only calls (`list_volume_attachments` per tag-passing volume) were added; nothing is deleted, stopped, or released that was kept before. `tests/legacy/oci_spot_vm.txt` is untouched. All 69 unmarked parity cases in `tests/test_oci_spot_instances_parity.py` assert equality with the oracle (filtering only the new ownership read and its pager call), and the 8 `BUG_255` diverging cases (4 scenarios x live/dry-run across both `SpotVM` and `SpotVmCleaner`) assert that the oracle deletes `v1` while the new code keeps it.
4. **Production commands**: None reach OCI spot; no CLI flags, dependencies, or public signatures were broken (`SpotVM._volume_ok_to_delete` keeps `owner` optional so existing two-argument callers continue to work).
5. **Fail-closed paths**: Missing, non-`datetime`, or incomparable `time_created`, volume older than instance, failed `list_volume_attachments`, and non-`DETACHED` attachments to another or unknown instance all fail closed before `delete_volume` is called.
6. **Protected files & docs**: `tests/test_oci_spot_vm.py`, `tests/archtest/safety_lock.json`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, and `CLEANUP_SAFETY.md` are untouched. `crc/oci/spot_vm/README.md` Public API and Safety Invariants are updated (`ARCH-002` passes).

### Gates

- `ruff format --check .`: passed
- `ruff check .`: passed
- `mypy`: passed (`Success: no issues found in 147 source files`)
- `pytest` (including `tests/archtest`): 42474 passed (up from 42444 on `182466d`)

VERDICT: APPROVE
