# Pending bugs: ST-OCI-VM (`crc/oci/vm/`)

Columns as in `docs/refactor/BUGS.md`. Locations cite `main` (`git show main:crc/oci/vm.py`).

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | `terminate_instance(instance.id)` passes no flags, so the SDK defaults apply: the boot volume is deleted (`preserve_boot_volume` defaults to false) but data volumes created at launch are kept (`preserve_data_volumes_created_at_launch` defaults to true). Those volumes become `AVAILABLE` and keep billing; only the `oci` / `disk` cleaner can remove them later, and only if they match its tag filter and age. The refactor keeps the call unchanged (`OciComputeApi.terminate_instance` in `crc/oci/vm/client.py`) | `crc/oci/vm.py:156` | yes | keeps what it should delete | low | ST-OCI-VM (round 2) | open |

The rung itself is a pure move of `crc/oci/vm.py` and `crc/oci/vm_api.py` into the subpackage
`crc/oci/vm/` and introduces no quirk. The known OCI VM rows are `BUG-158` to `BUG-171` in `BUGS.md`.
