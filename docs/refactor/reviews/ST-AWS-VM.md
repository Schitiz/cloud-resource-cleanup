## Coding summary

Rung ST-AWS-VM: status DONE (implemented, `make check` green, pushed to `refactor/lane-aws-vm`; round 1 reviewed: APPROVE). Pure move, no behaviour change.

- **Move (`git mv`, history follows).** `crc/aws/vm.py` -> `crc/aws/vm/adapter.py` (`VM`, `VmRuntime`), `crc/aws/vm_cleaner.py` -> `crc/aws/vm/cleaner.py`, `crc/aws/vm_api.py` -> `crc/aws/vm/client.py`, `crc/aws/vm_scan.py` -> `crc/aws/vm/scan.py`. New `crc/aws/vm/__init__.py` re-exports every public name of the four old modules (`__all__`), so `from crc.aws.vm import VM` (`crc.py`, `crc/cli/vm_ops.py`) keeps working unchanged. Only import lines and the module docstrings that named the old paths changed inside the moved files.
- **Import sites updated.** `tests/test_aws_vm.py` and `tests/test_aws_vm_parity.py`: `crc.aws.vm_cleaner` -> `crc.aws.vm.cleaner` (import lines only, no assertion). No other file in `crc/`, `crc.py` or `tests/` imported the old sibling paths; none of the five hash-locked tests or `tests/legacy/**` does, so no shim module was needed.
- **monkeypatch targets.** None needed retargeting: the tests patch `boto3.client`, `boto3.session.Session` and `crc.service.init_logging`, which are looked up outside the moved modules.
- **Docs.** New `crc/aws/vm/README.md` with the four ARCH-002 sections (Public API synced with `__all__` and public defs); the VM entries of `crc/aws/README.md` trimmed to a pointer. `docs/refactor/bugs/pending/ST-AWS-VM.md`: no new bugs.
- **Not touched.** `pyproject.toml` (the `crc/aws/vm.py` ratchet entry was already removed in AWS-3), `tests/archtest/legacy_baseline.txt` (it still lists `crc/aws/vm.py`, which no longer exists; baseline entries may only be removed by its owner), `BUGS.md`, `STATUS.md`, `FILTER_VARIANTS.md`, `crc/README.md`, `tests/README.md`, `tests/legacy/**`.
- **Gates.** `make check` (ruff, mypy, import-linter, pytest incl. archtests) green. `pytest -q` before: 42213 passed; after: 42213 passed (same count).

## Round 1 (Argon)

Scope reviewed: `git diff -M d109ee5..HEAD` (`crc/aws/vm/__init__.py`, `crc/aws/vm/adapter.py`, `crc/aws/vm/cleaner.py`, `crc/aws/vm/client.py`, `crc/aws/vm/scan.py`, `crc/aws/vm/README.md`, `crc/aws/README.md`, `tests/test_aws_vm.py`, `tests/test_aws_vm_parity.py`, `docs/refactor/bugs/pending/ST-AWS-VM.md`, `docs/refactor/reviews/ST-AWS-VM.md`) against `AGENTS.md` and `.cursor/skills/crc-python-refactor/REVIEW_CHECKLIST.md`.

### Verification

1. **Pure move (`git diff -M d109ee5..HEAD`):**
   - `crc/aws/vm.py` -> `crc/aws/vm/adapter.py` (`R097`): only the module docstring reference (`crc.aws.vm_cleaner.VmCleaner` -> `crc.aws.vm.cleaner.VmCleaner`) and internal imports (`crc.aws.vm_scan` -> `crc.aws.vm.scan`, `crc.aws.vm_api` -> `crc.aws.vm.client`, `crc.aws.vm_cleaner` -> `crc.aws.vm.cleaner`) changed; zero logic changes.
   - `crc/aws/vm_cleaner.py` -> `crc/aws/vm/cleaner.py` (`R098`): only the module docstring note (`(`adapter.py`)`) and internal imports (`crc.aws.vm_scan` -> `crc.aws.vm.scan`, `crc.aws.vm_api` -> `crc.aws.vm.client`) changed; zero logic changes.
   - `crc/aws/vm_api.py` -> `crc/aws/vm/client.py` (`R100`): 100% byte-for-byte rename.
   - `crc/aws/vm_scan.py` -> `crc/aws/vm/scan.py` (`R098`): only the import line (`crc.aws.vm_api` -> `crc.aws.vm.client`) changed; zero logic changes.
   - `crc/aws/vm/__init__.py`: new subpackage entry point that re-exports all 24 public symbols of the four modules in `__all__`.
2. **Import resolution, tests, and safety locks:**
   - `from crc.aws.vm import VM` in `crc.py:16` and `crc/cli/vm_ops.py:9` resolves unchanged through `crc/aws/vm/__init__.py`.
   - `tests/test_aws_vm.py:12` and `tests/test_aws_vm_parity.py:22` updated only their `from crc.aws.vm_cleaner import ...` line to `from crc.aws.vm.cleaner import ...` (plus a trailing blank line removed in `tests/test_aws_vm_parity.py`); no test assertions or case tables were modified, and no monkeypatch retargeting was needed.
   - No other caller in `crc/`, `crc.py`, or `tests/` imported `crc.aws.vm_cleaner`, `crc.aws.vm_api`, or `crc.aws.vm_scan`.
   - All five hash-locked safety test files (`safety_lock.json`) and `tests/legacy/**` (including `tests/legacy/aws_vm.txt`) are untouched.
3. **READMEs and ARCH-002:**
   - `crc/aws/vm/README.md` has all four `ARCH-002` sections (`## Purpose`, `## Public API`, `## Safety Invariants`, `## Extension Rules`) and its 24 backticked names under `## Public API` match `crc/aws/vm/__init__.py` `__all__` and the public top-level definitions across `crc/aws/vm/*.py`.
   - `crc/aws/README.md` edits only the AWS VM lines in `## Purpose`, `## Public API`, and `## Safety Invariants` to point to `crc/aws/vm/README.md`, leaving all other module sections untouched.
4. **Lane rules and forbidden files:**
   - `docs/refactor/BUGS.md`, `docs/refactor/STATUS.md`, `docs/refactor/FILTER_VARIANTS.md`, `crc/README.md`, `tests/README.md`, `tests/legacy/**`, `crc.py`, `crc/cli/**`, `crc/core/**`, `pyproject.toml`, `.github/CODEOWNERS` guardrail files, and all other cleaner modules are untouched.

### Findings

- **BLOCKING:** none.
- **NIT (left):** `Clock` (`crc/aws/vm/adapter.py:42`) and `Decision` (`crc/aws/vm/cleaner.py:44`) are module-level type aliases not re-exported in `crc/aws/vm/__init__.py` (matching pre-move `crc/aws/README.md`, which did not list them under `## Public API`).
- **NIT (left):** `tests/archtest/legacy_baseline.txt` still lists `crc/aws/vm.py` (already removed from `pyproject.toml` in AWS-3; `legacy_baseline.txt` is an owner-only guardrail file).

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed! |
| `mypy` (`crc`, `tests`) | Success: no issues found in 197 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 42213 passed |

Test count: 42213 passed on base (`d109ee5`), 42213 passed on `HEAD` (+0, unchanged).

VERDICT: APPROVE
