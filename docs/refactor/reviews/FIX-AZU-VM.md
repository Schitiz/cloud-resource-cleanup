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
