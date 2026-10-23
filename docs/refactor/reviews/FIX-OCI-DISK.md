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
