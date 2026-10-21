# Refactor status

| Rung | State | Notes |
|------|-------|-------|
| R0a | done, reviewed: APPROVE | Added pyproject (ruff, mypy strict, import-linter, pytest config), requirements-dev.txt, Makefile `check`, Cursor environment, AGENTS.md/CLAUDE.md, ARCHITECTURE.md, CODEOWNERS, Cursor rules and project skill. Review (`docs/refactor/reviews/R0a.md`) replaced the whole-tree exemptions with a per-file legacy list (new files are checked), added mypy `files` guard; 110 tests before and after. |

Open issues (R0a):

- Core layer import-linter contract is a commented TODO until `crc/core` exists.
- `.cursor/environment.json` needs `python3.11` on the image; `make check` uses
  `.venv/bin` when present, otherwise tools on `PATH`.
- CODEOWNERS only takes effect once branch protection requires code owner review.
- `crc.py` (module) and `crc/` (package) share the name `crc`; mypy checks only
  `crc/` and `tests/` (`files`), so the CLI rung must resolve the clash.
