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
