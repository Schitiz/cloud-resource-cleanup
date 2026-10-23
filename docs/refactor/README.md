# docs/refactor

## Purpose

The bug register of CRC. The refactor itself is finished and its history is in
`docs/archive/`; this directory keeps only the register and the holding area for new rows.

## Public API

- `BUGS.md`: `BUG-NNN` rows, IDs never reused, rows never deleted (only their status changes).
  ARCH-009 requires every `BUG-NNN` in `crc/` and `tests/` to have a row here.
- `bugs/`: holding area for rows written by parallel agents, see `bugs/README.md`.

## Safety Invariants

- A bug is recorded as a row, then fixed in a PR that names its ID (see `AGENTS.md`).
- Documented locations must match the code; verify before writing a row.

## Extension Rules

1. Append a row with the next free ID, the current `file:line`, the risk and a status.
2. When a PR fixes a row, set its status to `fixed in <PR>`; keep the row.
