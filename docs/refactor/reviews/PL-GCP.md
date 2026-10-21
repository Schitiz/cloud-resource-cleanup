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
