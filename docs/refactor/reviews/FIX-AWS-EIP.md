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
