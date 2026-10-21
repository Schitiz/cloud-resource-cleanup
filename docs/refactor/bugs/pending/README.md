# docs/refactor/bugs/pending

## Purpose

Bugs and quirks found by a rung that are not yet in `docs/refactor/BUGS.md`, one file per rung.

## Public API

This directory exposes no code, only the per-rung markdown files (for example `AWS-1.md`).

## Safety Invariants

- Rows keep the `BUGS.md` columns with the ID set to `NEW` and a verified `main` file:line.
- Nothing here is fixed by the rung that records it.

## Extension Rules

1. Add one `<rung>.md` per rung; never edit another rung's file.
2. When the integrator moves a row into `BUGS.md`, it removes it from here.
