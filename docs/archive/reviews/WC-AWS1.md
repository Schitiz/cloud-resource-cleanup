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
