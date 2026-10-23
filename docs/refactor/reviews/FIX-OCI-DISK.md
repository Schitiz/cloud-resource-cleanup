## Coding summary

**Rung FIX-OCI-DISK (wave FIX-1): BUG-096, BUG-097 and BUG-098 fixed. `make check` green.**

- **Bugs fixed.**
  - `BUG-096`: if listing volume attachments fails with a connectivity/auth error (`CONNECTIVITY_ERRORS`), every block volume of that region is kept (it used to be deleted as "unattached").
  - `BUG-097`: if `list_availability_domains` or any `list_boot_volume_attachments` call fails, every boot volume of that region is kept. A partial set (first domain ok, second fails) is discarded.
  - `BUG-098`: a region with no availability domains keeps every boot volume.
  - In each case the region is recorded once with `region_skipped`, a WARNING `Region <r>: keeping every disk|boot disk: ...` is logged, and each kept volume is counted as run-log skip `attachments_unknown` (skip reasons `block volume attachments unknown` / `boot volume attachments unknown`).
- **Bugs left.** None of the three; the rest of `BUG-099` to `BUG-110` is untouched.
- **Scope notes (direction rule).** Only keeps more. The SDK calls and their order are unchanged (the reads still happen, only the deletes disappear); unexpected non-connectivity errors still propagate; the other volume kind of the region and other regions are decided as before; a non-`AVAILABLE` volume keeps its `state is not AVAILABLE` reason. Both production commands (the two `--cloud oci --resource disk` Jenkins lines) keep the same flags and the same selection when attachment listing works.
- **Files changed.** `crc/oci/disk/cleaner.py` (the module formerly `crc/oci/disk.py`: `attached_volume_ids` / `attached_boot_volume_ids` return `set[str] | None`, `_keep_all`, `decide`, `_skip_reason`), `crc/oci/disk/adapter.py` (type of `_process` argument only), `crc/oci/disk/README.md`, `tests/test_oci_disk_parity.py` (six cases marked in `DIVERGES` with their BUG ID; the six quirk checks that asserted the buggy outcome removed; every other case still equals the oracle), new `tests/test_oci_disk_fix.py`, this review. No hash-locked test, `tests/legacy/` oracle, `CLEANUP_SAFETY.md`, PLAN/STATUS/BUGS file was touched.
- **Tests.** `pytest -q`: 42444 passed before (at 182466d), 42450 passed after.
- **Owner actions.** See below.

## Owner action

Proposed addition to `CLEANUP_SAFETY.md` (CODEOWNERS file, not edited here), for example under "Leftover disks on other clouds" or "Uncertain API signals":

> [SAF-NNN] OCI `crc/oci/disk`: when the volume attachments, the availability domains or the boot volume attachments of a region cannot be listed (connectivity or auth error, or no availability domain), every block volume (respectively boot volume) of that region is kept and the region is recorded as skipped. Attachment state that is unknown is never read as "unattached".

No locked test needed a change.

## Owner decision

None.

## New bugs

- `crc/oci/disk.py` (main, `get_availability_domains` in `crc/oci/_base.py:119-129`): the availability-domain result is cached per region in `Base`, so a transient empty list is cached for the rest of the run; with this fix that only keeps boot volumes of that region, but it would also hide them from every later pass. Exists on main: yes. Not fixed.

## Round 1 (Argon)

Scope reviewed: `git diff 182466d..HEAD` on branch `fix/oci-disk` (rung `FIX-OCI-DISK`, wave `FIX-1`).

### Checks

1. **Fixed bugs (`BUG-096`, `BUG-097`, `BUG-098`)**:
   - `BUG-096` (`crc/oci/disk/cleaner.py:188-203`, `:226-247`, `:300-307`): `attached_volume_ids()` returns `None` when `api.list_volume_attachments()` raises any `CONNECTIVITY_ERRORS` (`ConnectTimeout`, `RequestException`, `ServiceError`), logs `log_skipped_region` plus `WARNING: Region <r>: keeping every disk: block volume attachments unknown`, records `_logger.region_skipped(region, e)` once per region, and causes `decide()` / `_skip_reason()` to skip every `AVAILABLE` block volume in that region with reason `"block volume attachments unknown"` (run-log skip key `"attachments_unknown"`). Tested by `test_volume_attachment_error_keeps_every_block_volume` (`tests/test_oci_disk_fix.py`) and cases `attachment-listing-connection-error-deletes-attached` and `attachment-listing-auth-error-deletes-attached` (`tests/test_oci_disk_parity.py`), all of which fail on `182466d` and pass now.
   - `BUG-097` (`crc/oci/disk/cleaner.py:204-224`, `:226-247`, `:300-307`): `attached_boot_volume_ids()` returns `None` when `api.list_availability_domains()` or any `api.list_boot_volume_attachments(domain)` raises `CONNECTIVITY_ERRORS` (discarding any attachments collected from earlier availability domains in the same region), logs `log_skipped_region` plus `WARNING: Region <r>: keeping every boot disk: boot volume attachments unknown`, records `_logger.region_skipped(region, e)` once per region, and keeps every `AVAILABLE` boot volume in that region with reason `"boot volume attachments unknown"`. Tested by `test_availability_domain_error_keeps_every_boot_volume`, `test_boot_attachment_error_keeps_every_boot_volume`, and `test_error_in_a_later_domain_discards_the_attachments_found_so_far` (`tests/test_oci_disk_fix.py`) and cases `boot-attachment-listing-error-deletes-attached`, `availability-domains-error-deletes-attached`, and `boot-attachment-second-domain-error-keeps-first` (`tests/test_oci_disk_parity.py`), all of which fail on `182466d` and pass now.
   - `BUG-098` (`crc/oci/disk/cleaner.py:212-215`): when `api.list_availability_domains()` returns an empty sequence, `attached_boot_volume_ids()` logs the keep-all warning, records `region_skipped` once per region, and returns `None`, keeping every `AVAILABLE` boot volume in that region. Tested by `test_region_without_availability_domains_keeps_every_boot_volume` (`tests/test_oci_disk_fix.py`) and case `no-availability-domains` (`tests/test_oci_disk_parity.py`), which fail on `182466d` and pass now.
   - Both the `Cleaner` path (`DiskCleaner.plan()` / `apply()`) and the legacy `Disk.delete()` adapter (`crc/oci/disk/adapter.py:107-131`) share `attached_volume_ids`, `attached_boot_volume_ids`, and `decide`.
2. **Direction rule & parity (`tests/test_oci_disk_parity.py`, `tests/legacy/oci_disk.txt`)**:
   - Only keeps more (never deletes, stops, or releases anything that was kept before). Non-`AVAILABLE` volumes still skip with `"state is not AVAILABLE"` before the attachment check (`crc/oci/disk/cleaner.py:303-306`), the other volume kind in the same region and all other regions are decided as before, and non-connectivity errors still propagate.
   - `tests/legacy/oci_disk.txt` is untouched (`git diff 182466d..HEAD -- tests/legacy/` is empty).
   - Only the 6 in-scope cases are in `DIVERGES` (each tagged with `"BUG-096"`, `"BUG-097"`, or `"BUG-098"`), and all 71 other `PARITY_CASES` still assert exact equality with the oracle on calls, errors, deleted list, count, logs, and stdout.
   - **Tightened in review**: updated `test_unknown_attachments_keep_the_volumes` (`tests/test_oci_disk_parity.py:805-851`) to assert the exact `new.logs`, `planned.logs`, `planned.calls == _reads(old.calls)`, `new.stdout == old.stdout`, and `planned.stdout == old.stdout` for all 6 diverging cases per `BEHAVIOUR_FIX.md` section 3.
3. **Production commands**:
   - Both Jenkins `--cloud oci --resource disk` commands keep working with the exact same CLI flags and the same volume selection whenever attachment and availability-domain listing succeed (and fail closed per region when attachment state is unknown). No new CLI flags, dependencies, async, or pydantic.
4. **Fail-closed before mutation**:
   - `plan()` is read-only (`ARCH-005`), unknown attachment sets keep all volumes of that kind in the region without calling `delete_volume` or `delete_boot_volume`, and unexpected errors raise before `apply()`.
5. **Protected files**:
   - `git diff 182466d..HEAD` touches only `crc/oci/disk/README.md`, `crc/oci/disk/adapter.py`, `crc/oci/disk/cleaner.py`, `docs/refactor/reviews/FIX-OCI-DISK.md`, `tests/test_oci_disk_fix.py`, and `tests/test_oci_disk_parity.py`. No locked safety test, `tests/archtest/safety_lock.json`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, or `CLEANUP_SAFETY.md` was edited.
6. **README & Public API (`crc/oci/disk/README.md`)**:
   - `Public API` and `Safety Invariants` in `crc/oci/disk/README.md` are updated and pass `ARCH-002`.
7. **Owner action & Owner decision**:
   - Proposed `CLEANUP_SAFETY.md` invariant is recorded under `## Owner action`; all three bugs in scope are fixed (`## Owner decision` is `None`).

### BLOCKING

None.

### NIT

None in do-not-edit files (`AGENTS.md`, `ARCHITECTURE.md`, `CLEANUP_SAFETY.md`, `docs/refactor/PLAN.md`, `.cursor/**`, `tests/archtest/**`).

### Gates & test count

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

- `python3 -m ruff check .`: passed
- `python3 -m mypy`: passed
- `lint-imports`: passed (5 contracts kept, 0 broken)
- `python3 -m pytest -q`: 42450 passed (42444 at `182466d`, +6 net from 18 new tests in `tests/test_oci_disk_fix.py` and 6 parity cases moved from `PARITY_CASES` + `QUIRKS` to `DIVERGES` in `tests/test_oci_disk_parity.py`)

VERDICT: APPROVE
