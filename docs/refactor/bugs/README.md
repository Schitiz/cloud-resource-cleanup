# docs/refactor/bugs

## Purpose

Holding area for bugs and quirks found by parallel refactor lanes, so that `docs/refactor/BUGS.md`
is edited in one place only (by the integrator).

## Public API

- `pending/<rung>.md`: the new bugs and quirks of one rung, same columns as `docs/refactor/BUGS.md`.

## Safety Invariants

- Rows here are not in the register until the integrator merges them and assigns `BUG-NNN` IDs.
- Locations are `file:line` on `main`, verified with `git show main:<path>`.

## Extension Rules

1. A lane adds `pending/<rung>.md` with the ID column set to `NEW`; it never edits `BUGS.md`.
2. After merging a file into `BUGS.md`, keep it as history.
