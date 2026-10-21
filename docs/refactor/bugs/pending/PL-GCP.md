# PL-GCP pending bugs and quirks

Rows found while refactoring `crc/gcp/_base.py` and `crc/gcp/__init__.py` (rung PL-GCP). None is
fixed. Same columns as `docs/refactor/BUGS.md`; ID is `NEW` until the integrator assigns one.
Locations are `main` (`git show main:crc/gcp/_base.py`). `BUG-067` (no error handling and no
connectivity fallback in `get_gcp_regions`) already exists and is not repeated.

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | `get_gcp_regions` iterates the SDK pager inside a list comprehension: an error while fetching a later page discards the regions already read and raises, so the caller gets no partial list (`BUG-067` shape, mid-iteration) | `crc/gcp/_base.py:12` | yes | run fails | low | PL-GCP | open |
| NEW | `project_id` is passed to `RegionsClient().list(project=...)` without validation: `None` or an empty string reaches the SDK and fails there (or lists nothing useful) instead of failing before any cloud call | `crc/gcp/_base.py:6-9` | yes | run fails | low | PL-GCP | open |
| NEW | Region names are returned as the SDK yields them: no filtering, sorting or deduplication, and a region object without a string `name` is passed through (or raises `AttributeError`) | `crc/gcp/_base.py:12` | yes | cosmetic | low | PL-GCP | open |
| NEW | A new `RegionsClient` (new credential lookup) is built on every `get_gcp_regions` call, and the client is never closed | `crc/gcp/_base.py:7` | yes | cosmetic | low | PL-GCP | open |
| NEW | No-op self-assignment `project_id = project_id` and a stray comment: dead code with no effect (dropped in the refactor, no behaviour change) | `crc/gcp/_base.py:8`, `:11` | yes | cosmetic | low | PL-GCP | open |
