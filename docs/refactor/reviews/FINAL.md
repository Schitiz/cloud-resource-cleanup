## Coding summary

Rung FINAL, README sweep. Docs only: no `.py`, `pyproject.toml`, `Makefile`, `.github/`, `tests/archtest/`, `tests/legacy/*.txt`, `AGENTS.md`, `ARCHITECTURE.md`, `CLEANUP_SAFETY.md`, `docs/refactor/PLAN.md` or `.cursor/` file changed. Each README keeps the four ARCH-002 sections and its synced Public API.

Files changed and what was stale:

- `crc/README.md`: the direct modules were called "legacy, not yet refactored". `service.py` and `utils.py` are refactored and strict-checked (parity: `tests/test_crc_service_parity.py`, `tests/test_crc_service_is_old_parity.py`, `tests/test_crc_utils_parity.py`); `aws/azu/gcp/oci` were listed as "legacy". The note "Not synced with ARCH-002" is still true but its reason was wrong: `package_dirs` in `tests/archtest/readmes.py` skips the modules directly in `crc/`, and `crc/__init__.py` has no `__all__` (not "the modules are legacy"). The note now says so. The `crc/cli/` text was already correct.
- `crc/aws/README.md`: "Legacy AWS cleaners", "Partly refactored", "every other module is legacy" (all modules are refactored); `spot_instance_requests.py` listed as a module (it is the package `spot_instance_requests/`); Public API intro listed only some modules; "legacy adapter class" and "not as another legacy class"; Extension Rule 4 told readers to remove a module from the ruff and mypy lists (the lists hold only five test files).
- `crc/azu/README.md`, `crc/gcp/README.md`, `crc/oci/README.md`: "Legacy Azure/GCP cleaners" headers, "Partly refactored" (GCP), "legacy adapter", "legacy Base", "not as another legacy class", and the extension rule about removing a module from the legacy lists.
- `crc/aws/{disk,vm,vpc,spot_instance_requests}/README.md`, `crc/azu/{vm,spot_vm}/README.md`, `crc/gcp/spot_vm/README.md`, `crc/oci/{vm,spot_vm}/README.md`: "legacy class / entry point / adapter / Base / tests" wording; the adapter classes remain the entry point `crc/cli` uses.
- `crc/core/README.md`: said only `aws` / `keypair`, `ip` and `kms` are registered and that `crc.py` sends notifications; every cleaner of the four clouds is registered (lists them), and `crc/cli` (not `crc.py`) sends them. States that wiring `crc/cli` through `engine.run` is deferred (`docs/refactor/PLAN.md`).
- `tests/README.md`: "tests of the legacy cloud modules", missing CLI, service, utils and all other parity tests, `test_azure_*` pattern; now lists every parity test file, the five hash-locked files and the helpers.
- `tests/legacy/README.md`: listed three oracles; now a table of all 30 oracles with their `main` source path and parity tests, plus the notify oracle that lives in `tests/legacy_crc_notify_reference.txt`.
- `docs/refactor/README.md`, `docs/refactor/reviews/README.md`: rung and review lists stopped at R2c; "legacy module" in the `FILTER_VARIANTS.md` row.
- Checked and left unchanged (still true): `crc/cli/README.md`, `crc/notify/README.md`, `crc/oci/{disk}/README.md`, `crc/aws/{...}` safety text, `docs/README.md`, `docs/refactor/bugs/**/README.md`, `tests/archtest/README.md`.

Every path written was checked to exist; the `main` source paths in the oracle table were checked with `git cat-file -e main:<path>`. No SAF or BUG ID was added.

## Out of scope: docs found wrong, not changed

- `.py` docstrings still say "legacy class": `crc/aws/disk/__init__.py:6`, `crc/aws/vpc/__init__.py:6`, `crc/oci/spot_vm/adapter.py:3` (and likely the other adapter module docstrings). Wording only; `.py` files are out of scope.
- `docs/refactor/STATUS.md` row "Final (docs)" still says "in progress" and "README wording sweep follows as a Cursor rung"; the owner or driver updates it.
- `docs/refactor/FILTER_VARIANTS.md` intro (rung R1b) says "Read from the code on `refactor/python-agentic`" and calls the modules "legacy modules" with `file:line` citations of the pre-refactor files. The citations are `main` file:line, not the current layout; not rewritten here.
- `AGENTS.md` line 10 says the branch is `refactor/python-agentic` (guardrail file) and `docs/refactor/PLAN.md` "Final" row mentions the README sweep (guardrail file); both untouched.
- `make check` in this environment: `mypy` reports 17 `import-untyped` errors for `google.cloud`, `azure.*` and `google.api_core` (installed SDKs without `py.typed`; one `unused-ignore` in `tests/test_gcp_base.py:15`). It is the same before and after this change (no `.py` or config file touched), so it comes from the VM's package versions, not from this rung. Not fixed (config out of scope).
