## Coding summary

Lane WC-AWS1: delete the dead adapter classes `ElasticIPs` and `Kms`.

- Routed: nothing new in this lane. `aws` / `ip` and `aws` / `kms` were already run by `crc/cli/bridge.py` through the registered Cleaners; no production code used the adapters (`git grep` of the class and module path found only the package re-export, the adapters' own docstrings, tests, `tests/helpers_cl2_crc.py` / `tests/test_cli_bridge_aws.py` / `tests/test_core_engine.py` name strings and `tests/legacy/*`).
- Deleted: `crc/aws/elastic_ips/adapter.py` (`ElasticIPs`) and `crc/aws/kms/adapter.py` (`Kms`), their package re-exports and their README Public API lines; the `crc/aws/README.md` lines for both kinds were trimmed (no rung names, no adapter wording). Both package READMEs were rewritten to describe only the current code. `ElasticIpRuntime` and `KmsRuntime` stay exported (still injectable); they have no production caller now.
- Not touched: the five adapters the hash-locked safety tests build, those tests, `tests/legacy/*`, `docs/refactor/BUGS.md`, `CLEANUP_SAFETY.md`.
- Tests retargeted to drive the Cleaner through `crc.core.engine.run` (new helper `tests/helpers_wc_aws1_engine.py`):
  - `tests/test_aws_ip_parity.py` and `tests/test_aws_kms_parity.py`: every oracle case (`tests/legacy/aws_elastic_ips.txt`, `aws_kms.txt`) now runs the engine path against the same oracle (calls, results, errors, stdout, log lines), quirks and skip-decision cases included. The adapter-vs-oracle `test_matches_main` tests are gone; they are replaced by `test_engine_dry_run_never_releases` / `test_engine_dry_run_never_schedules` per case so the test count does not drop. BUG-011 (IP) outcomes are asserted exactly for the engine path (`ENGINE_FIXED`) next to the main-with-fix outcomes (`FIXED_MAIN`); KMS fixed cases keep `assert_fixed` plus a new log check of the fixed outcome (`_assert_fixed_logs`).
  - Constructor-only cases are ported to Cleaner options: `_should_skip_instance` / `_should_skip_kms` become `ElasticIpCleaner.should_skip` / `KmsCleaner.should_skip` built by the registry factory from `RunContext.options`; the KMS "accumulates over two `delete()` calls" case now asserts that two engine runs repeat the same SDK calls and lines and that the oracle's accumulated list is `["k1","k2","k1","k2"]`.
  - `tests/test_aws_elastic_ips.py`, `_fix.py`, `tests/test_aws_kms.py`, `_fix.py` and the Elastic IP and KMS parts of `tests/test_aws_misc_logger.py` use the engine too.
- Allowed behaviour change (not recorded here, the wave owner adds the single BUGS.md and CLEANUP_SAFETY.md rows): the Elastic IP cleaner lists every region before it releases; a listing error in a later region now stops the run before any release.
- CLI parity tests: untouched in this lane (they do not reach these adapters).
- Test count: 44415 before, 44415 after (floor 44415, ARCH-008 green). `make check` green.
- Owner actions: none. If the wave adds the BUGS.md row, the README sentence "`plan()` lists every region before `apply()` releases" in `crc/aws/elastic_ips/README.md` and `crc/aws/README.md` can cite its ID.

## New bugs

None found.

## Left over

- `tests/helpers_cl2_crc.py`, `tests/test_cli_bridge_aws.py`, `tests/test_core_engine.py` still mention the names `ElasticIPs` / `Kms` as strings (oracle class names of the legacy CLI); outside this lane's files.
- `ElasticIpRuntime` / `KmsRuntime` and `ElasticIpCleaner.plan_region` / `KmsCleaner.connect_and_list`, `plan_keys`, `schedule` were public for the adapters; they are still used by tests and the cleaners, so they stay.

## Round 1 (Argon)

### Findings & fixes made in review

1. **Removed dead adapter runtime dataclasses (`ElasticIpRuntime` and `KmsRuntime`)** (`crc/aws/elastic_ips/client.py`, `crc/aws/elastic_ips/__init__.py`, `crc/aws/elastic_ips/README.md`, `crc/aws/kms/client.py`, `crc/aws/kms/__init__.py`, `crc/aws/kms/README.md`):
   - `ElasticIpRuntime` and `KmsRuntime` were only used by the deleted `ElasticIPs` and `Kms` adapters (neither `ElasticIpCleaner`, `KmsCleaner`, nor any test imported or used them). Removed both classes, their package re-exports, and their `Public API` lines (matching `ENG-0`'s removal of `KeyPairRuntime` when `KeyPairs` was deleted).
2. **Tightened error-case call and log parity in `test_aws_ip_parity.py`** (`tests/test_aws_ip_parity.py`):
   - `test_cleaner_protocol_matches_main` now also asserts `describe_addresses` calls, `new.logs == old.logs[:-1]`, and (for single-region cases) `_without_client(new.calls) == _without_client(old.calls)` on error and `fails_in_plan` cases.

### Checklist verification

- **Check (1) Production paths intact**: `crc/cli/scan.py`, `crc/cli/routes/aws.py`, `build_elastic_ip_cleaner` (`aws` / `ip`), `build_kms_cleaner` (`aws` / `kms`), and the 5 adapters used by the hash-locked safety tests (`crc.aws.disk.Disk`, `crc.aws.spot_instance_requests.SpotInstanceRequests`, `crc.azu.spot_instances.SpotVM`, `crc.gcp.spot_instances.SpotVM`, `crc.oci.spot_instances.SpotVM`) are untouched and importable.
- **Check (2) Module parity tests drive the registered Cleaner through `crc.core.engine.run`**: `tests/test_aws_ip_parity.py` and `tests/test_aws_kms_parity.py` (plus `tests/test_aws_elastic_ips.py`, `tests/test_aws_elastic_ips_fix.py`, `tests/test_aws_kms.py`, `tests/test_aws_kms_fix.py`, and `tests/test_aws_misc_logger.py`) drive `ElasticIpCleaner` and `KmsCleaner` through `crc.core.engine.run` against `tests/legacy/aws_elastic_ips.txt` and `tests/legacy/aws_kms.txt` with all oracle cases, quirks, skip-decision checks, and `BUG-NNN` divergences (`BUG-011`, `BUG-004`, `BUG-007`, `BUG-008`, `BUG-014`, `BUG-055`, `BUG-357`) preserved. Locally breaking `ElasticIpCleaner.plan_region` and `KmsCleaner._select_key` caused 100 test failures across `test_aws_ip_parity.py` and `test_aws_kms_parity.py` (reverted after verification).
- **Check (3) Deleted names gone & READMEs trimmed**: `crc/aws/elastic_ips/adapter.py` (`ElasticIPs`), `ElasticIpRuntime`, `crc/aws/kms/adapter.py` (`Kms`), and `KmsRuntime` are deleted and unreferenced across `crc/`, `crc.py`, and `tests/` (only oracle string names in `tests/helpers_cl2_crc.py`, `tests/test_cli_bridge_aws.py`, `tests/test_core_engine.py`, and `tests/legacy/*` remain). `crc/aws/elastic_ips/README.md`, `crc/aws/kms/README.md`, and the `elastic_ips` / `kms` lines of `crc/aws/README.md` describe only the current code with no rung, refactor, legacy-path, or adapter wording and no links to moved docs.
- **Check (4) Locked files untouched**: No hash-locked safety test, `tests/legacy/*.txt` oracle, or `tests/archtest/**` file was touched.
- **Check (5) Size limits & Public API sync**: All touched files in `crc/` are well under 250 lines (max 209 lines in `crc/aws/kms/cleaner.py`) and all functions are at most 60 lines (`ARCH-004`). `Public API` sections in `crc/aws/elastic_ips/README.md` and `crc/aws/kms/README.md` are in sync with `__all__` and module exports (`ARCH-002`).
- **Check (6) Gates & test count**: After `pip install -r requirements.txt -r requirements-dev.txt`, `make check` is green:
  - `ruff check .`: passed
  - `mypy`: passed (`Success: no issues found in 371 source files`)
  - `lint-imports`: 5 contracts kept, 0 broken
  - `pytest -q -n auto`: **44415 passed in 55.62s**
  - `ARCH-008`: 44415 tests, floor 44415 (`ARCH-001..011` and `SAF-LOCK` green)

## New bugs

None found.

VERDICT: APPROVE
