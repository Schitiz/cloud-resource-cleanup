# ARCHITECTURE.md

Target architecture of the CRC Python refactor. `docs/refactor/PLAN.md` owns the
rung schedule; this file owns the rules. Modules that do not exist yet are
targets, built rung by rung.

## Layout

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

## Dependency rules

- `crc.py` -> `crc.core.engine` -> `crc.core.*`.
- Cloud packages (`crc.aws`, `crc.azu`, `crc.gcp`, `crc.oci`) depend on
  `crc.core` only and never import each other.
- `crc.core` never imports a cloud package or a cloud SDK (`boto3`, `azure`,
  `google`, `oci`). Policy and age logic are pure functions on plain data.
- Notifiers (`crc.notify`) consume the report model only.
- Enforced by import-linter (`lint-imports`, config in `pyproject.toml`). Today
  the independence contract for the four cloud packages is active. The core
  layer contract is a commented TODO until `crc/core` exists.

## Cleaner contract

```python
class Cleaner(Protocol):
    def plan(self) -> Plan: ...   # discovery and policy filtering, read-only
    def apply(self, plan: Plan) -> Result: ...  # all mutating cloud calls
```

- `plan()` makes no mutating cloud call (no delete, stop, cancel, tag write).
  It backs `--dry_run`: a dry run is `plan()` without `apply()`.
- `apply()` performs the destructive calls for items already in the plan, in
  the order required by `CLEANUP_SAFETY.md` (for example AWS spot: cancel the
  request before terminating the instance).
- Plans and results are frozen dataclasses. SDK objects do not cross the
  cleaner boundary; cleaners normalise to domain DTOs.
- SDK clients, policy and logger are injected through the constructor so tests
  pass mocks.

## Decorator registration

Cleaners self-register with a typed decorator, for example
`@register_cleaner(cloud="aws", resource="disk")`, defined in
`crc/core/registry.py`. The registry maps `(cloud, resource)` to a cleaner
factory. Rules: no `@singleton`, no hidden mutable globals beyond the registry
dict owned by the registry module, no import-time cloud calls. The engine
selects cleaners from the registry using the parsed `--cloud` / `--resource`
values.

## Legacy ratchet

Modules not yet refactored (`crc.py`, everything under `crc/`, `tests/`) are
exempt from ruff and mypy through one explicit list: ruff `extend-exclude` and
the `[[tool.mypy.overrides]]` `ignore_errors` block in `pyproject.toml`. The list
may only shrink. A rung removes the modules it refactors from both places in
the same change, and the refactored code must then pass ruff (complexity 10,
statements 40, args 6) and mypy strict. Narrow the lists as modules move;
never widen them.

## Add a resource cleaner

1. Read `CLEANUP_SAFETY.md` and the nearest existing cleaner in the same cloud.
2. Create `crc/<cloud>/<resource>.py`. Do not import another cloud package.
3. Define frozen dataclass DTOs for the candidate and the plan.
4. Implement the class with an injected SDK client and policy. Require a real
   age gate in `__init__` for destructive resources. Fail closed on missing or
   invalid age, tags or telemetry.
5. `plan()`: list, normalise, apply policy from `crc.core.policy`. No mutation.
6. `apply()`: perform the deletes or stops in the documented order, isolate
   per-resource errors only where `CLEANUP_SAFETY.md` says so, chain errors with
   `raise ... from e`.
7. Register it with `@register_cleaner(cloud=..., resource=...)`.
8. Add offline tests under `tests/` using mocks: happy path, fail-closed path,
   dry run makes no mutating call, call order for destructive sequences.
9. Update the package README and, for destructive behaviour, `CLEANUP_SAFETY.md`.
10. Remove the module from the legacy lists if it was listed, then run
    `make check`.
