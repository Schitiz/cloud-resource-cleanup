# WC-DOCS

## Coding summary

- Lane: docs only (docstrings, comments and READMEs); no logic, no test logic, no BUGS.md or
  CLEANUP_SAFETY.md edits. Nothing was routed, shimmed or deleted: the CLI already runs every
  (cloud, kind) pair through `crc.cli.bridge` -> route tables -> `crc.core.engine.run` -> registered
  Cleaners -> `crc.notify`, so the docs now say so. The adapter classes in `crc/aws`, `crc/azu`,
  `crc/gcp` and `crc/oci` belong to the other lanes and are untouched; no parity-test retargeting
  was needed here.
- `crc/core`: `engine.py` ("nothing is wired yet", the `vpc` label "placeholder for the wiring
  rung"), `selection.py` ("the wiring rung only calls `build_selection()`"; now says the bridge builds
  a one-pair `Selection` and `validate_targets` checks pairs), `report.py`, `logger.py`, `policy.py`
  docstrings and comments; `crc/core/README.md` (deferred-wiring paragraph, rung names R3 / FIX-CORE-AGE /
  LOG-0, `crc.py` strings, moved-doc links: `docs/archive/FILTER_VARIANTS.md`, `docs/logging.md`).
- `crc/README.md` (`crc.py` re-exports only `main`, `get_argparser` and the validators; the adapter
  classes are not the CLI entry point), `crc/notify/README.md` and `crc/notify/*.py` comments (no more
  "as `crc.py` does today"), `tests/README.md`, `docs/refactor/bugs/README.md` and
  `docs/refactor/bugs/pending/README.md` (no lanes or rungs).
- `tests/*.py`: 64 module docstrings and comments lost their rung, lane and review names (`FIX-*`,
  `LOG-*`, `CL2-*`, `WA-*`, `ENG-*`, `pre-CL2`, `BEHAVIOUR_FIX.md`, `LOGGING.md`). BUG-NNN and SAF-NNN
  IDs stay. Test and file names are unchanged (for example `test_bug_356_lane_rule_...`,
  `helpers_cl2_*.py`, `helpers_wa1_notify.py`).
- Test count: 44415 before and after (no test added or removed; ARCH-008 unchanged, no floor
  raise). `make check` is green: ruff, mypy, lint-imports, pytest, ARCH checks, SAF-LOCK.
- Owner actions: none. Optional follow-ups below.

## Left over (files this lane may not edit)

- `crc/aws/**`, `crc/azu/**`, `crc/gcp/**`, `crc/oci/**` READMEs still cite `docs/refactor/PLAN.md`,
  `FILTER_VARIANTS.md`, `LOGGING.md` and `.cursor/skills/crc-python-refactor/BEHAVIOUR_FIX.md`, and
  rung names (R4a, AWS-2, ENG-0, ...); `crc/aws/keypairs/__init__.py` names `ENG-0`.
- `crc/cli/README.md` and `crc/cli/routes/azu.py:1` ("Empty until its lane migrates them").
- `tests/legacy/README.md:65` (`BEHAVIOUR_FIX.md`) and the archtest remediation texts
  (`tests/archtest/bug_refs.py:15`, `frozen_inputs.py:13-14`).
- Test file names that carry lane names (`helpers_cl2_*.py`, `helpers_wa1_notify.py`,
  `helpers_wa2_scan.py`) were left because renaming is not a docstring edit.

## New bugs

None found. Doc statements that were wrong and are now fixed: `crc/README.md` said `crc.py`
re-exports the adapter names, the constants and `CRC`; `crc/notify/README.md` said `crc.py`
delegates `notify_*`, `ping_on_slack`, `get_msg` and `write_influxdb` to the notifiers (`crc.py` is
a 30-line entry point; the `CRC` run context in `crc/cli/runner.py` has only `get_msg`).
