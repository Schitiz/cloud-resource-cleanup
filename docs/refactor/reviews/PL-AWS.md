# Review: PL-AWS

## Coding summary

Rung PL-AWS (plumbing): `crc/aws/_base.py`, `crc/aws/connectivity.py` and `crc/aws/__init__.py` are strict-clean, no behaviour change. Nothing is registered (they are not cleaners).

- **Summary.** `get_all_regions` and `CONNECTIVITY_ERRORS` / `log_skipped_region` keep every call, argument, log line and error path of `main`: one `boto3.client(service, region_name=default)` + `describe_regions()`, the INFO log of the list, and on a `CONNECTIVITY_ERRORS` error only the WARNING plus `boto3.session.Session().get_available_regions(service)` and the INFO "(static)" log; every other error (auth, `NoCredentialsError`, `KeyError` on a malformed response) propagates. Changes are typing only: `List` to `list`, annotated locals so the untyped boto3 results are narrowed to `list[str]`, `CONNECTIVITY_ERRORS: tuple[type[BaseException], ...]`, the import-time docstring of `_base.py` moved to a real module docstring, and the botocore import split so ruff isort passes. `__init__.py` still holds only the copyright comment (no `__all__`, no export list). No `# type: ignore`. All three files are removed from both legacy ratchet lists in `pyproject.toml` (ruff `extend-exclude`: 3 lines; mypy override: `crc.aws`, `crc.aws._base`, `crc.aws.connectivity`); nothing was added.
- **Tests.** Before: 7379 passed. After: 7523 passed (+144): `tests/test_aws_base_parity.py` (40: 38 cases, env set/unset, success, empty, malformed responses, every connectivity error in describe and in client creation, auth/credential/other errors, static fallback empty/tuple/erroring, plus a coverage check), `tests/test_aws_connectivity_parity.py` (98: tuple identity, classification of 16 exceptions, 80 log cases compared on records, args and stdout, plus a split check), `tests/test_aws_base.py` (3) and `tests/test_aws_connectivity.py` (3). Oracles `tests/legacy/aws_base.txt` and `tests/legacy/aws_connectivity.txt` are byte-identical to `git show main:<path>`; the base parity test swaps in the connectivity oracle while the base oracle runs. Non-vacuity proven: changing the "(static)" log text fails 19 cases, removing `ConnectionClosedError` from the tuple fails 7, changing the skipped-region log text fails 80; all reverted. `make check` equivalent (ruff, mypy strict on 166 files, import-linter, pytest incl. archtests) is green.
- **Open issues.** None for the code. 4 quirks are in `docs/refactor/bugs/pending/PL-AWS.md` (static fallback lists regions the account has not enabled and has no retry; `SSLError` counts as a connectivity error; unchecked response indexing). BUG-227 (vm scan static list) is related and untouched.
- **Core changes needed.** None.
- **`crc/README.md` / `tests/README.md` / `tests/legacy/README.md` (not edited).** `tests/legacy/README.md` should list `aws_base.txt` (exact `git show main:crc/aws/_base.py`, run by `tests/test_aws_base_parity.py`) and `aws_connectivity.txt` (exact `git show main:crc/aws/connectivity.py`, run by `tests/test_aws_connectivity_parity.py`); `tests/README.md` should list `test_aws_base_parity.py`, `test_aws_base.py`, `test_aws_connectivity_parity.py` and `test_aws_connectivity.py`; `crc/README.md` should no longer call `crc/aws/_base.py`, `connectivity.py` and `__init__.py` legacy.

## Round 1 (Argon)

Scope reviewed: `git diff ef1f718..HEAD` (`crc/aws/_base.py`, `crc/aws/connectivity.py`, `crc/aws/__init__.py`, `crc/aws/README.md`, `pyproject.toml`, `docs/refactor/bugs/pending/PL-AWS.md`, `docs/refactor/reviews/PL-AWS.md`, `tests/legacy/aws_base.txt`, `tests/legacy/aws_connectivity.txt`, `tests/test_aws_base.py`, `tests/test_aws_base_parity.py`, `tests/test_aws_connectivity.py`, `tests/test_aws_connectivity_parity.py`) against `git show main:crc/aws/_base.py`, `git show main:crc/aws/connectivity.py`, `git show main:crc/aws/__init__.py`, `AGENTS.md`, `docs/refactor/BUGS.md`, and `.cursor/skills/crc-python-refactor/REVIEW_CHECKLIST.md`.

### 1. Behaviour parity (`git show main:<path>`)

- `crc/aws/_base.py` (`crc/aws/_base.py:14-42` vs `main:crc/aws/_base.py:15-43`):
  - `get_all_regions(service_name: str, default_region_name: str) -> list[str]` keeps the exact signature, `boto3.client(service_name, region_name=default_region_name)` call, `[region["RegionName"] for region in client.describe_regions()["Regions"]]` comprehension, `logging.info(f"Retrieved list of regions: {regions}")` log line, `except CONNECTIVITY_ERRORS as e:` clause, `logging.warning("describe_regions failed for %s via %s (%s); using boto3 static region list", service_name, default_region_name, type(e).__name__)` log line, `boto3.session.Session().get_available_regions(service_name)` fallback, and `logging.info(f"Retrieved list of regions (static): {static_regions}")` log line.
  - Non-connectivity errors (`ClientError` such as `AuthFailure`, `NoCredentialsError`, `KeyError`, `TypeError`) propagate without fallback (SAF-001, SAF-004).
- `crc/aws/connectivity.py` (`crc/aws/connectivity.py:10-32` vs `main:crc/aws/connectivity.py:10-31`):
  - `CONNECTIVITY_ERRORS: tuple[type[BaseException], ...] = (BotoConnectionError, ReadTimeoutError, ConnectionClosedError)` keeps the exact tuple elements and order.
  - `log_skipped_region(region: str, context: str, exc: BaseException) -> None` keeps the exact signature and `logging.warning("Region %s: skipped %s — network/connectivity (%s): %s", region, context, type(exc).__name__, exc)` call.
- `crc/aws/__init__.py` (`crc/aws/__init__.py:1` vs `main:crc/aws/__init__.py:1`): byte-identical (`# Copyright (c) Yugabyte, Inc.`).
- Every symbol callers import (`get_all_regions`, `CONNECTIVITY_ERRORS`, `log_skipped_region`) works with the same signature and types.

### 2. Oracles and parity tests

- `diff -u <(git show main:crc/aws/_base.py) tests/legacy/aws_base.txt` and `diff -u <(git show main:crc/aws/connectivity.py) tests/legacy/aws_connectivity.txt` are both empty (byte-identical).
- Verified non-vacuous parity by mutating the static-fallback log line in `crc/aws/_base.py:41` and removing `ConnectionClosedError` from `CONNECTIVITY_ERRORS` in `crc/aws/connectivity.py:22`: 22 parity tests failed immediately across `tests/test_aws_base_parity.py` and `tests/test_aws_connectivity_parity.py`; reverted both changes.

### 3. Typing, lint, scope, and pending bugs

- `crc/aws/__init__.py`, `crc/aws/_base.py`, and `crc/aws/connectivity.py` (`crc.aws`, `crc.aws._base`, `crc.aws.connectivity`) were removed from both ratchet lists in `pyproject.toml` (`pyproject.toml:24-43`, `:67-86`) with nothing added; `mypy` strict and `ruff check .` pass with zero `# type: ignore` or `# noqa` comments in the refactored modules and their tests.
- `crc.py`, `crc/core/**`, all cleaners, and all files forbidden by the lane rules are untouched; `crc/aws/README.md` edits only the sections describing `_base.py`, `connectivity.py`, and `__init__.py` and passes `ARCH-002` symbol sync.
- Verified every row in `docs/refactor/bugs/pending/PL-AWS.md` against `git show main:crc/aws/_base.py` and `git show main:crc/aws/connectivity.py`.

### Findings

- **BLOCKING (fixed): `SSLError` quirk in `docs/refactor/bugs/pending/PL-AWS.md` was not covered by a parity test (`tests/test_aws_base_parity.py:44-52`, `tests/test_aws_connectivity_parity.py:31-51`, `:113-119`, `docs/refactor/bugs/pending/PL-AWS.md:9`).**
  `docs/refactor/BUGS.md` rule 2 requires every recorded quirk to be covered by a test, and row 3 of `docs/refactor/bugs/pending/PL-AWS.md` documents `botocore.exceptions.SSLError` being classified as a connectivity error via `BotoConnectionError`, yet neither `tests/test_aws_connectivity_parity.py` nor `tests/test_aws_base_parity.py` included `SSLError`, and `tests/test_aws_base_parity.py:_run` only compared `stdout` (`capsys.readouterr().out`) without `stderr`. Added `"ssl"` (`SSLError`) to `EXCEPTIONS` and `test_connectivity_split_is_not_vacuous` in `tests/test_aws_connectivity_parity.py` and to `conn_errors()` and `test_cases_cover_both_paths_and_errors` in `tests/test_aws_base_parity.py`, added `stderr` comparison to `tests/test_aws_base_parity.py:201-210`, added a `no-describe-regions-method` parity case (`tests/test_aws_base_parity.py:95-99`) plus its corresponding `NEW` low-risk `cosmetic` row in `docs/refactor/bugs/pending/PL-AWS.md:11` (`main:crc/aws/_base.py:15-30`, `:40-41`: `get_all_regions` docstring names `'s3'` alongside `'ec2'`, but `client.describe_regions()` is EC2-only and raises `AttributeError` on non-EC2 clients), and cited the `ssl` test cases in row 3 of `docs/refactor/bugs/pending/PL-AWS.md`.
- **NIT (left): None.**

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` (`crc`, `tests`) | Success: no issues found in 166 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 7533 passed |

Test count: 7379 before PL-AWS (`ef1f718`), 7523 before review, 7533 after review additions (+154).

VERDICT: APPROVE
