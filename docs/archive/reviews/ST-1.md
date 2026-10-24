# ST-1 review

## Coding summary

Stricter Python style, no behaviour change. Branch `st/1`, `make check` green (44,571 passed,
1 skipped; ARCH-008 floor 44,572 before and after, no test added or removed).

- Routing / adapters: out of scope for this lane. `main` already runs every pair through
  `crc.core.engine` via `crc/cli/bridge.py`; this lane routed, deleted and shimmed nothing, and the
  CLI parity tests are untouched (they still reach the cleaners through the bridge seams).
  No `tests/test_<name>_engine.py` copy was needed.
- Commits: (1) `[tool.ruff.format]` config, skipping `*.md` (ruff would otherwise rewrite code
  blocks in `ARCHITECTURE.md`); (2) `ruff format` of the repo, formatting only (19 files, AST of the
  locked tests unchanged, SAF-LOCK green); (3) the rule set, fixes and noqa.
- `pyproject.toml`: select adds `DTZ BLE G LOG C4 RET N`; global ignore only `LOG015` (root logger,
  parity tests compare logger names). `make lint` and CI run `ruff format --check .`.
  `AGENTS.md` gains the rule-set line and the `# noqa: BLE001 - <reason>` convention.
- `G004`/`G003`: 117 f-string logging calls became `%s`/`%r` arguments (scripted from the AST, no
  format specs involved). One mixed call in `crc/azu/spot_vm/disks.py` (an f-string that already
  carried `%s`) was rewritten by hand to keep the argument order. The one `G003` in
  `crc/azu/disk/cleaner.py` keeps the `+` concatenation with `noqa`, because `%s` would turn the
  BUG-174 `TypeError` for a `None` name into a logged "None" (`test_azure_disk_parity` caught it).
- `tests/test_aws_base_parity.py` compared `record.msg` and `record.args` with the frozen oracle
  (which uses f-strings); it now compares level and rendered message (`getMessage()`), the log text.
- Tests: `N811` alias `NewCRC` -> `NEW_CRC` (6 files), `_Built` -> `_BuiltError`, `routed_Check` ->
  `routed_check`, two `dict.fromkeys` (C420). Nothing else renamed.

### Counts per rule (`ruff check --select <rule>`, LOG015 ignored, whole repo)

| Rule | Before crc | Before tests | After |
|------|-----------:|-------------:|------:|
| DTZ  | 3   | 49  | 0 (3 + 45 noqa, 4 sites in locked tests ignored per file) |
| BLE  | 68  | 83  | 0 (151 noqa) |
| G    | 118 (117 G004, 1 G003) | 0 | 0 (1 noqa) |
| C4   | 0   | 4   | 0 (2 fixed, 2 in locked tests ignored per file) |
| RET  | 0   | 0   | 0 |
| N    | 37  | 121 | 0 (N802/N803 per-file ignores, N811/N818/N806 fixed) |
| LOG  | 0 (LOG015: 291, ignored) | 0 | 0 |

### noqa reasons (all `BLE001` unless stated; counts)

- 83 tests: parity harness, the exception type and message are the outcome compared with the oracle.
- DTZ001/DTZ005 (45, tests): naive fixture time kept, an aware value is not provably identical.
- DTZ007 (3, `crc/gcp/_common.py`, `spot_vm/disks.py`, `spot_vm/instances.py`): `TIME_FORMAT` ends
  in `%z`, so the result is aware (the missing offset case is BUG-187, open).
- G003 (1): BUG-174.
- Per-resource / per-instance / per-disk / per-VM / per-NIC / per-key / per-request isolation,
  failure logged and recorded, resource kept (about 30 sites; SAF-003 AWS disk, SAF-005 Azure
  Spot VM, SAF-033/034 AWS spot, SAF-039 GCP spot disk, SAF-040 OCI spot, BUG-162 OCI VM).
- Per-region / per-zone isolation, region skipped and recorded (snapshot, spot, GCP, OCI).
- Listing failures that keep everything (BUG-186 GCP VM, GCP disk zones, AWS spot regions).
- Notification sinks must not abort the run (Slack, Slack owners, Influx, `crc/cli/scan.py`).
- Read-only scan paths, display-only values, and best-effort fallbacks (`crc/aws/vm/scan.py`,
  `crc/cli/scan.py`, `crc/notify/slack.py`, `requests.py` naive-time UTC fallback, BUG-279).
- `crc/cli/bridge.py` (2): the error is stored and `run_routed` re-raises it after the notifiers.
- No BLE001 was narrowed: no test shows a narrower type covers every exception that can reach it.

### Per-file ignores (pyproject.toml, listed with reasons)

- `crc/aws/*/client.py`: `N802`, `N803` (boto3 keyword arguments such as `Filters=`, `VpcId=`).
- 34 test files: `N802`, `N803` (fakes that mirror the same boto3 / oracle signatures).
- Locked tests that cannot be edited: `test_aws_vpc.py`, `test_core_age.py`, `test_core_age_fix.py`
  (`DTZ001`), `test_cli_logger.py` (`C420`), `test_gcp_spot_vm_engine.py` (`C408`).

## Owner action

- Locked tests with per-file ignores instead of edits: the five files above. When relocked, fix
  the naive datetimes / comprehension / `dict()` call and drop the entries.
- Decide whether naive fixture datetimes in tests should become aware (45 `DTZ001`/`DTZ005`
  noqa); that is a test-behaviour change and was not provable here.

## New bugs

None found. (`crc/azu/disk/cleaner.py:118` still raises `TypeError` on a `None` disk name, which is
BUG-174, already open.)
