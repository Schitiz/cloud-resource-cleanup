## Coding summary

Rung LOG-AZU (Azure lane of the LOG family, contract in `docs/refactor/LOGGING.md`). Log text and
levels only: what is selected, deleted or stopped, the SDK calls and their order, Slack, Influx,
CLI flags and exit codes are unchanged.

Files changed:

- `crc/azu/_runlog.py` (new): thin Azure helpers over `crc.core.runlog.current()` (`started`,
  `region_done`, `skip`, `acted`, `failed`, `reason_slug`). Azure has no regions, so one REGION line
  per resource group with `region=<resource group>`. Skip reasons are mapped to short snake_case
  slugs (`filter_tags`, `exception_tag`, `exception_or_notags`, `notags`, `too_young`, `state`,
  `attached`, `name_regex`, `exception_regex`, `not_spot`, `no_creation_time`, ...; unknown
  reasons are slugged). With no `begin()` the calls count and log nothing.
- `crc/azu/disk.py`, `ip.py`, `nic.py`, `vm/cleaner.py`, `vm/adapter.py`, `spot_vm/cleaner.py`,
  `spot_vm/removal.py`, `spot_vm/__init__.py`, `vm_delete_helpers.py`: REGION / ACTION / skip /
  fail calls in the adapters `crc.py` runs and in the Cleaner `plan()` / `apply()` paths (a dry-run
  `plan()` logs the `would_*` ACTION lines; `apply()` logs only real ones, so plan + apply never
  double count). `VmCleaner.process` now returns a bool (acted on); `AzureDiskCleaner.delete_disk`
  and `AzureNicCleaner.attempt_delete` gained a keyword `record` (default True).
- `crc/azu/README.md`: Public API entry for the helpers, logging invariant.
- Tests: `tests/test_azure_runlog.py` (new, 15 tests: disk, ip, nic, vm, spot VM real run, dry run,
  failure, skipped reasons, DEBUG tag dumps, no double action from plan+apply, unattached run logs
  nothing); `tests/helpers_log_fix.py` (new rule `BUG-358`: raw tag dump = str of a dict or
  `None` becomes DEBUG; `BUG-356` also matches `Skipping leftover Spot disk ...`);
  parity tests `test_azure_disk_parity.py`, `test_azure_vm_parity.py`,
  `test_azure_spot_instances_parity.py` compare logs through `expected_logs(old.logs, BUGS)` and
  assert `oracle != new` for at least one case per bug (repeat-delete cases for disk and VM,
  a new leftover-disk case for the Spot VM). IP, NIC and the delete helpers parity tests are
  unchanged (their existing lines keep level and text).

Bug IDs handled:

- BUG-358 (Azure disk and VM): `logging.info(disk.tags)` and `logging.info(vm.tags)` are DEBUG.
- BUG-356 (Azure part): the per-leftover-disk skip lines of the Spot VM remover ("Skipping leftover
  Spot disk ...", two lines) are DEBUG with unchanged text.
- BUG-361 (Azure): one REGION line per resource group for vm, spot_instances, disk, ip, nic.
- BUG-362 (Azure): swallowed per-resource errors are recorded with `fail()`: VM processing errors
  (adapter `process` and `apply()`), VM status read error, Spot VM delete error and dry-run preview
  error, leftover Spot disk delete errors, NIC delete after three attempts, VM primary NIC after
  24 attempts (`vm_delete_helpers`). Existing inline error lines stay.
- BUG-360 (Azure): ACTION and SKIPPED lines feed the RESULT line (header and footer are LOG-0).

Test count: 42256 before (LOG-0 tip 7437ac5), 42272 after. `make check` (ruff, mypy, lint-imports,
pytest) green on Python 3.12.3.

## Notes and left

- `Skipping Spot VM <name>: no creation time (age check not possible)` stays WARNING: it is a
  fail-closed signal for an uncertain age, not routine per-resource noise. It is counted as
  `no_creation_time` in SKIPPED. Change it to DEBUG in a follow-up if the owner prefers.
- "Updating age for disk/vm/Spot VM", "Deleted ...", "Deleting ...", the per-leftover-disk
  "has delete_option=" lines and every summary line stay INFO / WARNING (not in the contract list).
- REGION is logged after the loop, so in the adapters the ACTION lines come before it; in the
  Cleaner path `plan()` logs REGION first and `apply()` logs the ACTION lines later.
- Per-leftover-disk skips (outside the resource group, protected by tags) are counted under
  `leftover_disk_outside_resource_group` and `leftover_disk_exception_tag` in the Spot VM SKIPPED
  lines; they count disks, not VMs.
- The NIC deleted together with a VM and the Spot VM leftover disks produce no ACTION line (the
  contract is one ACTION per resource of the run's `--resource`); only their failures are listed.
- The `BUG-358` rule in `tests/helpers_log_fix.py` is generic (str of a dict, or `None`); the GCP and
  OCI lanes edit the same file in parallel, so expect a trivial merge there.
- Errors that propagate (disk, IP delete, Spot VM list failure) are not recorded with `fail()`:
  they are not swallowed, the CLI still prints RESULT from its `finally`.
- No locked safety test asserts these log levels (`tests/test_azu_spot_vm.py` has no level
  assertion and stays untouched). No `## Owner action` needed.
- No bugs found beyond those already in BUGS.md.
