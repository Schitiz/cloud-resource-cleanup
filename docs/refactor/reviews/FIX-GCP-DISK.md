# FIX-GCP-DISK (behaviour-fix rung, wave FIX-1)

## Coding summary

- **Bugs fixed:** BUG-005, BUG-006, BUG-126, BUG-127 (all in `crc/gcp/disk.py`).
  - BUG-005: `notags` is applied with `policy.notags_all`, the helper and semantics of `crc/gcp/vm.py`
    (skip only when the disk's labels match every `notags` key; a disk missing a key is kept for
    deletion). The skip is counted as `exception_tag`.
  - BUG-006: `name_regex` is applied with `policy.name_regex_search_matches` (`re.search`, any
    pattern, empty list matches all; the same helper AWS disk and keypair use, because `vm.py` has no
    name regex). A disk that does not match is skipped as `name_regex_mismatch`. A non-list value or an
    invalid pattern raises `ValueError` naming `name_regex` when the cleaner is built, before any SDK
    call (fail closed). `disk.name` is only read when patterns are set, so a disk without a name
    behaves as before when `name_regex` is empty.
  - BUG-126: after `disks().delete().execute()` the zone operation is polled until DONE without an
    error, with the GCP spot helper `crc.gcp.spot_vm.operations.wait_operation` (180 s, every 5 s). A
    missing operation name, an operation error, a poll error or a timeout is logged, recorded with
    `fail()` and the disk is not recorded as deleted. `GcpDiskClient` gained `get_operation` and
    `ComputeDiskClient` implements it with `zoneOperations().get(...).execute()`.
  - BUG-127: an error while evaluating one disk (timestamp parse, `exception_regex`, `MAX_AGE`, a
    missing field) is logged, recorded with `fail(zone, disk)` and the disk is kept; the loop continues.
    A listing error of one zone (also while iterating) is logged, recorded as `zone <name>` and the
    zone skipped. The zones listing and building the disks client still raise (list/auth failures).
- **Bugs left:** none of the four. BUG-124 (`detach_age`) is out of this rung.
- **Production command:** neither `--notags` nor `--name_regex` is passed, so both are empty and the
  selection is unchanged (every unmarked parity case still equals the oracle). The only visible
  differences for it are the zone-operation polls after each delete and that a failed or
  incomplete delete is no longer counted as deleted. `--filter_tags`, `--exception_tags`,
  `--custom_age_tag_key`, `--slack_channel` keep working with the same flags.
- **Files changed:** `crc/gcp/disk.py`, new `crc/gcp/disk_client.py` (client protocols and
  `ComputeDiskClient`, split out for ARCH-004's 400-line limit and re-exported by `disk.py`),
  `crc/gcp/README.md`, `tests/test_gcp_disk.py` (fake returns an operation), `tests/test_gcp_disk_parity.py`
  (marked cases, wait calls), new `tests/test_gcp_disk_fix.py`.
- **Parity test:** 17 cases carry `diverges` (`BUG-127`; `ignored-age-notags-name-regex` is `BUG-006`).
  For each, the oracle still shows the old outcome and the new code is asserted to give the exact new
  `deleted` list and number of logged errors, on the `Disk` and the Cleaner path. The 10 quirk checks
  of those cases assert the oracle's old quirk and the new outcome. Every unmarked case still equals the
  oracle on calls (leaving out the BUG-126 polls), results, logs and stdout;
  `test_bug_126_every_accepted_delete_is_followed_by_one_operation_poll` pins the polls exactly. The
  oracle runs with its old `notags`/`name_regex` values; the new code with empty ones for unmarked cases.
- **Locked tests:** none touched; `tests/test_gcp_spot_vm.py` passes unchanged.
- **Test count (`pytest -q`):** 42444 at 182466d, 42579 now.
- **Gates:** `make check` green (ruff, mypy, lint-imports, pytest).
- **Owner actions:** see below.

## Owner action

`CLEANUP_SAFETY.md` is CODEOWNERS and was not edited. Proposed edits:

1. Module map row for `crc/gcp/disk.py`, replace with:
   `| crc/gcp/disk.py | GCP disks; detach_age via last_detach_timestamp; --age ignored; custom label replaces detach_age; notags and name_regex applied; delete waits for the zone operation; per-disk and per-zone errors are recorded and skipped |`
2. SAF-021..SAF-024 stay true. Optionally add a new invariant after SAF-045:
   `[SAF-NNN] GCP disk delete is recorded only after the zone operation is DONE without error; an error evaluating or deleting one disk, or listing one zone, is recorded and the run continues; the disk is kept.`

## Owner decision

- Time bound: a stuck zone operation now costs up to 180 s per disk (the spot default) before the
  disk is reported as failed. If that is too long for a Jenkins run with many disks, the bound can be
  lowered through `DiskSettings.wait_sec` (not wired to a flag: no new CLI flag in this wave).

## New bugs

- `crc/gcp/disk.py` `Disk.age` / `--age` is still ignored (SAF-022, known, unchanged) and zonal disks only:
  regional disks are never listed (exists on main: yes; main `crc/gcp/disk.py:117-124`).
- `ComputeDiskClient.list_zones` reads `["items"]` and raises `KeyError` for a project without zones
  (exists on main: yes; main `crc/gcp/disk.py:117-124`); the same call is not isolated by BUG-127 on purpose.
- An invalid `--exception_regex` is now evaluated per disk, so it logs one error per disk and keeps
  every disk instead of aborting the run on the first one (exists on main: yes, as an abort).
