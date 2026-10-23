## Coding summary

- Bugs fixed: BUG-017, BUG-018 (`crc/cli/dispatch.py`, new `validate_targets` called first in `run_dispatch`).
  - BUG-017: every (cloud, resource) pair is checked before the first cleaner. An unsupported pair (`keypair`/`kms` off AWS, `nic` off Azure, `ip` on OCI) with an explicit cloud raises `ValueError` (same message as the `CRC` method) before anything runs; under `--cloud all` it is skipped with a WARNING and a `RUN START`/`SKIPPED reason=unsupported_cloud_resource`/`RESULT` log triple, and no `CRC` method is called for it.
  - BUG-018: `--cloud all --resource disk|all` can never complete (AWS EBS is opt-in for `--cloud aws --resource disk` only), so it now raises the existing opt-in `ValueError` before any `CRC` is built or cleaner runs. It is not made to run. `--cloud aws --resource all` already fails in `check_flag_combinations` before any cleaner (unchanged). The breaker in `_disk` stays as defence in depth.
- Bugs left: none.
- Files changed: `crc/cli/dispatch.py`, `crc/cli/README.md`, `tests/test_cli_main_parity.py`, `tests/test_core_selection.py` (cases that trigger the bugs are derived from what the oracle did, marked BUG-017/BUG-018, and assert the exact new outcome; all other cases still equal the oracle; plus a test that both markers occur and differ from the oracle), new `tests/test_cli_dispatch_fix.py`, this file.
- Tests (`pytest -q`): 42444 collected at 182466d, 42476 after (+32: 40 new tests in `tests/test_cli_dispatch_fix.py` and one parity check, minus parametrised skips removed). `tests/test_core_selection.py` (the `crc.core.selection` model compared against `main()`) also changed: its three comparison tests now expect the BUG-017 outcome for unsupported pairs (explicit cloud raises with nothing reached, `--cloud all` skips with the warning); every other pair is still compared unchanged.
- Owner actions: none (no locked test or `CLEANUP_SAFETY.md` change needed).

## Notes

- Production Jenkins commands: none reach this code with `--cloud all` or an unsupported pair, so no production command changes.
- On the new up-front errors `main()` has already run `set_max_age`, so `MAX_AGE` stays set and "MAX_AGE reset." is not printed, as for every other error after that point.
- The pair table lives in `dispatch.SUPPORTED_CLOUDS`; it mirrors the cloud guards inside `ResourceOps` (`delete_keypairs`, `delete_nic`, `delete_kms`, `_get_ip`).

## New bugs

- `crc/cli/dispatch.py` `_snapshot` ignores the cloud: `--cloud all --resource snapshot` runs the AWS snapshot cleanup once per cloud (4 times), and `delete_vpc` builds the AWS VPC cleaner for every cloud. Exists on main: yes (`crc.py` snapshot branch and `delete_vpc`, same shape). Not fixed.

## Owner decision

- `crc/core/selection.py` (`build_selection`) still models `main` and returns unsupported pairs (for example `azure`+`keypair`) as selected. It is outside this rung's files, so it is unchanged; FIX-CLI-ROUTE or a later rung should make it agree with `dispatch.validate_targets`. Its test now documents the BUG-017 difference.

## Round 1 (Argon)

Reviewed `git diff 182466d..HEAD` against the `FIX-CLI-ALL` task, `.cursor/skills/crc-python-refactor/BEHAVIOUR_FIX.md` and the wave `FIX-1` overrides.

### Findings

- **BLOCKING (fixed):** `crc/cli/dispatch.py:251` called `crc = make_crc(context, cloud)` at the top of `for cloud in targets.clouds:`, before checking `if (cloud, resource) in skipped:`. Because `CRCBase.__init__` (`crc/cli/base.py:50-51`) raises `ValueError("project_id is mandatory Parameter for GCP")` when `cloud == "gcp"` and `project_id` is unset, running `--cloud all --resource keypair`, `--cloud all --resource nic --resource_group <rg>` or `--cloud all --resource kms --kms_key_description <d> --kms_user <u>` without `--project_id` still deleted on the supported cloud (`aws` or `azure`) and then raised `ValueError` on the skipped `gcp` iteration. Moved `make_crc(context, cloud)` after the `if (cloud, resource) in skipped:` branch so `CRC` is only constructed for clouds with a non-skipped resource (`crc/cli/dispatch.py:251-259`), updated `tests/test_cli_main_parity.py:589-594`, and added `test_bug_017_cloud_all_real_crc_does_not_build_skipped_clouds` plus `SKIPPED ... reason=unsupported_cloud_resource count=1` log assertions in `tests/test_cli_dispatch_fix.py:100-149`.
- **New bug noted (not fixed):** Under `--cloud all` for resources where `gcp` is supported (`vm`, `ip`, `disk`), `CRCBase.__init__` (`crc/cli/base.py:50-51`, `main:crc.py:87-88`) checks `if cloud == "gcp" and not project_id:` when `make_crc(context, "gcp")` runs in the loop, so omitting `--project_id` raises `ValueError` after `aws` and `azure` already ran (the `run_dispatch` counterpart of `BUG-343`). Exists on `main`: yes.

### Verification

1. **Bug fixes (`BUG-017`, `BUG-018`):**
   - `BUG-017`: `validate_targets` checks every `(cloud, resource)` pair before the loop. Explicit unsupported pairs (`keypair`/`kms` off `aws`, `nic` off `azure`, `ip` on `oci`) raise the exact `ResourceOps` `ValueError` before `make_crc` or any cleaner runs; under `--cloud all`, unsupported pairs are skipped with `_LOG.warning("%s is not supported on %s; skipped under --cloud all", resource, cloud)` and a `RUN START` / `SKIPPED cloud=<c> resource=<r> reason=unsupported_cloud_resource count=1` / `RESULT ... skipped=1` triple without constructing `CRC` or calling any cleaner for the skipped cloud.
   - `BUG-018`: `--cloud all --resource disk` and `--cloud all --resource all` raise `ValueError(AWS_DISK_OPT_IN_MESSAGE)` in `validate_targets` before any `CRC` is built or any cleaner runs; `_disk` retains the breaker as defence in depth.
   - `tests/test_cli_dispatch_fix.py` fails on `182466d` and passes on `HEAD`.
2. **Direction rule & parity (`tests/test_cli_main_parity.py`, `tests/test_core_selection.py`, `tests/legacy/crc_main.txt`):**
   - Nothing is deleted, stopped or released that was kept before; fixes only fail closed earlier or skip unsupported `--cloud all` pairs.
   - `tests/legacy/crc_main.txt` is untouched. `diverging_outcome` in `tests/test_cli_main_parity.py` derives `BUG-017` and `BUG-018` triggers from the oracle outcome and asserts the exact new `Outcome`; all other cases assert exact equality with the oracle, and `test_diverging_cases_exist_and_differ_from_the_oracle` verifies both bug IDs trigger and differ from the oracle.
3. **Production commands & guardrails:**
   - No production Jenkins command uses `--cloud all` or an unsupported `(cloud, resource)` pair; all supported explicit pairs run unchanged.
   - No locked safety test, `tests/archtest/safety_lock.json`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md` or `CLEANUP_SAFETY.md` was edited.
   - `crc/cli/README.md` `## Public API` and `## Safety Invariants` are updated and pass `ARCH-002`.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt`, then `make check`:
- `ruff check .`: All checks passed!
- `mypy`: Success: no issues found in 219 source files
- `lint-imports`: Contracts: 5 kept, 0 broken
- `pytest -q`: 42479 passed (up from 42444 on `182466d`, +35)

VERDICT: APPROVE

