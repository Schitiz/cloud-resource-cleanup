# PL-GCP review

## Coding summary

Rung PL-GCP: `crc/gcp/_base.py` and `crc/gcp/__init__.py` made strict-clean (lane
`refactor/lane-gcp`). No behaviour change.

- **Summary.** `get_gcp_regions(project_id: str) -> list[str]` keeps the exact SDK use of main:
  one `compute_v1.RegionsClient()` per call, then `client.list(project=project_id)`, then the
  names in listing order. Only changes: type annotations and removal of the no-op
  `project_id = project_id`, the narrating comment and the temporary variable. There is no env
  read, no fallback, no log, no print and no error handling on main, and none was added (BUG-067
  stays). `__init__.py` holds only the copyright comment, is ruff clean and has no export list.
  Callers: none on this branch (`crc/gcp/ip.py` now builds its own `RegionsClient`; on main
  `ip.py:8` imported it), `crc.py` and the cleaners are unchanged.
- **Parity.** `tests/legacy/gcp_base.txt` is the byte-identical `git show main:crc/gcp/_base.py`.
  `tests/test_gcp_base_parity.py` runs oracle and module against the same fake
  `compute_v1.RegionsClient` over 24 cases (two, one, unsorted, empty and duplicate regions,
  env set and unset, empty and `None` project, non-string and nameless regions, generator and
  tuple listings, non-iterable listing, constructor credential error, listing permission,
  authentication, unreachable and connection errors (no fallback), mid-iteration error),
  comparing SDK constructions and calls in order with arguments, results, logs, stdout and
  raised errors, plus quirk assertions. Non-vacuity: replacing the comprehension with
  `sorted(...)` failed `unsorted-regions` and `non-string-names`; wrapping the project in
  `str(...)` failed `none-project-id`; both reverted.
- **Test counts.** Before: 7379 passed. After: 7415 passed (+36: 30 in `tests/test_gcp_base_parity.py`, 6 in `tests/test_gcp_base.py`). No existing test changed.
- **Gates.** `ruff check .`, `mypy` (strict, no per-SDK override needed: google-cloud-compute is
  typed; one narrow `# type: ignore[no-untyped-call]` in `tests/test_gcp_base.py` for the
  untyped `google.api_core` exception constructor), `lint-imports`, `pytest -q`.
  `crc/gcp/__init__.py`, `crc/gcp/_base.py`, `crc.gcp` and `crc.gcp._base` are removed from both
  ratchet lists in `pyproject.toml`.
- **Open issues.** Five new quirks in `docs/refactor/bugs/pending/PL-GCP.md` (none fixed).
  `get_gcp_regions` is currently unused; removing it is a later decision, not this rung.
  `docs/refactor/bugs/pending/README.md` lists only `GCP-1.md` in its Public API: the integrator
  can add `PL-GCP.md` (not edited here, outside the lane).
- **Core change needed.** None.
- **`crc/README.md` / `tests/legacy/README.md` / `tests/README.md` change needed.** Add
  `gcp_base.txt` (exact `git show main:crc/gcp/_base.py`, used by
  `tests/test_gcp_base_parity.py`) to `tests/legacy/README.md`. `crc/README.md`: mark
  `crc/gcp/_base.py` and `crc/gcp/__init__.py` as refactored if it lists them as legacy.

## Round 1 (Argon)

Scope reviewed: `git diff ef1f718..HEAD` (`crc/gcp/_base.py`, `crc/gcp/__init__.py`, `crc/gcp/README.md`, `pyproject.toml`, `docs/refactor/bugs/pending/PL-GCP.md`, `docs/refactor/reviews/PL-GCP.md`, `tests/legacy/gcp_base.txt`, `tests/test_gcp_base.py`, `tests/test_gcp_base_parity.py`) against `git show main:crc/gcp/_base.py`, `git show main:crc/gcp/__init__.py`, `AGENTS.md`, `docs/refactor/BUGS.md`, and `.cursor/skills/crc-python-refactor/REVIEW_CHECKLIST.md`.

### 1. Behaviour parity with `git show main:<path>`

- **`crc/gcp/_base.py`** (`crc/gcp/_base.py:1-9` vs `main:crc/gcp/_base.py:1-13`):
  - `get_gcp_regions(project_id: str) -> list[str]` preserves the exact signature (`project_id` parameter), SDK construction (`compute_v1.RegionsClient()` with no arguments), list call (`client.list(project=project_id)`), and return value (`[region.name for region in regions]` in listing order).
  - No environment variable or config is read directly by the module; no log line or `print` is emitted; no exception is caught or swallowed, and there is no connectivity fallback (`BUG-067` preserved).
  - Only changes from `main` are parameter/return type annotations and dropping the dead self-assignment `project_id = project_id`, narrating comment, and local `region_list` variable.
- **`crc/gcp/__init__.py`** (`crc/gcp/__init__.py:1` vs `main:crc/gcp/__init__.py:1`):
  - Byte-identical to `main` (`# Copyright (c) Yugabyte, Inc.`, no `__all__`).

### 2. Oracle and parity test verification (`tests/legacy/gcp_base.txt`, `tests/test_gcp_base_parity.py`)

- Diffed `tests/legacy/gcp_base.txt` against `git show main:crc/gcp/_base.py`: byte-identical (0 lines of diff).
- Verified `tests/test_gcp_base_parity.py` executes both the oracle (`tests/legacy/gcp_base.txt`) and `crc.gcp._base` against the same `FakeComputeV1` / `FakeRegionsClient` across 24 cases and 6 quirk assertions, comparing ordered SDK `calls` (with `args` and `kwargs`), `result`, `logs` (at `DEBUG`), `stdout`, and `error` (`(type(exc).__name__, str(exc))`).
- Tested a deliberate one-line behaviour change in `crc/gcp/_base.py` (`return sorted(region.name for region in regions)` instead of `return [region.name for region in regions]`): `pytest -q tests/test_gcp_base_parity.py` failed immediately (2 failed: `unsorted-regions`, `non-string-names`); reverted.

### 3. Ratchet, typing, lint, scope, and pending bugs

- `crc/gcp/__init__.py` and `crc/gcp/_base.py` (`crc.gcp` and `crc.gcp._base`) were removed from both the ruff `extend-exclude` and mypy `ignore_errors` ratchet lists in `pyproject.toml`; nothing was added (`ARCH-001`), and no new mypy override was needed.
- `crc/gcp/_base.py` and `crc/gcp/__init__.py` pass `ruff check .` and `mypy` (`strict = true`) with zero `# type: ignore` or `# noqa` comments (`tests/test_gcp_base.py:15` has one narrow `# type: ignore[no-untyped-call]` on `PermissionDenied("denied")`).
- Verified `git diff ef1f718..HEAD --name-status`: `crc.py`, `crc/core/**`, every cleaner module, and all lane-forbidden files (`docs/refactor/BUGS.md`, `docs/refactor/STATUS.md`, `docs/refactor/FILTER_VARIANTS.md`, `crc/README.md`, `tests/README.md`, `tests/legacy/README.md`, other cloud helpers) are untouched.
- `crc/gcp/README.md` edits are scoped to the PL-GCP sections and pass `ARCH-002` symbol sync (`get_gcp_regions()`).
- Verified all 5 rows in `docs/refactor/bugs/pending/PL-GCP.md` against `git show main:crc/gcp/_base.py`: all `main` file:line citations (`:12`, `:6-9`, `:7`, `:8`, `:11`), `BUGS.md` columns (`ID` = `NEW`, valid `Effect` and `Risk` values), and descriptions are accurate.

### BLOCKING (fixed)

None.

### NIT (left)

None.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` (`crc`, `tests`) | Success: no issues found in 164 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 7415 passed |

Test count: 7379 before PL-GCP (`ef1f718`), 7415 after (+36: 30 in `tests/test_gcp_base_parity.py`, 6 in `tests/test_gcp_base.py`).

VERDICT: APPROVE
