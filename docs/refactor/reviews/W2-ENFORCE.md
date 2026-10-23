## Coding summary

Lane W2-ENFORCE: prose rules turned into mechanical checks. No CLI behaviour change.

**Fast feedback**
- `requirements-dev.txt`: `pytest-xdist==3.8.0`.
- `make check` = `lint` + `pytest -q -n auto` + ARCH-008 floor check. New targets: `make lint` (ruff, mypy, lint-imports), `make check-fast` (lint + `pytest -n auto` without `tests/test_cli_main_parity.py`, `tests/test_cli_crc_parity.py`, `tests/test_cli_args_parity.py`), `make test-file F=tests/test_x.py`, `make raise-test-floor`.
- Runtime (4 cores): `make check` 2m58s before, about 1m01s after. `make check-fast` about 21s (9368 tests).
- xdist broke collection on two tests with process-dependent parametrize ids (object address in `tests/test_gcp_disk_fix.py`, set order and object address in `tests/test_cli_args_parity.py`). Fixed with stable ids only; no test logic changed, counts unchanged. `-n auto` is kept everywhere.

**Checks (all in `tests/archtest/`, documented in its README)**

| Rule | What | Module |
|------|------|--------|
| ARCH-003 (extended) | Per-package bans: `crc/core` no wall clock, `print`, `sys.exit`; `crc/cli` no `re`; `crc/notify` no `re`, env, `sys.exit` | `bans.py` (`PACKAGE_BANS`) |
| ARCH-005 (extended) | `check_plan_readonly_siblings` follows calls into sibling modules; old scan untouched; passes on current code | `readonly_plan.py` |
| ARCH-006 | No `async`/`await`/`asyncio`/`pydantic`/`httpx`/`tenacity`/`threading` in `crc/` and `crc.py` | `banned_constructs.py` |
| ARCH-007 | SHA-256 manifest of `tests/legacy/*.txt` and `requirements.txt` | `frozen_inputs.py`, `frozen_inputs.json`, owner-only `update_frozen_inputs.py` |
| ARCH-008 | Test-count floor, run by `make check` after pytest | `test_count.py`, `test_count_floor.txt` |
| ARCH-009 | Every `BUG-NNN` in `crc/**`, `tests/**` exists in `docs/refactor/BUGS.md` | `bug_refs.py` |

Each has a real check plus tmp_path self-tests that prove it fires and does not fire.

**`crc/core/age.py` split (284 to 120 lines)**: `age_spec.py` (AgeSpec, AGE_KEYS, KEEP_AGE, `require_positive_age`) and `age_tags.py` (custom age tag lookup and parsing). `age.py` re-exports every name (with `__all__`), so `crc.core.age.<name>`, `crc.core import age as core_age` and `crc.core` re-exports and mock targets on `core_age` keep working. No public name was added, so the ARCH-002 symbol sync is unchanged.

**MAX_AGE env read left in `crc/core/age.py`**: `is_old` reads `MAX_AGE` at call time. A setter that `crc/cli/main.py` calls would not keep env-only callers working (the many tests and callers that only set the env var), and the env read would still have to live in `crc/core` as the fallback. Moving it needs a read outside `crc/core` that core cannot import (layering). Not done; the `crc/core` env ban is listed under Wave B checks (no allowlist entry).

**Test count**: 43010 before (cea0a8a) and 43068 after (+58), floor file set to 43068.

**Other edits needed by the new checks**: `tests/test_log_fix_*.py` wrote the deliberately unknown ID `BUG-999` as a literal; it is now built as `"BUG-" + "999"` so ARCH-009 does not flag it (same value). `tests/archtest/test_arch003_bans.py::test_arch003_selftest_skips_legacy_and_other_packages` used `crc/core` as its "other package"; it now uses `crc/service.py` and `crc/other` because `crc/core` is now scanned.

**Owner actions**
1. `frozen_inputs.json` was generated once by me with `update_frozen_inputs.py` from the tree at cea0a8a (the files are unmodified in git); verify the hashes against `main` if you want. After that, only the owner runs the script.
2. `frozen_inputs.json` and `test_count_floor.txt` sit under the `/tests/archtest/` CODEOWNERS entry already. The docs lane should mention ARCH-006..009 in `AGENTS.md` ("Rule IDs ARCH-001..005") and `ARCHITECTURE.md`; not touched here. Run `make raise-test-floor` at the end of each wave.
3. `.github/workflows/ci.yml` needed no change (it runs `make check`, and `pip install -r requirements-dev.txt` brings xdist).

## Wave B checks

- **ARCH-003 `env` ban for `crc/core`**: `crc/core/age.py` `_apply_max_age_override` (`os.getenv("MAX_AGE")`). Needs `MAX_AGE` to be handed to core by the CLI boundary (setter or parameter threaded through `is_old` callers) and the env-only tests updated; touches every cloud caller of `core_age.is_old`.
- **ARCH-003 `clock`/`print` in `crc/notify` and `crc/cli`**: left legitimate today (`crc/notify/slack.py:44` clock, `print` in `slack.py`, `influx.py:89`; `crc/cli/notify.py:59` clock). Candidates to ban once injected clocks and the logger are used.
- **ARCH-003 `re` in `crc/core`** is intentionally allowed (`crc/core/policy.py:12`).
- ARCH-005 sibling scan found nothing on the current code; no pending item. It does not follow methods of imported classes or calls through instances of sibling classes; a later check could.
- ARCH-006 does not forbid `concurrent.futures`; none is used in `crc/` today.

## New bugs

None found.
