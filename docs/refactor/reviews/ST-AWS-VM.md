## Coding summary

Rung ST-AWS-VM: status DONE (implemented, `make check` green, pushed to `refactor/lane-aws-vm`; not yet reviewed). Pure move, no behaviour change.

- **Move (`git mv`, history follows).** `crc/aws/vm.py` -> `crc/aws/vm/adapter.py` (`VM`, `VmRuntime`), `crc/aws/vm_cleaner.py` -> `crc/aws/vm/cleaner.py`, `crc/aws/vm_api.py` -> `crc/aws/vm/client.py`, `crc/aws/vm_scan.py` -> `crc/aws/vm/scan.py`. New `crc/aws/vm/__init__.py` re-exports every public name of the four old modules (`__all__`), so `from crc.aws.vm import VM` (`crc.py`, `crc/cli/vm_ops.py`) keeps working unchanged. Only import lines and the module docstrings that named the old paths changed inside the moved files.
- **Import sites updated.** `tests/test_aws_vm.py` and `tests/test_aws_vm_parity.py`: `crc.aws.vm_cleaner` -> `crc.aws.vm.cleaner` (import lines only, no assertion). No other file in `crc/`, `crc.py` or `tests/` imported the old sibling paths; none of the five hash-locked tests or `tests/legacy/**` does, so no shim module was needed.
- **monkeypatch targets.** None needed retargeting: the tests patch `boto3.client`, `boto3.session.Session` and `crc.service.init_logging`, which are looked up outside the moved modules.
- **Docs.** New `crc/aws/vm/README.md` with the four ARCH-002 sections (Public API synced with `__all__` and public defs); the VM entries of `crc/aws/README.md` trimmed to a pointer. `docs/refactor/bugs/pending/ST-AWS-VM.md`: no new bugs.
- **Not touched.** `pyproject.toml` (the `crc/aws/vm.py` ratchet entry was already removed in AWS-3), `tests/archtest/legacy_baseline.txt` (it still lists `crc/aws/vm.py`, which no longer exists; baseline entries may only be removed by its owner), `BUGS.md`, `STATUS.md`, `FILTER_VARIANTS.md`, `crc/README.md`, `tests/README.md`, `tests/legacy/**`.
- **Gates.** `make check` (ruff, mypy, import-linter, pytest incl. archtests) green. `pytest -q` before: 42213 passed; after: 42213 passed (same count).
