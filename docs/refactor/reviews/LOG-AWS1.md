## Coding summary

Rung LOG-AWS1 (logging lane for `crc/aws/vm`, `crc/aws/spot_instance_requests`, `crc/aws/disk`;
contract in `docs/refactor/LOGGING.md`). Log text and levels only: nothing selected, deleted,
stopped, posted or written changed, no SDK call or its order changed, no CLI flag or exit code.

Files changed:

- `crc/aws/vm/cleaner.py`, `crc/aws/vm/adapter.py`: the raw tag list of each instance is logged at
  DEBUG (BUG-358); REGION via the new `note_region()`; ACTION via `apply_region()` (real run) and the
  new `note_dry_run()` (dry run, Cleaner and adapter paths); `skip()` with `no_tags`, `exception_tag`,
  `too_young`; `fail()` for the per-instance processing error, the missing Name tag (logged at ERROR)
  and a failed terminate/stop; `region_skipped()` inside `skip_region()`.
- `crc/aws/disk/volumes.py`, `cleaner.py`, `detach.py`: the INFO `Skipping volume ...` lines are DEBUG
  with the same text; skip reasons (`state`, `attached`, `multi_attach`, `untagged`, `filter_tags`,
  `name_regex`, `sensitive_yb_task`, `kubernetes_csi`, `exception_tag`, `notags`, `exception_regex`,
  `too_young`, `no_create_time`, `invalid_age_tag`, `no_age_floor`, `recently_attached`,
  `cloudwatch_incomplete`, `detach_age_zero`); REGION in `plan_region()`; ACTION `would_delete` in
  `note_dry_run()` and `deleted` after `delete_volume`; `fail()` for every swallowed per-volume
  error, region error, failed delete and CloudWatch lookup error; `region_skipped()` for connectivity
  and unauthorised region skips.
- `crc/aws/spot_instance_requests/{cleaner,adapter,requests,cleanup,preview,leftover,volumes}.py`:
  the INFO `Skipping leftover volume`, `Skipping tagged leftover volume` and `Skipping cancelled spot
  request` lines are DEBUG with the same text; REGION in `list_matches()` (listing plus filtering
  time); ACTION `deleted` for each cancelled request, terminated instance and deleted volume,
  `would_delete` for the same three in a dry run (`preview_request` got an optional `region`);
  skip reasons (`no_tags`, `cancelled_no_instance`, `exception_tag`, `filter_tags`,
  `invalid_age_tag`, `too_young`, `volume_protected`, `already_cancelled_done`, `sweep_gates`);
  `fail()` for describe, cancel, terminate, tag, wait/delete, sweep and region-listing errors;
  `region_skipped()` for connectivity skips. `filtered_requests` got an optional `region`.
- READMEs of the three packages (Public API for `note_region`/`note_dry_run`, logging invariant).
- Tests: `tests/helpers_log_fix.py` (BUG-358 rule `_bug_358_aws_vm` behind a `_BUG_358_PARTS` tuple
  so other lanes can append theirs; the BUG-356 rule now also turns the INFO `Skipping <resource>`
  lines of this lane into DEBUG; BUG-361/362 are identity rules), the three parity tests (every log
  comparison goes through `expected_logs(old.logs, FIXED_BUGS)`, plus an explicit
  `oracle != new` test per package), and the new `tests/test_aws_log_fix.py` (exact REGION/ACTION/
  SKIPPED/ERRORS/FAILED/RESULT lines: dry run, real run, failure, connectivity skip, skip reasons).

Bug IDs handled: BUG-358 (AWS VM tag dump to DEBUG, fixed for AWS VM), BUG-356 (the per-resource
`Skipping ...` lines of disk and spot to DEBUG; the age-check lines were done in LOG-0), BUG-361
(REGION per region, `region_skipped`) and BUG-362 (`fail()` at every swallowed per-resource error) for
these three cleaners. BUG-360 is not in this lane.

Test count: 42256 at 7437ac5 (LOG-0 review), 42271 after (`make check` green: ruff, mypy, lint-imports, pytest).

## Notes and choices

- Parity runs have no begun run, so `runlog.current()` is unattached and logs nothing: the new lines
  never appear in the parity logs. BUG-361/362 therefore have identity rules in `expected_logs` and
  are pinned by `tests/test_aws_log_fix.py` (separate exact assertion, as the contract says). The
  `oracle != new` requirement is met by the BUG-358 (VM) and the `Skipping ...` (disk, spot) tests.
- Lines of an acted resource (`Deleted volume`, `Instance X deleted.`, `Cancelled spot request`,
  `Dry run: would delete ...`) stay at INFO: they are few and the contract does not list them. The
  ACTION line is the machine-readable twin. WARNING and ERROR skip lines (missing CreateTime, invalid
  custom age tag, incomplete CloudWatch answer) keep their level because they flag an anomaly.
- A missing Name tag on an instance is logged at ERROR on main, so it is a `fail()` (not a `skip()`).
- Unauthorised/opt-in region skips of the disk cleaner also count as `region_skipped` (the contract
  names connectivity skips only; this is a skipped region either way).
- `REGION seconds` for spot is the time of listing plus filtering, not of the cleanup that follows
  (the cleanup loop is a per-request closure with no region boundary); VM and disk measure the same
  span (list and filter). The spot `scanned` is the number of requests the region returned.
- `fail()` is not called for the secondary marker-invalidation errors of spot (`Failed to clear
  scope tag ...`, `Failed to invalidate ...`): they follow a primary failure that is recorded.
- A failed region (`describe_*` error, region-level exception) has `id=-` in its FAILED line.
- `ACTION name` is `-` for disk and spot (the disk label has spaces; spot has no name).
- Runlog API workaround: none needed. `RunLog.region()` takes `seconds` from the caller, so the
  cleaners use `time.monotonic()` (not injectable); the unit tests accept `seconds=0`.
- No locked safety test asserts these log levels; none touched.

## Left

Nothing. BUG rows in `docs/refactor/BUGS.md` are not edited here (other lanes edit it); the status
of BUG-358 (AWS VM part), BUG-361 and BUG-362 (AWS VM, disk, spot parts) should be set at
integration.
