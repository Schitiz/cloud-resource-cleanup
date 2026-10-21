# tests

## Purpose

Offline pytest suite (`pytest -q`, part of `make check`). No test calls a real cloud API or uses
credentials; SDK clients are mocked. Layout:

- `test_core_*.py`: pure tests of `crc/core` (age, policy, cleaner, registry, report, selection, engine).
  Some compare against `crc.py` itself, loaded under another module name.
- `test_aws_*.py`, `test_azu_*.py`, `test_gcp_*.py`, `test_oci_*.py`: mocked tests of the legacy
  cloud modules, several of them locked by `SAF-LOCK`.
- `archtest/`: mechanical architecture checks (see `tests/archtest/README.md`).

## Public API

This directory exposes no library. Run everything with `make check`, or only tests with `pytest -q`.
`tests/__init__.py` makes `tests.archtest` importable.

## Safety Invariants

- Never delete, skip, xfail, weaken or loosen a test; add or strengthen only. The test count never drops.
- Tests mapped in `tests/archtest/safety_lock.json` are hash-locked; changing one needs the owner
  (`tests/archtest/README.md`).
- Mock every SDK client; no credentials, no network. `plan()` tests assert no mutating call was made.
- Use `tmp_path` and `monkeypatch`; no shared mutable state, no autouse session fixtures.

## Extension Rules

1. Name new files `test_<package>_<module>.py` and keep them typed (they are checked by ruff and mypy
   unless listed in the legacy ratchet, which may only shrink).
2. Cover the happy path, the fail-closed path, dry run without mutating calls, and call order for
   destructive sequences (`.cursor/skills/crc-python-refactor/SKILL.md`, section 5).
3. A new bug found by a test goes into `docs/refactor/BUGS.md`; the test preserves the quirk.
