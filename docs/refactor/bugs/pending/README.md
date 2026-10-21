# docs/refactor/bugs/pending

## Purpose

Per-rung bug and quirk rows not yet merged into `docs/refactor/BUGS.md` (see `docs/refactor/bugs/README.md`).

## Public API

- `GCP-1.md`: quirks of the GCP IP cleaner (`crc/gcp/ip.py`).

## Safety Invariants

- Rows use the `BUGS.md` columns with ID `NEW`, and cite `main` file:line.
- No row is a fix; behaviour stays as on `main` until a behaviour-fix rung.

## Extension Rules

1. Add one `<rung>.md` per rung.
2. Never reuse or renumber IDs after the rows move to `BUGS.md`.
