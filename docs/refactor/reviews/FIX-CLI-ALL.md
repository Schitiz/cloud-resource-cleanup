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
