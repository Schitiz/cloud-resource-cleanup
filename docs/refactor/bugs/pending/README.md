# docs/refactor/bugs/pending

## Purpose

Pending bug and quirk rows per rung (`AZ-1.md` and its siblings), waiting to be merged into
`docs/refactor/BUGS.md`.

## Public API

- `<rung>.md`: one table per rung with the `docs/refactor/BUGS.md` columns and ID `NEW`.

## Safety Invariants

- Every row cites the `main` `file:line` checked with `git show main:<path>`.
- Refactor rungs preserve these quirks and pin them with a test; they are not fixed here.

## Extension Rules

1. Add one file per rung, named exactly like the rung.
2. Do not renumber or delete rows; the integrator changes the ID when merging.
