# AG-DOCS review

## Coding summary

Lane AG-DOCS (branch `ag/docs`): every live doc now describes the current code, and ARCH-011
checks that.

- Routed: nothing in the code changed. Every pair already runs through `crc.core.engine`; the
  docs now say so. No adapter was deleted or shimmed by this lane (AG-ADAPT owns that).
- Deleted-code descriptions removed: `dispatch.HANDLERS`, `crc/cli/vm_ops.py`,
  `resource_ops.py`, `notify.py`, `CRC.delete_*`, `AWS_Disk`, `GCP_Disk`, the "kinds being moved
  to the engine" text in `AGENTS.md`, `ARCHITECTURE.md` (run-flow diagram; add-a-cleaner steps
  6-8 now name args choices, `constants.RESOURCES`, `pairs.py`, routes, `KIND_LABELS`, tests and
  the CLI parity tests to extend), `CLEANUP_SAFETY.md` (SAF-004, SAF-005, SAF-018, SAF-021,
  SAF-022, the engine-path note, the module map), `crc/cli/README.md`, `.cursor/rules`,
  `.cursor/skills` and `tests/legacy/README.md`. Every SAF rule is kept and numbered as before.
- BUG-004: the KMS (`crc/aws/README.md`), Azure disk, GCP disk and `is_old_enough`, and OCI disk
  README lines now say a present but bad custom age tag keeps the resource (`KEEP_AGE`).
  `crc/core/README.md` marks `gcp_ip_exception_excludes` and `nic_name_included` as dead helpers
  (BUG-370), and no longer lists the inverted GCP IP exception as a current quirk.
- One bug-location rule, worded the same in `AGENTS.md`, the `BUGS.md` header, rules 1-2 of
  `BUGS.md`, `docs/refactor/README.md`, `docs/refactor/bugs/README.md`, `bugs/pending/README.md`,
  `fix-bug.md`, the package READMEs and the ARCH-009 remediation: a new row cites the current
  `file:line` in `crc/`; an old row keeps its main location. `BUGS.md` header and notes links
  now point to `docs/archive/`. No `BUGS.md` row was edited.
- `AGENTS.md` (112 lines, within ARCH-010): measured timings (4-core VM, warm caches:
  `make check-fast` 24 s, `make check` 61 s), "never hand-edit `test_count_floor.txt`
  (`make raise-test-floor` only)", which failures print `REMEDIATION:` (archtest) and which do
  not (ruff, mypy, import-linter, plain tests), the flag workflow now states that
  `tests/test_cli_args_parity.py` compares flag for flag against the oracle. The rule numbers in
  the ARCH-007 remediation are now "rules 3 and 7" and the ARCH-009 remediation cites rule 5.
- ARCH-011 (`tests/archtest/doc_links.py`) now scans every `.md` and `.mdc` file recursively
  except `docs/archive/**`, symlinks and cache directories, and checks backticked repo-relative
  paths under `crc/`, `tests/`, `docs/`, `.cursor/`, `.github/` (a path must exist; a glob or
  `<placeholder>` must match at least one path; `:line`, `::test` and `#anchor` suffixes are
  dropped). Eight self-tests were added or reworked. Historic paths are written `main:<path>`
  (`tests/legacy/README.md`).
- Test count: before 44,415 (floor 44,415); after 44,421; floor raised with
  `make raise-test-floor`. `make check` is green.

## Owner action

- None required for the guardrail files. Decision for the owner: ARCH-011 skips the whole table
  rows of `docs/refactor/BUGS.md` for the backticked-path check, not only the "Location on main"
  column, because the title and notes cells of old rows also name files that exist only on
  `main` (for example `crc/oci/spot_vm.py`, `crc/cli/notify.py`) and rows may not be edited.
  The header and footer of `BUGS.md` are checked. Links are checked everywhere.

## What is left

- `crc/aws/vm`, `crc/azu/vm`, `crc/oci/vm` READMEs and the VM lines of `crc/gcp/README.md` (AG-ADAPT)
  still say the age tag "fails open" (`crc/azu/vm/README.md:47`, `crc/aws/vm/README.md:46`,
  `crc/oci/vm/README.md:39`) and `crc/oci/vm/README.md:53` still has the old bug-location text.
- The Spot and disk adapter classes (`SpotVM`, `SpotInstanceRequests`, `Disk`, `VM`) still exist
  in the code, so their READMEs still describe them; they need a pass when AG-ADAPT deletes or
  shims them.
- `tests/test_cli_args_parity.py`, `test_cli_main_parity.py` and `test_core_selection.py` fail
  for an added flag or resource (AGENTS.md says so now); an additive-flag allowance is a code
  change outside this lane.

## New bugs

- None found. (Doc-only drift fixed above; no new `BUGS.md` rows.)
