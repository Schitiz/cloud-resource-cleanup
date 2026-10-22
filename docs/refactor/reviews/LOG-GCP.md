## Coding summary

Rung LOG-GCP (GCP lane of the LOG family, contract in `docs/refactor/LOGGING.md`). Log text and
levels only: no selection, SDK call, call order, delete/stop, Slack, Influx, CLI flag or exit code
changed.

Bug IDs handled: BUG-358 (GCP part: disk/VM label dump, IP address dump and the per-disk "Skipping
leftover Spot disk" line are DEBUG, text unchanged), BUG-361 (GCP part: one `REGION` line per zone
or region walked, for vm, spot_vm, disk and ip), BUG-362 (GCP part: swallowed per-resource errors
call `runlog.current().fail()`; the inline error lines stay). `ACTION` lines and skip reasons
(BUG-360 plumbing) are wired for all four cleaners. Rows in `BUGS.md` are not edited (other lanes
do; GCP part is done, the rows stay open until every lane is merged).

Files changed:

- `crc/gcp/_scan.py` (new): `ZoneScan` (scanned/selected counters, `finish()` logs REGION through
  `runlog.current()`; `time.monotonic` for the seconds) and `log_action()`.
- `crc/gcp/vm.py`, `crc/gcp/disk.py`: `plan_zone` counts scanned/selected and logs REGION when the
  lazy listing is exhausted; the filter chain moved into `_reject()` / `_exception_reason()` (same
  order, same short circuits) returning a skip reason that is counted (`state`, `exception_tag`,
  `exception_regex`, `filter_mismatch`, `attached`, `never_detached`, `too_young`); `apply_*` log
  ACTION after a successful call (`would_*` in a dry run) and call `fail()` on a swallowed error;
  a dry-run `plan()` logs the would-be ACTION lines; label dump `logging.debug`. Both files are at
  exactly 400 lines (ARCH-004), so a few docstrings were shortened.
- `crc/gcp/ip.py`: address dump DEBUG, REGION per region, skip reasons (`state`, `filter_mismatch`,
  `exception_regex`), ACTION in `apply_region` (and in a dry-run `plan()`), a delete error is
  recorded with `fail()` and re-raised unchanged (the IP cleaner never swallowed errors).
- `crc/gcp/spot_vm/cleaner.py`, `instances.py`, `disks.py`, `adapter.py`: new `SpotVMCleaner.scan_zone()`
  (used by `plan()` and the adapter, same call order) logs REGION; `list_zone` failure calls
  `region_skipped()` and logs no REGION; new `instances.reject_reason()` (`is_selected` is
  `reject_reason() is None`); skip reasons `state`, `not_spot`, `managed_or_gke`, `exception_tag`,
  `filter_mismatch`, `too_young`, `disk_exception_tag`; failures (evaluate, delete, leftover disk
  read or delete, incomplete operation) call `fail()`; "Skipping leftover Spot disk" is DEBUG.
- READMEs: `crc/gcp/README.md` (`ZoneScan`, `log_action`, logging invariant),
  `crc/gcp/spot_vm/README.md` (`scan_zone`, `reject_reason`).
- Tests: `tests/helpers_log_fix.py` (rule `BUG-358`), `tests/test_log_fix_helpers_gcp.py` (rule unit
  tests), `tests/test_gcp_runlog.py` (new, 17 exact-line tests: dry run, real run, failure, skipped
  region, no-run silence), the four parity tests `tests/test_gcp_{vm,disk,ip,spot_instances}_parity.py`
  (every log comparison goes through `expected_logs(old.logs, {"BUG-358"})`, plus one explicit
  `oracle != new` case per file). Oracles untouched; calls, results, stdout and errors still equal.

Test count: 42256 before (LOG-0 result at 7437ac5), 42286 after. `make check` (ruff, mypy, lint-imports, pytest) green.

Left / notes:

- `Updating age for ...` (per labelled resource with a custom age tag) stays INFO, like LOG-0 left
  `Overwriting resource age`; it is not in the contract list. Candidate for a later LOG rung.
- The spot_vm leftover disks are not ACTION lines (resource=spot_instances counts VMs only);
  their failures are in `FAILED` and their label skips under `disk_exception_tag`.
- `notags` and `exception_tags` share the reason `exception_tag` in `vm` (one policy call).
- `tests/helpers_log_fix.py` `BUG-358` matches INFO dict dumps (`{...}`), the `namespace(...)` test
  double of an address, and the Spot disk skip line; other lanes add their own shapes to the same
  rule when merging (this lane only needed these).
- No locked safety test asserts these log levels (`test_gcp_spot_vm.py` has no log assertion);
  none was touched. No `## Owner action` needed.
- The runlog API had everything needed; nothing was worked around. `crc/core` and `crc/cli` untouched.
