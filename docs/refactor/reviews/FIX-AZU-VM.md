# FIX-AZU-VM

## Coding summary

- Bugs fixed: BUG-002, BUG-003, BUG-010, BUG-198 (all in `crc/azu/vm/`).
  - BUG-002: `VmCleaner.list_vms()` calls `virtual_machines.list(resource_group)` with
    `Base.resource_group` instead of `list_all()`. Nothing outside the configured group is listed or
    acted on; the group is never derived from the listed VM's id. An empty resource group raises
    `ValueError` before any SDK call.
  - BUG-003: stop calls `begin_deallocate` instead of `begin_power_off`; delete is unchanged.
  - BUG-010: the power state is the code after `PowerState/` of the first instance view status with
    such a code (not `statuses[1]`). A VM without one is kept; skip reason `no_power_state` (run-log
    `skip("no_power_state")`, plan reason `no_power_state`). A failing `instance_view` still keeps the
    VM and is logged as before.
  - BUG-198: `instance_state` entries are compared to the power state exactly (no substring; `""`
    matches nothing; `[]` still matches nothing).
- Bugs left: none. One part of the BUG-198 wording was narrowed, see "Owner decision".
- Files changed: `crc/azu/vm/client.py`, `crc/azu/vm/cleaner.py`, `crc/azu/vm/adapter.py`,
  `crc/azu/vm/README.md`, `crc/azu/README.md`, `tests/helpers_azure_vm.py` (fake gets `list`,
  `begin_deallocate`, status codes, per-VM `group`), `tests/test_azure_vm.py`,
  `tests/test_azure_vm_parity.py`, new `tests/test_azure_vm_fix.py`.
  No locked test, oracle, `CLEANUP_SAFETY.md`, `PLAN.md`, `STATUS.md` or `BUGS.md` edited.
- Parity test: the two call renames hit every case, so `test_azure_vm_parity.py` maps `list(rg)` back to
  `list_all` and `begin_deallocate` back to `begin_power_off` (`_oracle_shape`, documented there) and
  pins the new calls in `test_list_is_the_configured_group_only` and `test_stop_deallocates`. Six
  cases are marked `diverges` (BUG-198: `status-state-is-substring`,
  `status-empty-string-state-matches-all`; BUG-010: `status-single-entry-index-error`,
  `...-stop`, `status-empty-statuses`, `status-none-display`): the oracle still shows the bug and
  both new paths assert the new outcome (`test_fixed_quirk_diverges_from_main`). Every other case is
  still equal to the oracle, logs included.
- Tests (`pytest --collect-only`): 42444 at 182466d, 42470 now.
- Owner actions: none required.

## Owner decision

- BUG-198 "case-insensitive": the power state side (the Azure code) is lower-cased, but the allowed
  state from `instance_state` is compared as given. Comparing both sides case-insensitively would make
  `--resource_states '["Running"]'` match running VMs, which today matches nothing, so it would
  delete more than today and break the direction rule. Azure codes are always lower case, so every
  production value (`running`, `stopped`) behaves as intended. If the owner wants `Running` accepted,
  change `if state in states` in `VmCleaner.state_skip_reason` to
  `any(state == s.casefold() for s in states)` and flip the `["Running"]` row of
  `test_bug_198_state_is_matched_exactly`.

## New bugs

- Stopped-VM delete job vs deallocate: the production command `--resource_states '["stopped"]'`
  selects VMs whose power state is `stopped`. VMs stopped by `stop()` are now `deallocated`
  (BUG-003), so that job no longer sees them (it never matched `deallocated` before either, and
  powered-off VMs from other sources still match). Keeping more, so allowed here; the owner may want
  `"deallocated"` added to that Jenkins flag. Exists on main: no (consequence of BUG-003 fix).
- `crc/azu/vm/cleaner.py` `process()` / `plan()` count the VM as "selected" before the action; unchanged,
  exists on main yes (`crc/azu/vm.py:146-157`).

## Round 1 (Argon)

Scope reviewed: `git diff 182466d..HEAD` (`crc/azu/README.md`, `crc/azu/vm/README.md`,
`crc/azu/vm/adapter.py`, `crc/azu/vm/cleaner.py`, `crc/azu/vm/client.py`,
`docs/refactor/reviews/FIX-AZU-VM.md`, `tests/helpers_azure_vm.py`, `tests/test_azure_vm.py`,
`tests/test_azure_vm_fix.py`, `tests/test_azure_vm_parity.py`).

### Checklist verification

1. **Fixed bugs (`BUG-002`, `BUG-003`, `BUG-010`, `BUG-198`):**
   - `BUG-002` (`crc/azu/vm/cleaner.py:202-207`, `crc/azu/vm/client.py:67-69`): `VmCleaner.list_vms()` calls `virtual_machines.list(self._resource_group)` with `Base.resource_group` instead of `list_all()`, never derives a resource group from the VM's resource ID, and raises `ValueError` before any SDK call when `self._resource_group` is empty. Covered by `test_bug_002_*` in `tests/test_azure_vm_fix.py` and `other-resource-group-ignored` / `test_list_is_the_configured_group_only` in `tests/test_azure_vm_parity.py`.
   - `BUG-003` (`crc/azu/vm/cleaner.py:263-268`, `crc/azu/vm/client.py:79-81`): stop calls `virtual_machines.begin_deallocate(self._resource_group, vm_name)` instead of `begin_power_off`; delete (`begin_delete_vm_and_wait` + `delete_vm_primary_nic`) is unchanged. Covered by `test_bug_003_*` and `test_stop_deallocates`.
   - `BUG-010` (`crc/azu/vm/cleaner.py:112-121`, `:219-229`): `_power_state` scans `view.statuses` for the first status with a non-empty `PowerState/<state>` code rather than indexing `statuses[1]`; when none is present, `state_skip_reason` returns `"no_power_state"`, which keeps the VM and records `_logger.skip("no_power_state")` (`SKIPPED cloud=azure resource=vm reason=no_power_state count=...`) and `Skipped(..., reason="no_power_state")`. Covered by `test_bug_010_*` and four `diverges="BUG-010"` parity cases.
   - `BUG-198` (`crc/azu/vm/cleaner.py:118`, `:226-229`): power state is extracted as `code[len("PowerState/"):].casefold()` and matched by exact equality (`state in states`) instead of substring against `display_status` (`"run"` and `""` no longer match). Covered by `test_bug_198_*` and two `diverges="BUG-198"` parity cases.
2. **Direction rule and parity tests:**
   - Frozen oracle `tests/legacy/azu_vm.txt` is untouched.
   - `BUG-002` and `BUG-198` ("deletes what it should keep") only keep more or fail closed (`ValueError` on empty resource group before any SDK call). All unmarked parity cases assert exact equality with the oracle on SDK calls, order, selections, counts, logs, stdout, and errors; all 7 diverging cases are marked with `BUG-002`, `BUG-010`, or `BUG-198` and assert both the old oracle behaviour and the new outcome across both adapter and `Cleaner` paths.
3. **Production Jenkins commands:**
   - All six production `crc.py --cloud azure --resource_group "$RESOURCE_GROUP" --resource vm ...` commands run with identical CLI flags and selection (with the stopped-VM vs deallocated interaction noted under `## New bugs`). No new CLI flags, dependencies, async, or pydantic.
4. **Fail-closed paths:**
   - Empty `resource_group` raises `ValueError` in `list_vms()` before `self._compute()` or any SDK call; `instance_view` exceptions and missing `PowerState/` codes keep the VM without mutating calls.
5. **Protected / out-of-scope files:**
   - `tests/archtest/safety_lock.json`, all five hash-locked safety test files, `CLEANUP_SAFETY.md`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, `AGENTS.md`, `ARCHITECTURE.md`, `.cursor/**`, and `tests/archtest/**` are untouched.
6. **README sync (`ARCH-002`):**
   - `crc/azu/README.md` and `crc/azu/vm/README.md` `## Public API` and `## Safety Invariants` are synced and pass `ARCH-002`.
7. **Owner decision:**
   - The `instance_state` casing trade-off for `BUG-198` (preserving `["Running"]` as non-matching so the fix never deletes more than `main`) is clearly explained under `## Owner decision`.

### Findings (fixed in review)

- **NIT (fixed, `crc/azu/vm/cleaner.py:112-121`, `crc/azu/vm/client.py:51`):** Guarded `_power_state` against `statuses=None` (`statuses or ()`) and bare `"PowerState/"` codes with an empty suffix (`if state: return state`), so a malformed `"PowerState/"` code is treated as `no_power_state` and can never match `instance_state=[""]`. Added `empty-power-state` case and run-log `SKIPPED ... reason=no_power_state count=1` assertion in `tests/test_azure_vm_fix.py`.
- **NIT (fixed, `tests/test_azure_vm_parity.py:48-57`, `:115-120`, `:799`):** Tightened `_oracle_shape` to match `("list", group)` against the expected resource group (`case.resource_group or "env-rg"`) rather than any `list` call, and added `Case("other-resource-group-ignored", ..., diverges="BUG-002")` to `CASES` / `OLD_BEHAVIOUR`.
- **NIT (fixed, `crc/azu/vm/README.md:8`, `:19`, `:30`, `:41`):** Updated remaining prose references from `state_allowed` / `powers the VM off` / `power-off` to `state_skip_reason` / `deallocates the VM` / `deallocate` and listed `code` under `InstanceStatus`.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed! |
| `mypy` | Success: no issues found in 229 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 42474 passed in 138.30s |

Test count: 42444 at `182466d`, 42470 before review, 42474 after review (+4).

VERDICT: APPROVE
