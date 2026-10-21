# GCP-2 review

## Coding summary

Rung GCP-2: `crc/gcp/disk.py` refactored into a `Cleaner` (lane `refactor/lane-gcp`). No behaviour change.

- **Summary.** `DiskCleaner` (`cloud="gcp"`, `kind="disk"`, registered with `@register("gcp", "disk")`
  through `build_disk_cleaner`) lists the zones and their disks in `plan()` (read-only) and calls
  `delete_disk` from `apply()` / `apply_disk()` only. Filtering uses `policy.exception_regex_match_matches`
  (`re.match`), `policy.exception_tags_any`, `policy.filter_tags_any_key`, `policy.effective_age` and
  `policy.normalize_tags`; age uses `core_age.get_retention_age` and `core_age.is_old` (`MAX_AGE` is still
  read inside `core.age`). The SDKs sit behind the typed Protocols `GcpDiskClient` and `DiskView`;
  `ComputeDiskClient` builds the discovery service lazily once per run, builds `DisksClient` right after the
  zones were listed (as main) and `close()` closes the service (the `with` of main). Settings are the frozen
  `DiskSettings`. `Disk` is the thin adapter `crc.py` uses (constructor, attributes, `get_deleted`, `count`,
  `delete(disk_state=...)` unchanged; two optional trailing arguments `client` and `clock`). `crc.py` is not
  changed. The clock comes from `RunContext.now` (Cleaner) or the injected `clock` (adapter, default
  `datetime.datetime.now` as an uncalled reference, so ARCH-003 holds). `plan_zone` is a lazy generator so the
  adapter keeps main's disk-by-disk interleaving of listing, deleting and recording.
- **Parity.** `tests/legacy/gcp_disk.txt` is the byte-identical `git show main:crc/gcp/disk.py`.
  `tests/test_gcp_disk_parity.py` runs the oracle (with a frozen `datetime`) and the adapter against the same
  fake `googleapiclient.discovery.build` and `compute_v1.DisksClient` over 112 cases (dry run, age edges,
  `MAX_AGE`, custom age label, label filter and exceptions, regexes, untagged, Slack grouping, zone listing
  errors including auth and connectivity (no fallback on main), disk listing and iteration errors, delete
  errors, empty results, malformed disks and timestamps, ignored `age` / `notags` / `name_regex`) comparing
  SDK calls in order (including lazy page iteration), results, count, logs, stdout and errors. The same table
  runs through the registered Cleaner (plan then apply) and the logged summary lines match. Cleaner path
  differences, inherent to plan-then-apply and as accepted in GCP-1: all zones are listed and filtered before
  the first delete, so an error raised while listing or filtering stops before any delete, and log lines
  interleave differently for more than one disk (compared as multisets, exact for at most one disk). 55
  quirk checks assert the oracle and the new code show the same behaviour.
- **Test counts.** Before: 2879 passed. After: 3191 passed (+312: 285 in `tests/test_gcp_disk_parity.py`,
  27 in `tests/test_gcp_disk.py`). No existing test changed.
- **Gates.** `make check`: `ruff check .`, `mypy` (strict), `lint-imports`, `pytest -q` all pass.
  `crc/gcp/disk.py` and `crc.gcp.disk` are removed from both ratchet lists in `pyproject.toml`. One per-SDK
  mypy override was added, `googleapiclient` / `googleapiclient.*` with `ignore_missing_imports` (the package
  ships no stubs or `py.typed`); `google-cloud-compute` is typed, so it needs none.
- **Open issues.** New quirks are in `docs/refactor/bugs/pending/GCP-2.md` (16 rows, none fixed): no
  positive-age check on `detach_age`, swallowed delete errors, unawaited delete operations, run-aborting
  errors outside the per-disk `try`, unpaginated zone listing, zonal disks only, and Slack-mode count quirks.
  `Result.failed` stays empty and `Plan.skipped` stays empty because main reports neither failed deletes nor
  skip reasons; behaviour fixes belong to a later rung.
- **Core change needed.** None. `crc/core/policy.py` and `crc/core/age.py` already have every function used.
- **FILTER_VARIANTS.md change needed.** None for behaviour. Optional: the `gcp/disk.py` row could say that
  `states` (`["Unattached"]`) and `delete(disk_state)` are also never applied (recorded as a pending row).
- **`crc/README.md` / `tests/legacy/README.md` / `tests/README.md` change needed.** Add `gcp_disk.txt`
  (exact `git show main:crc/gcp/disk.py`, used by `tests/test_gcp_disk_parity.py`) to
  `tests/legacy/README.md`; `crc/core/README.md` could say `gcp` / `disk` is now registered. Both are
  outside this lane's edit rights.
