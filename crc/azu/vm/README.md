# crc.azu.vm

## Purpose

Azure virtual machine cleaner (rung AZ-4). `VmCleaner` is a registered `Cleaner`
(`@register("azure", "vm")`): `plan()` lists the VMs of the configured resource group only, applies the tag and
age policy and reads each selected VM's instance view; `apply()` deletes the VM and waits for it,
then removes its `<vm>-NIC` NIC (through `crc/azu/vm_delete_helpers.py`), or powers the VM off.
`VM` is the adapter entry point `crc.py` uses; `from crc.azu.vm import VM` keeps working.

Modules (split by responsibility):

- `client.py`: the Azure SDK calls used, as typed Protocols
- `cleaner.py`: settings, name tally, summary logging, `VmCleaner` and the registry factory
- `adapter.py`: the `VM` class, a thin adapter that drives the cleaner VM by VM

## Public API

- `SdkVm`, `InstanceStatus`, `InstanceView`: Protocols of the SDK objects read (name, tags, time_created, statuses, display_status).
- `LongRunningOperation`: Protocol of the poller the begin_delete calls return (result()).
- `VmOperations`: Protocol of the four virtual_machines calls used (list, instance_view, begin_delete, begin_deallocate); tests pass fakes.
- `VmComputeClient`: Protocol of the compute client part used (virtual_machines).
- `NicOperations`: Protocol of the one network_interfaces call used (begin_delete, positional arguments).
- `VmNetworkClient`: Protocol of the network client part used (network_interfaces).
- `ComputeFactory`, `NetworkFactory`: callables returning those clients; injected through the constructor.
- `DEFAULT_INSTANCE_STATES`: the default allowed state, running.
- `VmSettings`: frozen filters and thresholds of one run.
- `Tally`: the VM, stopped VM and NIC names recorded so far.
- `log_summary()`: the closing log lines of main for an operation.
- `VmCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_vms, decide, state_allowed, process and act used by the adapter).
- `build_vm_cleaner()`: registry factory behind @register("azure", "vm"); reads resource_group, filter_tags, exception_tags, notags, age, custom_age_tag_key and instance_state from RunContext.options and builds the clients from Base.
- `VM`: adapter crc.py calls (delete(), stop(), get_deleted, delete_count, get_deleted_nic, nic_delete_count, get_stopped, stopped_count, base); runs the cleaner VM by VM in the order of main.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md` (SAF-006, SAF-009, SAF-010, SAF-042; SAF-011 to SAF-013 are not met, as on main).
- `plan()` only calls `list` and `instance_view`; `begin_delete`, `begin_deallocate` and the NIC `begin_delete` are called from `apply()` (and the adapter) only and never in a dry run (ARCH-005).
- Untagged VMs are skipped (SAF-042); filter tags need all keys, exception tags any key, notags all keys (`FILTER_VARIANTS.md` section 3, `crc.core.policy`).
- Age uses `crc.core.age` (`get_retention_age`, fail open, then `is_old`, which still reads `MAX_AGE`); the clock is injected (`RunContext.now`, `VM(clock=...)`). There is no age gate in `__init__` (SAF-011 is not met): an empty age selects every VM that passes the tag and status checks (SAF-006).
- A VM is acted on only when an allowed state equals its power state: the code after `PowerState/` of the first instance view status with such a code, lower-cased (BUG-010, BUG-198: no substring match, an empty state matches nothing, the allowed state is compared as given, so `Running` never matches). A VM without a `PowerState/` status is kept and counted as skip `no_power_state`; a failing status read keeps the VM (fail closed) and is logged.
- Per-VM errors (status, delete, power-off) are logged and swallowed, as on main; list errors and age errors propagate.
- Every call, the listing included, uses the configured resource group (`virtual_machines.list(resource_group)`, BUG-002 fixed): nothing outside it is listed or acted on, and an empty group raises `ValueError` before any SDK call. Stop is `begin_deallocate` (BUG-003 fixed); delete is unchanged. Other quirks in `docs/refactor/BUGS.md` (`BUG-199` to `BUG-212`).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Keep the call order of main in the adapter (list, age, status, delete, wait, NIC); behaviour fixes are separate rungs.
2. Reach the SDK only through the Protocols in `client.py`; new SDK calls need a Protocol entry and a fake in `tests/helpers_azure_vm.py`.
3. Tag and age decisions go through `crc.core.policy` and `crc.core.age`, never inline.
4. Update this README and `tests/test_azure_vm_parity.py` (the oracle is `tests/legacy/azu_vm.txt`, never edited) with any change.
