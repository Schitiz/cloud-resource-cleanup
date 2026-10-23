# FIX-AWS-EIP review (wave FIX-1)

## Coding summary

- Bug fixed: `BUG-011`. `ElasticIpCleaner._should_skip` (`crc/aws/elastic_ips.py`) no longer raises
  `TypeError("'bool' object is not iterable")` when `notags` is set. It now uses the same
  semantics as AWS VMs (`crc/aws/vm/cleaner.py`): exception tags (any key, tag by tag, first
  hit returns) still skip first; otherwise all tags are collected and `policy.notags_all`
  decides, so an address is kept (skipped) when every notags key matches (an empty value list
  means "key present"). An address with an empty tag list is not skipped by notags. A tag without
  `Key` or `Value` raises `KeyError` while `notags` is set (fail closed, before any release,
  as for VMs). With `notags` empty or `None` nothing changes: same calls, order, logs, errors.
- Production: neither Jenkins command passes `notags`, so their selection is unchanged.
- Bugs left: none in scope. `BUG-053` (age) is not in this rung.
- Files changed: `crc/aws/elastic_ips.py`, `crc/aws/README.md` (Elastic IP safety note),
  `tests/test_aws_ip_parity.py` (4 cases marked `diverges="BUG-011"`, new-outcome table,
  `_should_skip_instance` divergence table; every other case still equals the oracle),
  `tests/test_aws_elastic_ips.py` (the `TypeError` test replaced by a fixed-behaviour test),
  new `tests/test_aws_elastic_ips_fix.py` (9 tests), this file. Oracle `tests/legacy/aws_elastic_ips.txt`
  and hash-locked tests untouched.
- Direction rule: the fix turns a run that failed on every tagged, unfiltered-out address into
  one that skips addresses matching notags and releases the others. This follows the owner's task
  text ("keeps addresses as the other AWS cleaners do"). Addresses matching notags are kept; the
  run no longer aborts, so addresses that are not kept by notags and match the filter are now released
  where `main` stopped with an error (only reachable with `notags`, which production never passes).
- Tests: `pytest -q` 42444 collected at 182466d, 42454 passed after (+10). `make check` green.
- Owner actions: none (no locked test or `CLEANUP_SAFETY.md` change needed).

## Owner decision

None.

## Owner action

None.

## New bugs

- `docs/refactor/FILTER_VARIANTS.md` (line 33) and the `crc/core/policy.py` docstring of
  `aws_eip_should_skip` still say notags never skips / raises for Elastic IPs. Both are outside this
  rung's files; the driver or a docs rung should update them. Exists on main: the docs yes (stale
  after this fix only).

## Round 1 (Argon)

### Findings

1. **(1) Bug fix (`BUG-011`)**: `ElasticIpCleaner._should_skip` (`crc/aws/elastic_ips.py:193-204`) now collects `all_tags[tag["Key"]] = tag["Value"]` when `self._notags` is truthy (after checking `self._exception_tags` tag by tag as before) and evaluates `policy.notags_all(all_tags, self._notags or {})`, matching `crc/aws/vm/cleaner.py` semantics. Verified with unit tests in `tests/test_aws_elastic_ips_fix.py` and `tests/test_aws_ip_parity.py` that fail on `182466d` and pass now.
2. **(2) Direction rule & parity tests**: When `notags` is empty or `None`, `if self._notags:` does not execute, so every SDK call, call order, selection, log line, stdout and exception matches the frozen oracle `tests/legacy/aws_elastic_ips.txt` (untouched). In `tests/test_aws_ip_parity.py`, tightened `DIVERGED` from boolean predicates to exact `Outcome` instances (asserting `calls`, `deleted`, `count`, `logs`, `stdout`, and `error`) for all 4 `diverges="BUG-011"` cases across both `test_matches_main` and `test_cleaner_protocol_matches_main`.
3. **(3) Production Jenkins commands**: Neither production command passes `--notags`; added `test_production_jenkins_filter_tags_selection_unchanged` in `tests/test_aws_elastic_ips_fix.py` pinning both Jenkins `filter_tags` payloads.
4. **(4) Fail-closed paths**: Malformed tag dicts missing `"Key"` or `"Value"` when `notags` is set raise `KeyError` during `plan_region` before any `release_address` call.
5. **(5) Protected files**: `tests/archtest/safety_lock.json`, the 5 locked safety test files, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, and `CLEANUP_SAFETY.md` are untouched.
6. **(6) Package README**: `crc/aws/README.md` Safety Invariants updated for `BUG-011` (`ARCH-002` passes).
7. **(7) Unfixed bugs**: None in scope (`BUG-053` is explicitly out of scope for this rung).

### Gates & Test Count

- `ruff check .`: clean
- `mypy`: clean (`Success: no issues found in 229 source files`)
- `lint-imports`: `8 contracts kept, 0 broken`
- `pytest -q`: `42456 passed` (42444 on `182466d`, +12 net)

VERDICT: APPROVE

