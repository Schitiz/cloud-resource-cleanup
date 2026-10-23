# FIX-GCP-IP review

## Coding summary

Rung FIX-GCP-IP (wave FIX-1, branch `fix/gcp-ip`): `crc/gcp/ip.py`.

- **Bugs fixed:** BUG-001, BUG-063, BUG-064.
  - BUG-001: `exception_regex` now excludes every RESERVED address whose name contains any entry
    (plain substring, as the flag text in `README.md` says). Before, only the matching names were
    kept for deletion. The check is local to `crc/gcp/ip.py` (`IpCleaner._excluded`); non-string
    entries still raise `TypeError`, evaluated for every RESERVED address as before.
  - BUG-063: a Google API / auth / OS error while deleting one address is logged at ERROR,
    recorded with `logger.current().fail(region, id, error)` (and in `Result.failed`), the address
    is not recorded as deleted and the loop continues. Addresses already deleted stay in
    `deleted_ips` and the summary is logged. Any other exception is recorded with `fail` and
    re-raised, as before.
  - BUG-064: `delete_address` returns the long-running operation (`OperationView`); `.result()`
    is called before "Deleting IP address" is logged and before the name is recorded. A failed or
    timed-out operation counts as a failed delete (BUG-063 path).
- **Bugs left:** none of the three. BUG-062 (no age gate) is not in this rung.
- **Production commands** (`--resource ip --name_regex [...]`, no `--exception_regex`): selection
  unchanged (`test_bug_001_production_selection_without_exception_regex_is_unchanged`); same CLI
  flags; the only SDK call added is `.result()` on the delete operation.
- **Files changed:** `crc/gcp/ip.py`, `crc/gcp/README.md`, `tests/test_gcp_ip.py`,
  `tests/test_gcp_ip_parity.py`, `tests/test_gcp_logger.py` (one return annotation of a local test
  helper so mypy accepts the new `delete_address` return type), new `tests/test_gcp_ip_fix.py`,
  this file. Not touched: PLAN.md, STATUS.md, BUGS.md, CLEANUP_SAFETY.md, `tests/legacy/*`,
  locked safety tests, `crc/core/policy.py`.
- **Parity test:** 9 cases are marked in `DIVERGING` with their bug ID (6 x BUG-001, 3 x BUG-063).
  For each, `test_matches_main` and `test_cleaner_protocol_matches_main` assert that the outcome
  differs from the oracle and the exact new deleted list and delete calls; the oracle quirk checks
  for BUG-001/BUG-063 moved to `FIXED_QUIRKS` (oracle shows the bug, new code does not). Every
  other case still equals the oracle (calls, logs, stdout, errors). The fake delete operation now
  has a `result()`.
- **Tests:** `pytest -q` at 182466d: 42444 passed. After: 42462 passed (+18).
- **Owner actions:** see below.

## Owner decision

- BUG-001 and the direction rule: inverting `exception_regex` necessarily changes the selection for
  every run that passes `--exception_regex` for GCP IPs: it now deletes names that the old code kept
  (for example `exception_regex=["keep"]` used to delete only `keep-*` names and now deletes
  everything except them). This follows the task text ("excludes matching names") and the flag's
  documentation, and production passes no `exception_regex`, so no Jenkins job is affected. It cannot
  be done without deleting some address the old code kept, so it does not fit the "never delete more
  than today" sentence literally. If the owner wants a stricter rule, the alternative is to fail
  closed with a `ValueError` when `exception_regex` is non-empty for `--resource ip`.

## Owner action

None. No hash-locked test changed and no destructive invariant text in `CLEANUP_SAFETY.md` mentions
GCP IP `exception_regex` or delete errors (no SAF ID covers `crc/gcp/ip.py`).

## New bugs

- `crc/core/policy.py:200` `gcp_ip_exception_excludes` still implements the inverted test and is now
  unused by `crc/gcp/ip.py` (still covered by `tests/test_core_policy.py`, which pins the inverted
  behaviour; the module was out of this rung's scope). Exists on main: no (policy module is new).
  Follow-up: remove or flip it together with its test.
- `crc/gcp/ip.py` `ComputeIpClient.delete_address` builds a new `AddressesClient()` for every delete
  (as main did, `crc/gcp/ip.py:101` on main); exists on main: yes. Not fixed.
- `.result()` has no explicit timeout; the SDK default applies. A hung operation would block the run.
  Exists on main: no (there was no wait).
