# docs/refactor/bugs

## Purpose

Holding area for bug and quirk rows that are not yet in `docs/refactor/BUGS.md`. A change that
finds a bug writes its row in a file under `pending/` so parallel branches never edit
`docs/refactor/BUGS.md` at the same time; the integrator folds the rows into `BUGS.md` and
assigns the real `BUG-NNN` IDs.

## Public API

- `pending/<topic>.md`: rows of one change, same columns as `docs/refactor/BUGS.md`, ID column `NEW` (deleted when folded into `BUGS.md`).

## Safety Invariants

- Locations are current `file:line`, verified in the working tree.
- A pending row never fixes anything: a fix is its own change with a test and a `BUGS.md` status.

## Extension Rules

1. One file per change in `pending/`; do not edit another change's file.
2. Once the rows are in `docs/refactor/BUGS.md`, the integrator deletes the pending file.
