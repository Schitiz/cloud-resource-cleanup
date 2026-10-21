# GCP-3 review

## Coding summary

Rung GCP-3: `crc/gcp/vm.py` refactored into a `Cleaner` (lane `refactor/lane-gcp`). No behaviour change.

- **Summary.** `VmCleaner` (`cloud="gcp"`, `kind="vm"`, registered with `@register("gcp", "vm")` through
  `build_vm_cleaner`, supports DELETE and STOP) lists the zones and their instances in `plan()` (read-only)
  and calls `delete_instance` / `stop_instance` from `apply()` / `apply_instance()` only. Filtering uses
  `policy.state_in` (status), `policy.should_skip_by_tags` (exception labels any key, notags all keys),
  `policy.filter_tags_all_keys`, `policy.effective_age` and `policy.normalize_tags`; age uses
  `core_age.get_retention_age` and `core_age.is_old` (`MAX_AGE` still read inside `core.age`). The SDKs sit
  behind the typed Protocols `GcpVmClient` and `InstanceView`; `ComputeVmClient` keeps main's `with
  discovery.build(...)` (service closed right after zones and `InstancesClient()`, later deletes still use
  it). Settings are the frozen `VmSettings`. `VM` is the thin adapter `crc.py` uses (constructor,
  attributes, `get_deleted`, `delete_count`, `get_stopped`, `stopped_count`, `delete(instance_state)`,
  `stop()` unchanged; two optional trailing arguments `client` and `clock`). `crc.py` is not changed. The
  clock is `RunContext.now` (Cleaner) or the injected `clock` (adapter, default `datetime.datetime.now`).
  `plan_zone` is a lazy generator so the adapter keeps main's instance-by-instance interleaving. The
  module is one file of under 400 lines, so no subpackage split. The module lists zones, not regions, so
  there is no region-listing connectivity fallback to preserve; zone listing errors (auth and
  connectivity) propagate as on main and are covered.
- **Parity.** `tests/legacy/gcp_vm.txt` is the byte-identical `git show main:crc/gcp/vm.py`.
  `tests/test_gcp_vm_parity.py` runs the oracle (frozen `datetime`) and the adapter against the same fake
  `googleapiclient.discovery.build` and `compute_v1.InstancesClient` over the case table (delete and stop,
  dry run, status states, age edges, `MAX_AGE`, custom age label, label filter / exception / notags,
  untagged, API and iteration errors, zone listing errors, action errors, empty results, malformed
  instances) comparing SDK calls in order (including lazy page iteration and `close`), results, counts,
  logs, stdout and errors, then runs the same table through the registered Cleaner (plan then apply) and
  compares results, errors, stdout, delete/stop calls and the logged summary lines. Cleaner-path
  differences, inherent to plan-then-apply (as accepted in GCP-1/GCP-2): all zones are listed and filtered
  before the first action, so an error while listing or filtering stops before any action, and log lines
  interleave differently for more than one instance (compared as multisets, exact for at most one).
  Quirk checks assert the oracle and the new code show the same behaviour.
- **Test counts.** Before: 4028 passed. After: 4322 passed (+294: 280 in `tests/test_gcp_vm_parity.py`,
  14 in `tests/test_gcp_vm.py`). No existing test changed.
- **Gates.** `ruff check .`, `mypy` (strict), `lint-imports` and `pytest -q` pass (run locally on
  Python 3.12). `crc/gcp/vm.py` and `crc.gcp.vm` are removed from both ratchet lists in `pyproject.toml`; no
  new override (the `googleapiclient` one from GCP-2 is reused).
- **Open issues.** New quirks are in `docs/refactor/bugs/pending/GCP-3.md` (10 rows, none fixed): swallowed
  action errors, unawaited operations, run-aborting errors outside the per-instance `try`, strict timestamp
  format, closed service reused, unpaginated zones, cumulative summary, ignored stop state, unvalidated age
  and one documented divergence on non-conforming input (string `instance_state`, non-string label values).
  `Result.failed` and `Plan.skipped` stay empty because main reports neither.
- **Core change needed.** None.
- **FILTER_VARIANTS.md change needed.** None for behaviour. Optional: the `gcp/vm.py` row could note that
  the status gate is `instance_state` (default `["RUNNING"]`, only `delete()` accepts another list).
- **`crc/README.md` / `tests/legacy/README.md` / `tests/README.md` change needed.** Add `gcp_vm.txt`
  (exact `git show main:crc/gcp/vm.py`, used by `tests/test_gcp_vm_parity.py`) to `tests/legacy/README.md`;
  `crc/core/README.md` could say `gcp` / `vm` is now registered. All outside this lane's edit rights.
