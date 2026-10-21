## Coding summary

**Rung ST-OCI-VM: `crc/oci/vm.py` and `crc/oci/vm_api.py` are now the subpackage `crc/oci/vm/`. Status: done, `make check` green.**

- **What moved (`git mv`, no logic edits).** `crc/oci/vm_api.py` -> `crc/oci/vm/client.py` (typed Protocols, `OciComputeApi`, `compute_api_for`). `crc/oci/vm.py` -> `crc/oci/vm/cleaner.py` (`VmSettings`, `VmCleaner`, `build_vm_cleaner`, the summary logging) and `crc/oci/vm/adapter.py` (`VmRuntime`, `VM`); the code was cut at the `VM` class and the imports adjusted. `adapter.py` imports the private `_log_summary` from `cleaner.py` (a private helper, not renamed). `crc/oci/vm/__init__.py` re-exports every name callers import (`VM`, `VmRuntime`, `VmSettings`, `VmCleaner`, `build_vm_cleaner`, `DEFAULT_INSTANCE_STATES`, `ApiFactory`, `ComputeApi`, `OciComputeApi`, `SdkInstance`, `STOP_ACTION`, `compute_api_for`), so `from crc.oci.vm import VM` in `crc.py` and `crc/cli/vm_ops.py` is unchanged.
- **Importers.** `crc.py`, `crc/cli/**` and `tests/legacy/**` need no change. `tests/test_oci_vm.py`: one import line changed (`from crc.oci.vm_api import ...` -> `from crc.oci.vm.client import ...`); no assertion touched. `tests/test_oci_vm_parity.py` imports `crc.oci.vm` only, unchanged. No hash-locked safety test imports the old `vm_api` path, so no shim module was needed (`crc/oci/vm_api.py` is gone).
- **monkeypatch targets.** None retargeted: the tests patch `oci.*` SDK attributes, `crc.service.init_logging` and environment variables, none of which live in the moved modules.
- **README.** New `crc/oci/vm/README.md` with the four ARCH-002 sections (Safety Invariants cite SAF-006 to SAF-013). The OCI section of `crc/oci/README.md` is trimmed to a pointer (module list, VM symbol list and VM safety bullet).
- **pyproject.toml.** Not touched; neither moved file was on a legacy list.
- **Gates.** `make check`: ruff, mypy, lint-imports and pytest green. Test count unchanged (see the commit summary: 42213 collected before and after).
- **Open issues.** None new; `docs/refactor/bugs/pending/ST-OCI-VM.md` records that no quirk was found. BUG-158 to BUG-171 still apply.
- **Needed changes outside this lane (not made).** `docs/refactor/STATUS.md` (record the rung), `crc/README.md` and `tests/README.md` if they name `crc/oci/vm.py` or `vm_api.py`, and `docs/refactor/bugs/pending/README.md` (list `ST-OCI-VM.md`).
