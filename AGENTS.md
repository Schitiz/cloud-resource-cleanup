# AGENTS.md

`CLAUDE.md` is a symlink to this file. Read this first; it is the map and the rules that no
check enforces. Detail lives one hop away.

## What this repo is

`cloud-resource-cleanup` (CRC) is a synchronous Python 3.11 CLI that Jenkins runs to stop and
delete leftover test resources on AWS, Azure, GCP and OCI. Entry point `crc.py`; the code is in
`crc/`. It deletes real resources, so safety beats elegance. Jenkins jobs in the
`cloud-resource-cleanup-triggers` repo call `python crc.py <flags>`: every flag, environment
variable and JSON-style value (`--age '{"days": 1}'`) must keep working.

## Commands

```
pip install -r requirements.txt -r requirements-dev.txt   # once; Python 3.11 (CI) or newer
make check-fast            # lint + tests minus the three slow CLI parity files, about 25 s
make check                 # everything CI runs, about 60 s; green before every commit
make lint                  # ruff, mypy, lint-imports only
make test-file F=tests/test_x.py     # one file while iterating
make raise-test-floor      # after adding tests, raises the floor (never lowers it); never edit the file by hand
```

Timings measured on a 4-core VM with warm caches: `make check-fast` 24 s (about 14,060 tests),
`make check` 61 s (44,421 tests; the three slow parity files hold about 30,000 of them).

Edit, `make test-file`, `make check-fast`, then `make check` once before you commit. A failing
archtest check (ARCH-001..011, SAF-LOCK, the test-count floor) prints its rule ID, `file:line`
and a `REMEDIATION:` paragraph: follow it. Failures of ruff, mypy, import-linter and ordinary
tests print no `REMEDIATION:`; read the tool's own message. Rule IDs are listed in
[tests/archtest/README.md](tests/archtest/README.md); do not restate or bypass them.
`make check-fast` skips the test-count floor check; only `make check` runs it.

## Map

| Path | What is there |
|------|---------------|
| `crc.py` | Thin entry point; re-exports `crc/cli` so `python crc.py` works |
| `crc/cli/` | Flags (`args*.py`), validation, `main()`, dispatch, engine bridge (`bridge.py`), route tables (`routes/<cloud>.py`) |
| `crc/core/` | Engine, registry, `Cleaner` protocol, report, pure policy and age code, run log |
| `crc/<cloud>/<kind>/` | Cleaners per cloud (`aws`, `azu`, `gcp`, `oci`), one package per resource kind |
| `crc/notify/` | Slack and InfluxDB sinks that consume the report |
| `tests/` | Offline pytest; `tests/archtest/` mechanical checks; `tests/legacy/` frozen oracles (read-only) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layers, run flow, Cleaner contract, add-a-cleaner guide |
| [CLEANUP_SAFETY.md](CLEANUP_SAFETY.md) | Destructive-cleanup invariants (`SAF-NNN`); authoritative for safety |
| [docs/logging.md](docs/logging.md) | Run-log line formats and rules |
| [docs/refactor/BUGS.md](docs/refactor/BUGS.md) | Register of known bugs (`BUG-NNN`); `docs/refactor/bugs/` holds pending rows |
| [docs/archive/](docs/archive/) | Archived history; read only when a bug row sends you there |
| `crc/**/README.md` | Per-package purpose, public API, safety invariants; read the one you edit |

Skills (task playbooks): [implement](.cursor/skills/crc-maintain/SKILL.md) for any change,
[review](.cursor/skills/crc-maintain/review.md) for a PR, [fix a bug](.cursor/skills/crc-maintain/fix-bug.md).

## Rules no check enforces

1. Never call a real cloud API or use real credentials. Tests mock every SDK client. Reason with
   `--dry_run`, never run the CLI against an account.
2. Fail closed: when age, tags, telemetry or a listing are uncertain, keep the resource and
   raise or skip; never delete on a guess.
3. Never delete, skip, xfail or loosen a test. Add or strengthen only. Never edit
   `tests/legacy/*.txt`, `tests/archtest/*.json` or run the `update_*.py` scripts; never
   hand-edit `tests/archtest/test_count_floor.txt` (`make raise-test-floor` is the only way it
   changes). If a fix needs a locked test changed, stop and put the proposed change in the PR
   description for the owner.
4. Keep the `CLEANUP_SAFETY.md` rules true. When behaviour of a destructive path changes, update
   that file in the same PR; never remove, weaken or renumber a `SAF-NNN` rule.
5. Do not widen scope. A bug you notice on the way becomes a row in `docs/refactor/BUGS.md`
   (next free ID), not an unrelated change; a new row cites the current `file:line` in `crc/`,
   while old rows keep their `main` location. Fix it in its own PR that names the `BUG-NNN`.
6. Keep destructive call order and per-resource error isolation as `CLEANUP_SAFETY.md` says;
   do not catch broad `Exception` silently, chain errors with `raise ... from e`, add no retry
   layer over SDK retries.
7. Do not add dependencies or edit `requirements*.txt`, `pyproject.toml` limits or import-linter
   contracts to make code pass; fix the code.
8. Docs that contradict code are bugs: fix the doc in the same PR, state only what the code does.

## Workflow: fix a bug

1. Find the row in `docs/refactor/BUGS.md` (or add it). An old row's location column cites
   `main` lines that have moved or are gone; grep the ID, which also appears in package READMEs
   and tests.
2. Write a failing offline test for the bug first, in the cleaner's test file.
3. Fix it toward `CLEANUP_SAFETY.md` (fail closed). Mark the row `fixed in <PR or commit>`; keep it.
4. `make check`. PR title names the ID. More in [fix-bug.md](.cursor/skills/crc-maintain/fix-bug.md).

## Workflow: add or change a cleaner

Every `(cloud, kind)` pair runs through `crc.core.engine`: `crc/cli/routes/<cloud>.py` maps flags
to cleaner options, the cleaner in `crc/<cloud>/<kind>/` implements `plan()` (read-only) and
`apply()` (mutating) and registers with `@register`. Follow the numbered guide in
[ARCHITECTURE.md](ARCHITECTURE.md#add-a-cleaner). Update the package README and, for a
destructive change, `CLEANUP_SAFETY.md`.

## Workflow: change a CLI flag (triggers-repo contract)

Flags are an external contract. Never rename, remove, re-type or change the default or meaning of
an existing flag, choice or value form. A new flag must be optional with a default that keeps
today's behaviour. Before any change, search the `cloud-resource-cleanup-triggers` repo
(`Jenkinsfile` and job definitions) for the flag with `gh search code` or a clone; if you cannot
see that repo, treat every flag as in use. Edit the matching `_add_*_args` group in
`crc/cli/args.py` or `args_run.py`. `tests/test_cli_args_parity.py` asserts the parser equals the
frozen oracle `tests/legacy/crc_main.txt` flag for flag, so a new flag fails it until that test
gains an allowance for additions that still compares every existing flag; never touch the oracle.
State in the PR which trigger jobs are affected (or "none, additive").

## How to review a PR

Use [review.md](.cursor/skills/crc-maintain/review.md). In short: run `make check`, read the diff
against the rules above and `CLEANUP_SAFETY.md`, confirm each new behaviour has an offline test
that fails without it, confirm no guardrail file changed, and confirm the PR names its `BUG-NNN`
or states why none applies.
