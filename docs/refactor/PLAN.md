# CRC Python refactor plan

Branch: `refactor/python-agentic`. Target runtime: Python 3.11.

## Goal

Refactor the existing Python code in place into a clean codebase that AI
agents can maintain without human review, with heavy, mechanically enforced
guardrails. This is a refactor: CLI flags, environment variables and cleanup
behaviour stay the same. The Jenkins jobs in `cloud-resource-cleanup-triggers`
must keep working unchanged, including JSON-style flag values such as
`'{"days": 1}'`.

## Target architecture

```
crc.py                    thin CLI: parse flags, build config, call engine
crc/core/age.py           age parsing, positive-age checks, is-old
crc/core/policy.py        tag, notags, exception tags, regex, age, custom age tag
crc/core/registry.py      provider and cleaner registration decorators
crc/core/cleaner.py       Cleaner protocol: plan() is read-only, apply() mutates
crc/core/engine.py        selects cleaners, runs plan/apply, builds the report
crc/core/report.py        report model used by notifiers and stdout
crc/notify/slack.py       Slack sink
crc/notify/influx.py      InfluxDB sink
crc/aws|azu|gcp|oci/      one module per resource, registered by decorator
```

Dependency direction: `crc.py` -> `crc.core.engine` -> `crc.core.*`; cloud
packages depend on `crc.core` only; cloud packages never import each other;
`crc.core` never imports a cloud package or cloud SDK. Enforced by
import-linter.

## Guardrails (from guardrail Option D, adapted to Python)

- `AGENTS.md` (short map), `CLAUDE.md` symlink, `ARCHITECTURE.md`.
- Ruff with `UP`, `FURB`, `SIM`, `PERF`, `B`, `C901`, `PLR` and target
  `py311`; mypy strict on refactored packages.
- import-linter contracts: layers, cloud independence, core forbids SDKs.
- `tests/archtest/`: README in every package with required sections and
  symbol sync, read-only `plan()`, bans on ad hoc `re` / `datetime.now` /
  `os.environ` in cloud packages, file and function size limits, safety
  test hash lock tied to `SAF-xxx` IDs in `CLEANUP_SAFETY.md`.
- Legacy ratchet: modules not yet refactored are listed in one allowlist and
  exempt from the new checks. Each rung removes the modules it refactors.
  The allowlist may only shrink.
- `.github/CODEOWNERS` requires the owner for guardrail files.
- Project skill `.cursor/skills/crc-python-refactor/` built from
  `docs/refactor/SKILL_SELECTION.md`.

## Rungs

Each rung is one Cursor Cloud Agent run that must finish in under 25
minutes, followed by one review run. Every rung must leave
`pytest`, `ruff check`, `lint-imports` and `mypy` green.

| Rung | Scope |
|------|-------|
| R0a | Tooling and docs: pyproject, dev requirements, Cursor environment, AGENTS.md, CLAUDE.md, ARCHITECTURE.md, CODEOWNERS, Cursor rules, project skill, Makefile `check` |
| R0b | `tests/archtest` with legacy allowlist, SAF IDs in CLEANUP_SAFETY.md, CI workflow |
| R1 | `crc/core/age.py`, `crc/core/policy.py` with tests (not wired) |
| R2 | registry, Cleaner protocol, engine, report (not wired) |
| R3 | move Slack and Influx into `crc/notify` |
| R4+ | one resource per rung: AWS keypair, AWS elastic IP, AWS KMS, AWS VPC, AWS snapshot, AWS VM, AWS disk, AWS spot requests (2-3 rungs), Azure, GCP, OCI |
| CLI | `crc.py` becomes thin wiring over the engine; flags unchanged |
| Final | remove legacy allowlist, lock all safety tests, README symbol sync everywhere |

Behaviour fixes (fail closed on missing age, no `MAX_AGE` env mutation, the
three Azure VM bugs) come after the refactor as separate rungs.

Progress is logged in `docs/refactor/STATUS.md`. Reviews go to
`docs/refactor/reviews/<rung>.md`.
