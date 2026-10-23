# FIX-AZU-NIC review

## Coding summary

Rung FIX-AZU-NIC (wave FIX-1), branch `fix/azu-nic`. Status: complete; `make check` green.

- Bugs fixed: `BUG-111` and `BUG-122` (the NIC listing is now `network_interfaces.list(resource_group)` with
  `Base.resource_group`, so nothing outside the configured group is listed or deleted and a "deleted" NIC
  can no longer be a no-op 204 on a missing resource); `BUG-113` (`name_regex` / `exception_regex` entries are
  regexes matched with `re.search`; patterns are compiled by `policy.compile_patterns` before any SDK call and
  an invalid one raises `ValueError`; an empty-string `name_regex` entry is ignored); `BUG-114` (a NIC with
  `virtual_machine`, `private_endpoint` or `private_link_service` set is kept, skip reason `in_use`;
  the two new attributes are read with `getattr(..., None)`).
- Bugs left: none of the four. See "Owner decision" for two deliberate deviations inside `BUG-113`.
- Files changed: `crc/azu/nic.py`, `crc/azu/README.md` (NIC Safety Invariants), `tests/test_azure_nic_parity.py`,
  `tests/test_azure_nic.py`, `tests/test_azure_logger.py` (one expected skip slug), `tests/helpers_azure_nic.py`
  (fake gets `list(resource_group_name)`), new `tests/test_azure_nic_fix.py`. No hash-locked test touched.
- Tests: `pytest -q` 42444 passed at 182466d, 42459 passed now (+15). `make check` green.
- Parity tests: the oracle's `list_all()` is mapped to `list(<group>)` (`_normalised`) so every unmarked case still
  asserts equal calls, results, logs and errors. Cases that trigger `BUG-113` are in `DIVERGING`: each asserts
  that the oracle still shows the old behaviour and asserts the exact new outcome (adapter and registered
  `Cleaner` path). The nine buggy quirk checks moved from `QUIRKS` into `DIVERGING`.
- Owner actions: none.

## Owner decision

- `exception_regex` empty-string entry: the contract says an empty entry is ignored. For `exception_regex` that
  would delete NICs that main keeps (`[""]` excludes every NIC today), which breaks the direction rule. It
  therefore raises `ValueError` before any SDK call (fail closed). `name_regex` empty entries are ignored as
  specified (an all-empty `name_regex` logs "No Azure NICs to delete." and lists nothing).
- `exception_regex` also keeps a NIC whose name contains the entry as a literal substring (`re.search(p)` or
  `p in name`), so a regex-special entry that main matched literally (`^nic` against `x^nic-a`) still excludes it
  and the fix never deletes a NIC main kept. For `name_regex` only `re.search` applies.
- A bare string instead of a list (main iterated it character by character) and non-string entries raise
  `ValueError` (fail closed). The CLI always passes a JSON list, so production is unaffected.
- `NIC.virtual_machine` is still read directly (a NIC object without the attribute raises `AttributeError` as
  today instead of being treated as free); only `private_endpoint` and `private_link_service` default to `None`.
- The NIC listing is still requested twice (`BUG-117`, not in scope); only its call changed.

## Production command check

`--resource nic --name_regex '["yb-itest", "yb-itests", "ui-auto"]'`: the values have no metacharacters, so
`re.search` selects exactly the same NICs as the substring test (`test_production_values_select_the_same_nics_BUG_113`).
The only call difference is `list(resource_group)` instead of `list_all()`. The skip count in the run log for
attached NICs is now `reason=in_use` (was `reason=attached`), log text only.

## New bugs

- `crc/core/policy.py` `nic_name_included` / `nic_name_excluded` (plain-substring helpers) are no longer used by
  `crc/azu/nic.py`; they are only exercised by `tests/test_core_policy.py` (dead code, exists on main: no, it was
  added by the refactor). Not removed here because `crc/core/` is outside this rung.
- `docs/refactor/BUGS.md` `BUG-118` (non-string `exception_regex` entry raising `TypeError` only when evaluated)
  is now a `ValueError` before any SDK call as a side effect of `BUG-113`; the `None`-name `TypeError` is kept.
