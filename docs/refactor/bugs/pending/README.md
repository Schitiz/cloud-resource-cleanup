# docs/refactor/bugs/pending

## Purpose

Bug and quirk rows not yet merged into `docs/refactor/BUGS.md` (see `docs/refactor/bugs/README.md`).

## Public API

- `docs/refactor/BUGS.md` (rows `BUG-001` and up): every pending file has been folded into `BUGS.md`; this directory holds only this README.

## Safety Invariants

- Rows use the `BUGS.md` columns with ID `NEW`, and cite the `main` file:line.
- No row is a fix; behaviour stays as it is until a fix with its own test and `BUGS.md` status.

## Extension Rules

1. Add one `<topic>.md` per change.
2. Never reuse or renumber IDs after the rows move to `BUGS.md`.
