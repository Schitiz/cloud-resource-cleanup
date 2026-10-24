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

## Round 1 (Argon)

### Findings (fixed in this round)

1. **`CLEANUP_SAFETY.md:202,258` — Two remaining post-`AD-VM` / post-adapter references:**
   - `:202` still cited `crc.azu.vm.VM` (`VM` was deleted in `AD-VM`); updated to `crc.azu.vm.VmCleaner`.
   - `:258` in the module map still claimed `crc.py` re-exports `CRC`, the cleaner classes and constants from `crc/cli/` and the cloud packages; updated to match `crc.py:7-28` (`main`, `get_argparser` and the input validators from `crc/cli/`).
2. **`crc/azu/vm/README.md:45` — Ambiguous `MAX_AGE` wording:**
   - Said `is_old, which still reads MAX_AGE`; updated to `where MAX_AGE still applies` so it does not imply an environment read inside `crc/core`.
3. **`ARCHITECTURE.md:118` and `crc/{gcp,oci}/README.md` — Add-a-cleaner step 6 & section title:**
   - Step 6 in `ARCHITECTURE.md:118` now also names `crc/core/selection.py` (`RESOURCES` or `EXTRA_RESOURCES`) alongside `crc/cli/constants.py` (noted in Audit 3 section 3.7).
   - `crc/gcp/README.md:65` and `crc/oci/README.md:44` now cite `"Add a cleaner"` (matching `ARCHITECTURE.md:101`) instead of `"Add a resource cleaner"`.
4. **`tests/archtest/README.md:31` — Missing period:**
   - Added the missing period after `with a written reason` in the `ARCH-011` row.

### Checklist Verification

1. **Task completeness (`f8ed6dd..HEAD`):**
   - **(1) Stale claims fixed:** Verified against code and data: `tests/archtest/README.md:4,24,62-63` (empty ratchet; `crc/core` bans `env` and `clock_ref`; `crc/cli` bans `re` and `clock_ref`; 46 of 46 `SAF-NNN` IDs locked, `gaps` empty), `ARCHITECTURE.md:89-91` and `.cursor/rules/20-core.mdc:10-11` (`MAX_AGE` injected by `crc/cli/context.py` `install_max_age_source` via `set_max_age_source`; `crc/core` reads no environment), `crc/README.md:15,42` and `tests/README.md:14-16,27-29,41-48,68-69` (empty legacy ratchet, no adapters, no legacy safety test files), `crc/azu/README.md:43` and `CLEANUP_SAFETY.md:202,258` (no `VM` adapter class), `crc/core/README.md:16-17,123` (`selection.py` holds only constants and `Selection`), `AGENTS.md:28-29` (measured test count and timing), `docs/refactor/BUGS.md:443` (`403 rows: critical 5, high 27, medium 65, low 306. 64 fixed and 5 partly fixed`), `README.md:89` (`-c constraints.txt`).
   - **(2) Agent pointers:** `AGENTS.md:17,21,85-87,106-112`, `ARCHITECTURE.md:118-137`, and `crc/cli/README.md:82-89` name `pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt`, `make smoke-offline`, `tests/fixtures/jenkins_commands.txt` with `tests/test_jenkins_contract.py`, and the ADDED tables in `tests/helpers_ag_cli_added.py` (claim that new flags are blocked removed). `AGENTS.md:85-86` instructs agents to search `BUGS.md` by ID or resource and not read it whole. `AGENTS.md` is 119 lines (`<= 120`, ARCH-010).
   - **(3) ARCH-011 bare filenames:** `tests/archtest/doc_links.py:22,29,73-86,136-140` resolves backticked bare filenames (`.py`, `.md`, `.txt`, `.json`, `.yml`, no slash) next to the document and then at the repo root, failing when neither exists; `BARE_NAME_ALLOWLIST` requires a non-empty reason (`test_arch011_bare_name_allowlist_entries_have_reasons`); 6 new self-tests in `tests/archtest/test_arch011_doc_links.py:173-239`. All 53 hits across live markdown were fixed.
   - **(4) Multi-agent skills:** `.claude/skills -> ../.cursor/skills` and `.agents/skills -> ../.cursor/skills` symlinks added (replacing `.claude/skills/crc-maintain`); `AGENTS.md:57-58` notes that Claude Code, Codex and Cursor share those playbooks. No settings files granting permissions were added.
2. **CLI / runtime / parity contract unchanged:**
   - `diff -u` of `python3 crc.py --help` between `f8ed6dd` and `HEAD` is empty (`HELP_IDENTICAL`).
   - Zero product files under `crc/` or `crc.py` were modified; `tests/test_jenkins_contract.py` and all `tests/test_*_parity.py` files are untouched.
3. **Guardrails & negative proof:**
   - `tests/legacy/*.txt`, `tests/archtest/safety_lock.json`, `tests/archtest/frozen_inputs.json`, and `docs/refactor/BUGS.md` rows are untouched.
   - Locally injected `` `nonexistent_bare_file.py` `` into `crc/azu/README.md`, ran `check_doc_links(REPO_ROOT)`, confirmed it failed with `ARCH-011: crc/azu/README.md:53 names nonexistent_bare_file.py, found in neither its directory nor the root` + `REMEDIATION:`, and reverted cleanly.
4. **Scope & ownership:**
   - All 25 touched paths in `git diff --name-only f8ed6dd..HEAD` belong to lane F-DOCS.
5. **Size & Public API sync:**
   - `tests/archtest/doc_links.py` is 146 lines (`<= 250`), longest function `_document_problems` is 19 lines (`<= 60`); `tests/archtest/test_arch011_doc_links.py` is 239 lines; `AGENTS.md` is 119 lines (`<= 120`); `ARCH-002` and `ARCH-004` pass.
6. **Gates, test count & runtime:**
   - `pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt` then `make check`: green (`make lint` 0 errors across ruff check, ruff format --check, mypy on 370 files, 5 import-linter contracts; `pytest`: **44,602 passed, 1 skipped** in 56.32s, total `make check` wall time 75.35s; `ARCH-008`: **44,603 collected**, floor 44,597).

VERDICT: APPROVE

