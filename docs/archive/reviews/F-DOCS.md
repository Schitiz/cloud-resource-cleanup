## Coding summary

Lane F-DOCS (branch `fw/docs`): documentation drift, agent pointers, ARCH-011 bare filenames and multi-agent skill links. No product code, flag, selection, delete, Slack/Influx or exit-code change.

- **Routed:** nothing changes in routing; every `(cloud, kind)` pair already runs through `crc.core.engine`. This lane is docs and the ARCH-011 checker only.
- **Adapters deleted or shimmed:** none by this lane (the audits' adapters were deleted earlier). The docs that still claimed adapters, five legacy safety test files, a non-empty ratchet or a `VM` class were corrected.
- **CLI parity tests reach the cleaners:** through the route tables and `FakeCleaners` (`tests/helpers_cli_routes.py`), which patches `bridge.build_registry` and `bridge.build_notifiers`; unchanged here and now documented in `crc/cli/README.md` and `ARCHITECTURE.md`.
- **Test count:** before 44,597 (committed floor; 44,421 claimed in `AGENTS.md`), after 44,603 collected (44,602 passed, 1 skipped). The six extra tests are ARCH-011 self-tests in `tests/archtest/test_arch011_doc_links.py` (five for bare filenames, one for symlinked directories). `make check-fast` 26 s (14,233 tests), `make check` 58 s, measured on 4 cores.
- **Owner actions:** run `make raise-test-floor` after the lanes merge (this lane did not touch `tests/archtest/test_count_floor.txt` to avoid a three-way conflict; the floor is 44,597, the suite is 44,603). Nothing else.
- **New bugs:** none.

### What changed

1. Stale claims fixed: `tests/archtest/README.md` (46 of 46 SAF locked, no gaps; `crc/core` bans `env` and `clock_ref`; `crc/cli` bans `clock_ref`; empty ratchet), `ARCHITECTURE.md` and `.cursor/rules/20-core.mdc` (`MAX_AGE` is injected by `crc/cli/context.py` `install_max_age_source`, which calls `crc.core.age.set_max_age_source`; `crc/core` reads no environment), `crc/README.md` and `tests/README.md` (empty ratchet, no legacy safety test files, no adapters), `crc/azu/README.md` (no `VM` class), `crc/core/README.md` (`selection` holds only constants and `Selection`), `AGENTS.md` timings and test count, `docs/refactor/BUGS.md` counts line (64 fixed, not 63), root `README.md` install line (`-c constraints.txt`), `crc/oci/README.md`, `crc/README.md` extension rule.
2. Agent pointers: `AGENTS.md`, `ARCHITECTURE.md` (add-a-cleaner steps 6 to 8) and `crc/cli/README.md` name `pip install ... -c constraints.txt`, `make smoke-offline`, `tests/fixtures/jenkins_commands.txt` with `tests/test_jenkins_contract.py`, and the ADDED tables of `tests/helpers_ag_cli_added.py`; the claim that new flags are blocked is gone. `AGENTS.md` says to search `BUGS.md` by ID or resource, not read it whole. `AGENTS.md` is 119 lines (ARCH-010 limit 120).
3. ARCH-011: backticked bare filenames (`.py .md .txt .json .yml`, no slash) must exist next to the document or at the repo root; `BARE_NAME_ALLOWLIST` (empty) takes a name only with a written reason; register rows and fenced code stay exempt; five self-tests. 53 hits fixed by writing root-relative paths (`CLEANUP_SAFETY.md`, `crc/aws/README.md`, `crc/cli/README.md`, `docs/refactor/bugs/**`, two footer lines of `docs/refactor/BUGS.md` now point to `docs/archive/FILTER_VARIANTS.md`, `tests/README.md`, `.cursor/rules/30-safety.mdc`, `AGENTS.md`, `ARCHITECTURE.md`, `crc/oci/README.md`). The scan also skips markdown behind a symlinked directory (one self-test), so the new skill links are never scanned twice.
4. Multi-agent skills: `.claude/skills` and `.agents/skills` are symlinks to `../.cursor/skills` (the old `.claude/skills/crc-maintain` link is replaced); `AGENTS.md` says the playbooks live there for Claude Code, Codex and Cursor. No settings files, no permissions granted.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt` then `make check`: green (lint, 44,602 passed, 1 skipped, ARCH-008 floor 44,597).

### Left for later

- `docs/refactor/BUGS.md` stays one table by owner decision; its rows were not edited.
- Facts repeated by hand across READMEs (route lists, SAF counts) are still hand-maintained; only the bare-filename and path checks are mechanical.
