# Review ST-AWS-VPC

## Coding summary

Rung ST-AWS-VPC (structure): `crc/aws/vpc.py` and `crc/aws/vpc_api.py` converted into the subpackage `crc/aws/vpc/`, pure move, no behaviour change.

- **Moves (`git mv`).** `crc/aws/vpc.py` -> `crc/aws/vpc/cleaner.py` (393 lines, unchanged except the import line), `crc/aws/vpc_api.py` -> `crc/aws/vpc/client.py` (unchanged). New `crc/aws/vpc/__init__.py` re-exports every public name (`VPC`, `VpcCleaner`, `VpcRuntime`, `build_vpc_cleaner` and all Protocols), so `from crc.aws.vpc import ...` in `crc.py`, `crc/cli/resource_ops.py` and the tests works unchanged. New `crc/aws/vpc/README.md` with the four ARCH-002 sections; the VPC section of `crc/aws/README.md` is trimmed to a pointer.
- **Import sites.** Only the internal import `crc.aws.vpc_api` -> `crc.aws.vpc.client` in `cleaner.py` changed. No other file imported `crc.aws.vpc_api`; no test import line changed; no shim module needed (none of the five hash-locked tests imports the VPC module).
- **monkeypatch targets.** None retargeted: the VPC tests patch `boto3.client`, `boto3.resource`, `boto3.session.Session` and `crc.service.init_logging`, all still looked up where they were.
- **Tests.** Before: 42213 passed. After: 42213 passed (same). `make check` steps (ruff, mypy, lint-imports, pytest incl. archtests) green.
- **Open issues.** `tests/archtest/legacy_baseline.txt` still lists `crc/aws/vpc.py` (stale since AWS-1, guardrail file, not edited; it only ever shrinks). `docs/refactor/FILTER_VARIANTS.md` and `crc/README.md` mention `crc/aws/vpc.py` / `vpc_api.py` paths (not edited; to update: `crc/aws/vpc/cleaner.py`, `crc/aws/vpc/client.py`). `docs/refactor/bugs/pending/AWS-1.md` / `BUGS.md` main file:line refs are of `main` and stay valid.
- **Bugs.** None new: `docs/refactor/bugs/pending/ST-AWS-VPC.md`.

## Round 1 (Argon)

Scope reviewed: `git diff -M d109ee5..HEAD` (`crc/aws/README.md`, `crc/aws/vpc/README.md`, `crc/aws/vpc/__init__.py`, `crc/aws/vpc/cleaner.py`, `crc/aws/vpc/client.py`, `docs/refactor/bugs/pending/ST-AWS-VPC.md`, `docs/refactor/reviews/ST-AWS-VPC.md`) against `AGENTS.md` and `.cursor/skills/crc-python-refactor/REVIEW_CHECKLIST.md`.

### Verification

1. **Pure move (`git diff -M d109ee5..HEAD`):**
   - `crc/aws/vpc.py` -> `crc/aws/vpc/cleaner.py` (99% similarity, 393 lines): only line 21 changed (`from crc.aws.vpc_api import Ec2Client, Ec2Resource, Vpc` -> `from crc.aws.vpc.client import Ec2Client, Ec2Resource, Vpc`). Zero logic changes.
   - `crc/aws/vpc_api.py` -> `crc/aws/vpc/client.py` (100% similarity, 184 lines): zero changes.
   - `crc/aws/vpc/__init__.py` (48 lines): docstring, re-exports of all 4 public definitions from `cleaner.py` (`VPC`, `VpcCleaner`, `VpcRuntime`, `build_vpc_cleaner`) and all 14 `Protocol`s from `client.py`, plus `__all__`. Importing `crc.aws.vpc` imports `crc.aws.vpc.cleaner`, so `@register("aws", "vpc")` still runs on package import.
2. **Import resolution and test invariance:**
   - Every caller import (`from crc.aws.vpc import VPC` in `crc.py`, `crc/cli/resource_ops.py`, and `tests/legacy/crc_main.txt`; `from crc.aws.vpc import VpcCleaner` in `tests/test_aws_vpc.py`; `from crc.aws.vpc import VPC, VpcCleaner, VpcRuntime, build_vpc_cleaner` in `tests/test_aws_vpc_parity.py`) resolves unchanged via `crc/aws/vpc/__init__.py`.
   - No caller or test in the repository imported `crc.aws.vpc_api`; the five hash-locked safety test files (`SAF-LOCK`) and `tests/legacy/**` are untouched; no test files needed edits or monkeypatch retargets (`tests/test_aws_vpc_parity.py` patches `boto3.client`, `boto3.resource`, `boto3.session.Session`, and `crc.service.init_logging`).
3. **READMEs and ARCH-002 sync:**
   - `crc/aws/vpc/README.md` contains all four required `ARCH-002` sections (`## Purpose`, `## Public API`, `## Safety Invariants`, `## Extension Rules`) and syncs all 18 exported public names.
   - `crc/aws/README.md` touches only the VPC entries and adds `### vpc`, without rewriting any other module's section.
4. **Lane and guardrail compliance:**
   - `docs/refactor/BUGS.md`, `docs/refactor/STATUS.md`, `docs/refactor/FILTER_VARIANTS.md`, `crc/README.md`, `tests/README.md`, `tests/legacy/**`, `crc.py`, `crc/cli/**`, `crc/core/**`, `pyproject.toml`, `.github/CODEOWNERS` guardrail files, and all other modules are untouched.

### BLOCKING (fixed)

None.

### NIT (left)

- `crc.aws.vpc_api` is not shimmed (moved to `crc.aws.vpc.client`), and module-level type aliases / private helpers (`TagSpec`, `ClientFactory`, `ResourceFactory`, `RegionLister`, `_boto3_client`, `_boto3_resource`, `_all_regions`) now live on `crc.aws.vpc.cleaner` rather than directly on `crc.aws.vpc`; no caller or test in the repository imports `crc.aws.vpc_api` or accesses those attributes on `crc.aws.vpc`.
- Shared docs (`docs/refactor/FILTER_VARIANTS.md`, `crc/README.md`) still mention `crc/aws/vpc.py` / `vpc_api.py` (outside lane scope; noted in the coding summary for integration).

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` (`crc`, `tests`) | Success: no issues found in 197 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 42213 passed |

Test count: 42213 before ST-AWS-VPC (`d109ee5`), 42213 after (+0, unchanged).

VERDICT: APPROVE
