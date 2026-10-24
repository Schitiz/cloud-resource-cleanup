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
  (which uses f-strings); it now compares logger name, level and rendered message (`getMessage()`),
  the log text.
- Tests: `N811` alias `NewCRC` -> `NEW_CRC` (6 files), `_Built` -> `_BuiltError`, `routed_Check` ->
  `routed_check`, `N802` `_BUG_NNN` -> `_bug_nnn` in `test_azure_nic_fix.py` and
  `test_azure_nic_parity.py` (13 functions), two `dict.fromkeys` (C420). Nothing else renamed.

### Counts per rule (`ruff check --select <rule>`, LOG015 ignored, whole repo)

| Rule | Before crc | Before tests | After |
|------|-----------:|-------------:|------:|
| DTZ  | 3   | 49  | 0 (3 + 45 noqa, 4 sites in locked tests ignored per file) |
| BLE  | 68  | 83  | 0 (151 noqa) |
| G    | 118 (117 G004, 1 G003) | 0 | 0 (1 noqa) |
| C4   | 0   | 4   | 0 (2 fixed, 2 in locked tests ignored per file) |
| RET  | 0   | 0   | 0 |
| N    | 37  | 121 | 0 (N802/N803 per-file ignores, N811/N818/N806/N802 fixed) |
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
- 32 test files: `N802`, `N803` (fakes that mirror the same boto3 / oracle signatures).
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

## Round 1 (Argon)

### Findings (fixed in round 1)

1. `pyproject.toml:70-71`, `tests/test_azure_nic_fix.py:41-174`, `tests/test_azure_nic_parity.py:639`:
   `test_azure_nic_fix.py` (12 functions) and `test_azure_nic_parity.py` (1 function) were listed in
   `[tool.ruff.lint.per-file-ignores]` for `N802`/`N803` even though their `N802` hits were test
   function names with uppercase `_BUG_111`/`_BUG_113`/`_BUG_114`/`_BUG_122` suffixes rather than
   SDK or oracle signatures. Renamed those 13 test functions to lowercase `_bug_nnn` and removed
   both files from `[tool.ruff.lint.per-file-ignores]`.
2. `tests/test_aws_base_parity.py:218`: switching `logs` from `(r.levelno, r.msg, r.args, r.getMessage())`
   to `(r.levelno, r.getMessage())` did not include `r.name`; updated to
   `[(r.name, r.levelno, r.getMessage()) for r in caplog.records]` so logger name parity is asserted
   alongside level and rendered message text.
3. `AGENTS.md:25-26`: joined the added rule-set note into one line as specified by the task.

### Verification of checklist

1. **Ruff rules and format**: `DTZ`, `BLE`, `G`, `LOG`, `C4`, `RET`, `N` are selected in
   `pyproject.toml` (`[tool.ruff.lint]`), with only `LOG015` globally ignored. `ruff check .` and
   `ruff format --check .` pass across `crc/`, `crc.py`, and `tests/`, and `ruff format --check .`
   runs in `make lint` (`Makefile:16`) and `.github/workflows/ci.yml:21`. The reformat commit
   (`26470a1`) is isolated as its own formatting-only commit.
2. **No behaviour change**:
   - **DTZ**: 0 semantic changes. All 3 `DTZ007` sites in `crc/gcp/` (`_common.py:36`,
     `spot_vm/disks.py:99`, `spot_vm/instances.py:72`) parse with `TIME_FORMAT` ending in `%z` and
     are kept with `# noqa: DTZ007 - TIME_FORMAT ends in %z, so the result is aware` (missing offset
     is tracked under open `BUG-187`). All 45 `DTZ001`/`DTZ005` sites in unlocked tests are kept
     with `# noqa` + reason, and 4 sites in 3 locked tests are in `per-file-ignores` and listed under
     Owner action.
   - **BLE**: AST comparison across all modified files confirms 0 `ExceptHandler` types were
     narrowed or altered in `crc/` or `tests/`; all 68 `crc/` sites and 83 `tests/` parity-harness
     sites carry `# noqa: BLE001 - <reason>` citing `SAF-NNN` or `BUG-NNN` where applicable.
   - **G004/G003 & LOG**: AST comparison of all 118 logging calls in `crc/` confirms all 117 `G004`
     conversions produce the exact same rendered message and argument order (including the mixed
     f-string + `%s` call in `crc/azu/spot_vm/disks.py:93`), and the 1 `G003` site in
     `crc/azu/disk/cleaner.py:118` is kept with `# noqa: G003 - BUG-174` so `disk_name=None` still
     raises `TypeError`. Logger names are unchanged across the repo.
3. **noqa and ignores**: Every `# noqa` added in `154dc27..HEAD` carries a `- <reason>`. Global
   `ignore` contains only `["LOG015"]`. All remaining `N802`/`N803` per-file ignores in
   `pyproject.toml` (`crc/aws/*/client.py` and 32 test files) are verified to be boto3/SDK/oracle
   method or argument names (`Filters`, `VolumeId`, `KeyId`, `VpcId`, `DhcpOptions`,
   `chat_postMessage`, `users_lookupByEmail`, `zoneOperations`, `RegionsClient`, etc.).
4. **Tests, oracles, and locks**: `tests/legacy/*.txt` and all 18 files in
   `tests/archtest/safety_lock.json` are untouched in `git diff 154dc27..HEAD`. No test was
   weakened, skipped, or deleted; test count is 44,572 (44,571 passed, 1 skipped; floor 44,572).
5. **Size limits**: `ARCH-004` passes (all non-legacy, non-test files <= 250 lines, functions <= 60
   lines).
6. **Gates**:
   - `ruff check .`: pass
   - `ruff format --check .`: pass (369 files already formatted)
   - `mypy`: pass (368 source files)
   - `lint-imports`: pass (5 kept, 0 broken)
   - `ARCH-001..011` and `SAF-LOCK`: pass
   - `make check`: **44,571 passed, 1 skipped in 54.52s** (ARCH-008: 44,572 tests, floor 44,572)

VERDICT: APPROVE
