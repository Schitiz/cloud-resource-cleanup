# docs/refactor/bugs

## Purpose

Staging area for bugs and quirks found by parallel refactor lanes. Each lane records its findings
in `pending/<rung>.md` instead of editing `docs/refactor/BUGS.md`; the integrator merges them.

## Public API

This directory exposes no code. Its only content is `pending/`, one markdown file per rung.

## Safety Invariants

- Do not fix a bug here: this is a register, not a fix. Behaviour fixes are separate rungs.
- Every row cites a `file:line` on `main`, verified with `git show main:<path>`.

## Extension Rules

1. One file per rung, named after the rung (for example `AWS-1.md`), in `pending/`.
2. Use the columns of `docs/refactor/BUGS.md` and set the ID column to `NEW`.
3. The integrator assigns `BUG-nnn` ids when moving rows into `BUGS.md`.
