# AG-ENV review

## Coding summary

Lane AG-ENV (branch `ag/env`): reproducible green gate, offline smoke, the last ARCH-003 loophole.

**Routed / adapters.** No kind was routed or unrouted and no adapter was deleted or shimmed; the
CLI parity tests reach the cleaners exactly as before.

**1. Reproducible gate.**
- `pyproject.toml`: mypy overrides with `ignore_missing_imports` for `google.*`, `azure.*`,
  `msrest*`, `msrestazure*` (next to the existing boto3, oci and googleapiclient ones), so a release
  without `py.typed` cannot break `make lint`. `follow_imports = "skip"` was tried and rejected:
  it turns the SDK types into `Any` and makes existing `type: ignore` comments in
  `tests/test_gcp_base.py` fail (`no-any-return`), and those files belong to other lanes.
- `constraints.txt`: `pip freeze` of a fresh Python 3.11.17 venv built from `requirements.txt` and
  `requirements-dev.txt` on 2026-10-24 (`make check` green in that venv: 44415 tests before my
  change). CI (`.github/workflows/ci.yml`, also the pip cache key) and `.cursor/environment.json`
  install with `-c constraints.txt`.
- `Makefile`: new `smoke-offline` target.

**2. `make smoke-offline`** (`scripts/smoke_offline.py`, `scripts/offline_hook/sitecustomize.py`,
`tests/test_smoke_offline.py`). One `python crc.py ... --dry_run` subprocess per (cloud, kind) of
`tests/fixtures/jenkins_commands.txt` (17 pairs, `--scan_tag` lines skipped, `$RESOURCE_GROUP` and
`${AWS_JENKINS_SLAVE}` substituted). The runner puts `scripts/offline_hook` on `PYTHONPATH` and sets
`CRC_OFFLINE_SMOKE=1`; the `sitecustomize` replaces `boto3.client/resource`, the Azure,
GCP (`compute_v1.*Client`, `discovery.build`), OCI, Slack and Influx clients with an in-memory
`Fake` and denies `socket` connects and DNS. Each pair must exit 0 with exactly one `RUN START` and
one `RESULT` line. Tests also pin: no effect without the switch, sockets denied, and no reference
to the hook anywhere under `crc/` or `crc.py` (so no Jenkins flag or variable reaches it). The
subprocess environment is rebuilt from `PATH`, `HOME`, `LANG` plus dummy credentials.

**3. ARCH-003.**
- `crc/core/age.py` no longer imports `os`. It has `set_max_age_source()` and `max_age_override()`;
  `crc/cli/context.py` `install_max_age_source()` (first call of `main`) installs
  `read_max_age_env()`, which reads `MAX_AGE` at each decision, so `--max_age` (exported by
  `set_max_age`) and a `MAX_AGE` set by Jenkins keep working exactly as before. Without a source no
  override applies. The core `RunContext` was left unchanged: cloud cleaners call `is_old` without a
  context and those files belong to other lanes, so an injected source is the only way to keep their
  signatures. `tests/conftest.py` installs the same production function so tests that set `MAX_AGE`
  with `monkeypatch` and call a cleaner without `main` behave as before.
- `tests/archtest/bans.py`: `crc/core` now bans `env`; new kind `clock_ref` (the clock passed as a
  value: default argument, `default_factory=`, attribute, `time.time`) is banned in `crc/core` and
  `crc/cli`, never double-reported for a call. `cloud_clock_refs()` reports the cloud hits only.
  Self-tests replace `core_env_ban_is_deferred_to_wave_b` with the inverse (env is banned in core).

**Test count:** before 44415, after 44461 (floor raised to 44461).

## Owner action

1. `requirements.txt` (not edited by this lane): `paramiko`, `requests` and `beautifulsoup4` are never
   imported (`rg "paramiko|bs4|beautifulsoup|import requests|from requests" --glob '*.py'` finds
   nothing; only `requirements.txt` names them). `requests` stays installed as a dependency of the
   Azure, OCI and Slack SDKs (pinned in `constraints.txt`). Proposed diff:

   ```diff
   -paramiko
   -requests
   -beautifulsoup4
   ```
   then regenerate `constraints.txt` the same way (fresh 3.11 venv, `pip freeze`).
2. `requirements.txt` is not hash-locked in this checkout (plain names, no pins); constraints.txt is
   the lock that matters now.

## Wave next

Docs (AG-DOCS): `README.md:89` and `AGENTS.md:17` install lines need `-c constraints.txt`;
`ARCHITECTURE.md` "One exception: `is_old` reads the `MAX_AGE` environment variable" is now false
(`crc/core` reads no environment; `crc/cli` installs the reader).

Cloud packages: the clock passed as a value (`clock_ref`), reported only (not failing):
`crc/aws/disk/__init__.py:38`, `crc/aws/spot_instance_requests/runtime.py:21`,
`crc/aws/vm/adapter.py:58`, `crc/azu/spot_vm/__init__.py:105`, `crc/azu/vm/adapter.py:40`,
`crc/gcp/spot_vm/adapter.py:51`, `crc/gcp/spot_vm/cleaner.py:165`, `crc/gcp/spot_vm/cleaner.py:188`,
`crc/gcp/spot_vm/disks.py:112`, `crc/gcp/vm_adapter.py:45`, `crc/oci/spot_vm/adapter.py:44`,
`crc/oci/vm/adapter.py:30`. When their owners remove them, add `clock_ref` to the cloud entries of
`PACKAGE_BANS` (`_ALL_KINDS`).

Smoke covers the 17 pairs of the Jenkins fixture only (no `vpc`, `gcp spot_vm`, `oci spot_instances`).

## New bugs

None found.
