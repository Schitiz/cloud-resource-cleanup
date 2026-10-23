## Coding summary

Rung FIX-OCI-VM (wave FIX-1, behaviour fix). Branch `fix/oci-vm`.

- **Bugs fixed.**
  - `BUG-158`: `VmCleaner` now skips OKE node-pool and instance-pool members with the guard `crc/oci/spot_vm` uses (`policy.oci_is_managed_or_oke_node` over freeform tags, defined tags and metadata). It runs right after the state check, also with empty `filter_tags`. The run-log skip key is `managed`; `plan().skipped` carries reason `OKE or instance pool member`. Keeps more than before, never deletes or stops more.
  - `BUG-162`: `VmCleaner.decide()` catches an unexpected error while evaluating one instance (missing or naive `time_created`, malformed `MAX_AGE`, anything else), logs it at ERROR (`Error occurred while evaluating instance <name>: <error>`), records it with `record_failure(region, id, error)` and keeps the instance (skip reason `evaluation failed`). The loop continues with the next instance and region; both the `VM` adapter and the registered Cleaner path use `decide()`, so both are covered. Instances already acted on are now reported and the summary is logged.
- **Bugs left.** None of the two. (`BUG-159`, `BUG-160`, `BUG-161`, `BUG-163` to `BUG-171` are out of scope.)
- **Files changed.**
  - `crc/oci/vm/cleaner.py` (guard, `decide()` try/except, skip key)
  - `crc/oci/vm/client.py` (`SdkInstance` Protocol gains `defined_tags` and `metadata`; the real SDK object has both, the guard reads them with `getattr` so fakes without them still work)
  - `crc/oci/vm/README.md` (Safety Invariants, Public API note)
  - `tests/test_oci_vm_parity.py` (BUG-162 cases marked in `DIVERGES`; the five old BUG-162 quirk checks moved to `test_bug_162_oracle_fails_and_new_code_carries_on`; `test_vm_diverges_from_oracle` skips those cases; every other case still equals the oracle)
  - `tests/test_oci_vm_fix.py` (new, 23 tests: BUG-158 freeform/defined/metadata markers, order after state check, empty filter, dry run, adapter, fakes without the attributes; BUG-162 missing/naive time, malformed MAX_AGE, other region continues, ERROR log, run-log failure, adapter)
  - `docs/refactor/reviews/FIX-OCI-VM.md`
- **Locked tests.** `tests/test_oci_spot_vm.py` and the other hash-locked tests are untouched and pass. `tests/legacy/*.txt` untouched.
- **Production commands.** Same CLI flags and selection. Only instances that are OKE or instance pool members, or whose evaluation raised, are now kept instead of acted on or aborting the run. The oci vm commands in the Jenkinsfile keep working.
- **Test count.** `pytest -q`: 42444 at 182466d, 42467 after (`make check` green: ruff, mypy, lint-imports, pytest).
- **Owner actions.** See below.

## Owner action

`CLEANUP_SAFETY.md` (CODEOWNERS, not edited here). Proposed text, extending SAF-045:

> [SAF-045] GCP skips GKE/MIG members; OCI skips OKE / instance-pool members (tags/metadata) in both the OCI Spot VM and the OCI VM cleaner (`crc/oci/vm`, skip reason `managed`).

Optional new invariant (needs a new locked test if the owner wants it hash-locked): "OCI VM: an error while evaluating one instance keeps that instance, is recorded as a failure and does not stop the run."

## New bugs

- `crc/oci/vm/cleaner.py` `_is_old`: a naive `time_created` is not given a timezone as `crc/oci/spot_vm/decide.py:is_old_instance` does, so with BUG-162 fixed such an instance is now kept with a recorded failure instead of being evaluated. Safe (fail closed); the spot VM variant treats it as local time. Exists on main: yes (`crc/oci/vm.py:121` on main raised `TypeError`).
- The `oke` guard is a case-insensitive substring match (`policy._looks_oke`), so any tag or metadata entry containing `oke` (for example a tag value such as `joker`) keeps a VM. Same on `spot_vm` today; fail closed, not fixed.
