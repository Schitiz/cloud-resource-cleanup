# Review ST-AWS-VPC

## Coding summary

Rung ST-AWS-VPC (structure): `crc/aws/vpc.py` and `crc/aws/vpc_api.py` converted into the subpackage `crc/aws/vpc/`, pure move, no behaviour change.

- **Moves (`git mv`).** `crc/aws/vpc.py` -> `crc/aws/vpc/cleaner.py` (393 lines, unchanged except the import line), `crc/aws/vpc_api.py` -> `crc/aws/vpc/client.py` (unchanged). New `crc/aws/vpc/__init__.py` re-exports every public name (`VPC`, `VpcCleaner`, `VpcRuntime`, `build_vpc_cleaner` and all Protocols), so `from crc.aws.vpc import ...` in `crc.py`, `crc/cli/resource_ops.py` and the tests works unchanged. New `crc/aws/vpc/README.md` with the four ARCH-002 sections; the VPC section of `crc/aws/README.md` is trimmed to a pointer.
- **Import sites.** Only the internal import `crc.aws.vpc_api` -> `crc.aws.vpc.client` in `cleaner.py` changed. No other file imported `crc.aws.vpc_api`; no test import line changed; no shim module needed (none of the five hash-locked tests imports the VPC module).
- **monkeypatch targets.** None retargeted: the VPC tests patch `boto3.client`, `boto3.resource`, `boto3.session.Session` and `crc.service.init_logging`, all still looked up where they were.
- **Tests.** Before: 42213 passed. After: 42213 passed (same). `make check` steps (ruff, mypy, lint-imports, pytest incl. archtests) green.
- **Open issues.** `tests/archtest/legacy_baseline.txt` still lists `crc/aws/vpc.py` (stale since AWS-1, guardrail file, not edited; it only ever shrinks). `docs/refactor/FILTER_VARIANTS.md` and `crc/README.md` mention `crc/aws/vpc.py` / `vpc_api.py` paths (not edited; to update: `crc/aws/vpc/cleaner.py`, `crc/aws/vpc/client.py`). `docs/refactor/bugs/pending/AWS-1.md` / `BUGS.md` main file:line refs are of `main` and stay valid.
- **Bugs.** None new: `docs/refactor/bugs/pending/ST-AWS-VPC.md`.
