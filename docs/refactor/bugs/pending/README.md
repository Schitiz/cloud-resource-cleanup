# docs/refactor/bugs/pending

## Purpose

One file per parallel rung (for example `OCI-1.md`) listing new bugs and quirks that the
integrator moves into `docs/refactor/BUGS.md`.

## Public API

This directory exposes no library, only documents.

## Safety Invariants

- Rows describe current behaviour on `main`; they never change code behaviour.
- A row is removed from here only when it has been copied into `docs/refactor/BUGS.md`.

## Extension Rules

1. Keep the `BUGS.md` columns; set the ID column to `NEW`.
2. Cite `main` file:line verified with `git show main:<path>` and name the parity case that pins it.
