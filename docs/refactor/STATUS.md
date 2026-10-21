# Refactor status

| Rung | State | Notes |
|------|-------|-------|
| R0a | done, reviewed: APPROVE | Added pyproject (ruff, mypy strict, import-linter, pytest config), requirements-dev.txt, Makefile `check`, Cursor environment, AGENTS.md/CLAUDE.md, ARCHITECTURE.md, CODEOWNERS, Cursor rules and project skill. Review (`docs/refactor/reviews/R0a.md`) replaced the whole-tree exemptions with a per-file legacy list (new files are checked), added mypy `files` guard; 110 tests before and after. |
| R0b | done, reviewed: APPROVE | Added `tests/archtest/` (ARCH-001..005, SAF-LOCK, each with self-tests, README, `legacy_baseline.txt`, `safety_lock.json`, owner-only `update_safety_lock.py`), `[SAF-001]`..`[SAF-046]` tags in `CLEANUP_SAFETY.md`, pinned `requirements-dev.txt`, `.github/workflows/ci.yml` (Python 3.11, `make check`), pointers in AGENTS.md and ARCHITECTURE.md. Review (`docs/refactor/reviews/R0b.md`) removed 4 wrong test mappings in `safety_lock.json` (`SAF-015`, `SAF-032`, `SAF-034`) and moved `SAF-034` to `gaps`. No change to `crc.py`, `crc/` or existing tests. pytest: 110 existing + 80 archtest = 190 passed. 30 of 46 SAF IDs locked to 61 existing test entries; 16 gaps. |

Open issues (R0a):

- Core layer import-linter contract is a commented TODO until `crc/core` exists.
- `.cursor/environment.json` needs `python3.11` on the image; `make check` uses
  `.venv/bin` when present, otherwise tools on `PATH`.
- CODEOWNERS only takes effect once branch protection requires code owner review.
- `crc.py` (module) and `crc/` (package) share the name `crc`; mypy checks only
  `crc/` and `tests/` (`files`), so the CLI rung must resolve the clash.

Open issues (R0b):

- SAF gaps with no existing test (not invented): SAF-001, 002, 004, 005, 006, 009, 010,
  014, 016, 021, 022, 023, 024, 034, 036, 037. Later rungs that add tests should ask the owner
  to map them with `tests/archtest/update_safety_lock.py --map`.
- SAF-LOCK hashes use a custom version-stable AST dump; verified identical on Python 3.11.17
  and 3.12.3. `update_safety_lock.py` is owner-only and its files are in CODEOWNERS (only
  enforced with branch protection).
- Pins (pytest 9.1.1, ruff 0.17.1, mypy 2.4.0, import-linter 2.15, types-python-dateutil
  2.9.0.20260807) passed `make check` on 3.11.17 and 3.12.3. The CI workflow has not run on
  GitHub yet.
- ARCH-002 covers sub-directories of `crc/`, not `crc/` itself. ARCH-005 also follows
  `self.`/`cls.` methods and same-module functions transitively from `plan`.
