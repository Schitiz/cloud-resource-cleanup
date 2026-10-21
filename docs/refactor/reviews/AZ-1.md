# AZ-1 review

## Coding summary

Rung AZ-1: `crc/azu/ip.py` is a registered `Cleaner` (`@register("azure", "ip")`), with `IP` kept as
a thin adapter. Status: complete, `make check` equivalent green (ruff, mypy strict, lint-imports,
pytest).

- Cleaner: `AzureIpCleaner` (`plan()` = `list_all` + policy, read-only; `apply()` = `begin_delete`
  in plan order). SDK behind the `IpNetworkClient` / `PublicIpOperations` Protocols; the client
  factory is injected through the constructor. Filtering: `policy.filter_tags_any_key` and
  `policy.should_skip_by_tags` (FILTER_VARIANTS.md section 3, `azu/ip.py`) over `normalize_tags`.
  No age gate exists on main, so `crc.core.age` is not used (recorded as a pending bug).
- Adapter: `IP(resource_group, dry_run, filter_tags, exception_tags, notags)` keeps `delete()`,
  `get_deleted`, `count`, `deleted_ips`, `base`, `dry_run`, `filter_tags`, `exception_tags`,
  `notags`. `delete()` iterates the lazy `list_all()` and decides and deletes IP by IP, so the call
  order (paging interleaved with `begin_delete`, one `get_network_client()` per delete), the
  mid-run error behaviour and the cumulative `deleted_ips` are those of main. `crc.py` is unchanged.
- Cleaner path: `plan()` lists and filters everything first, then `apply()` deletes. The only
  differences from main are therefore the interleaving of paging and deletes, and that a decision
  error (BUG-013 `TypeError`, a missing attribute, a paging error) now happens before any delete
  instead of after earlier deletes. Summary log lines are the same: dry run logs the "which will be
  deleted" warning from `plan()`, a real run logs the two "deleted" warnings from `apply()`.
- Tests: baseline `pytest -q` 2703 passed; now 2840 passed (+137): `tests/test_azure_ip_parity.py`
  (50 cases through the adapter, the same 50 through the registered Cleaner, 23 quirk checks, plus
  the subscription-wide/resource-group, repeated-delete and factory tests, 126 in all),
  `tests/test_azure_ip.py` (11 focused `plan()` / `apply()` tests). All existing tests unchanged.
  Oracle: `tests/legacy/azu_ip.txt` is byte-identical to `git show main:crc/azu/ip.py`.
- The module lists no regions, so there is no region fallback or auth-error case to cover.
- Ratchet: `crc/azu/ip.py` removed from ruff `extend-exclude` and the mypy override `crc.azu.ip`.
  No per-SDK mypy override was needed.
- Open issues: new bugs and quirks in `docs/refactor/bugs/pending/AZ-1.md` (8 rows, ID `NEW`).
  Existing BUG-013 is kept as is.
- ARCH-002 requires a README in every directory with files, so `docs/refactor/bugs/README.md` and `docs/refactor/bugs/pending/README.md` were added; other lanes adding the same paths will conflict on merge (keep either copy).
- Needed changes outside this lane (not made): `crc/README.md` and `tests/README.md` /
  `tests/legacy/README.md` should list `tests/legacy/azu_ip.txt`, `tests/test_azure_ip_parity.py`,
  `tests/test_azure_ip.py` and `tests/helpers_azure_ip.py`. `FILTER_VARIANTS.md` section 3: the
  `azu/ip.py` row can now cite `policy.filter_tags_any_key` and `policy.should_skip_by_tags`, and
  note that the `TypeError` for untagged IPs is kept in the cleaner (as BUG-011 for AWS), not in
  policy, so item 3 of section 7 is "kept in the cleaner, fix in a behaviour rung". No core change
  needed. `STATUS.md` and `BUGS.md` rows are for the integrator.
