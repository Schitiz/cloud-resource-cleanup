# docs/refactor/bugs

## Purpose

Holding area for bugs and quirks found by parallel refactor lanes before they are merged into
`docs/refactor/BUGS.md`. Each lane writes one file under `pending/`.

## Public API

This directory exposes no library, only documents.

## Safety Invariants

- Nothing here fixes a bug: rows only record what `main` does today, with its `main` file:line.
- `docs/refactor/BUGS.md` stays the single register; pending rows move there with a real ID.

## Extension Rules

1. Add rows to `pending/<rung>.md` with the same columns as `BUGS.md` and the ID set to `NEW`.
2. Verify every location with `git show main:<path>` before adding it.
