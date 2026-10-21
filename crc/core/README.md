# crc.core

## Purpose

Pure building blocks shared by every cloud package. `crc.core.age` holds the age-gate
logic moved out of `crc/service.py` without behaviour change: validating `--age` values,
reading custom age tags, and deciding whether a resource is old enough. Cleaners fetch
and normalise; this layer decides. Policy (tag and regex filtering) is a later rung.

## Public API

An age spec is a dict with days and/or hours integer values.

- `AgeSpec`: type alias for the days/hours dict.
- `AGE_KEYS`: the allowed age keys, days and hours.
- `require_positive_age()`: normalise an int or dict age, raise ValueError when it is empty, malformed, negative, overflowing or zero.
- `lookup_custom_age_tag()`: return whether the custom age tag is present, and its raw value, for AWS list tags or dict tags.
- `validated_retention_age()`: fail-closed custom age tag parse; None when the tag is absent, ValueError when present but empty, unparseable or invalid.
- `parse_literal()`: parse a tag value with ast.literal_eval, logging and returning None on error.
- `get_retention_age()`: fail-open custom age tag parse; None when absent, empty or unparseable.
- `get_min_age()`: return the shorter of two age specs; ties return the second.
- `is_old()`: True when the resource is at least as old as the age; an empty age returns True; the MAX_AGE environment variable can replace a longer age.

## Safety Invariants

- `is_old` with an empty age matches every resource (SAF-006). Destructive callers must
  reject empty ages first with `require_positive_age`.
- Custom age tags: callers that must fail closed use `validated_retention_age`; callers
  using `get_retention_age` alone fail open to `--age` (SAF-008, SAF-009). Do not change
  either in a refactor rung.
- `MAX_AGE` can still shorten a floor inside `is_old`, including to zero (SAF-010).
  Never add another place where it shortens a floor set by another flag.
- This package never imports `crc.aws`, `crc.azu`, `crc.gcp`, `crc.oci`,
  `crc.notifications`, `crc.service` or any cloud, Slack or Influx SDK
  (import-linter contracts in `pyproject.toml`).
- Log messages are part of the behaviour; keep them identical.

## Extension Rules

1. Keep modules pure: typed plain functions, no SDK calls, no clock reads. The only
   environment read is `MAX_AGE` in `is_old`; moving it to the caller is a later rung.
2. Declare every public name in `__all__` of `__init__.py` and list it under Public API.
3. Add table-driven tests under `tests/` for every branch, and never weaken them.
4. Do not edit the import-linter contracts to make an import pass.
