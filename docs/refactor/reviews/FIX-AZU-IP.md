# FIX-AZU-IP review

## Coding summary

Rung FIX-AZU-IP (wave FIX-1), branch `fix/azu-ip`. Status: complete.

- Bugs fixed: `BUG-074`, `BUG-013`, `BUG-077`, `BUG-076`.
  - BUG-074: `AzureIpCleaner.list_ips()` calls `public_ip_addresses.list(resource_group)` with
    `Base.resource_group` instead of the subscription-wide `list_all()`. Nothing outside the
    configured group is listed or acted on; the group is not derived from the listed resource.
    An empty resource group raises `ValueError` before any SDK call (fail closed).
  - BUG-013 / BUG-077: an untagged IP (`tags is None`) is an IP with no tags in the exception and
    notags checks, so it never raises. Earlier deletes are no longer followed by a `TypeError`.
    The filter check is unchanged (an untagged IP never matches a non-empty `filter_tags`).
  - BUG-076: an IP is kept (skip reason `in_use`) when `ip_configuration`, `nat_gateway`,
    `linked_public_ip_address` or `service_public_ip_address` is set; the four fields are read
    with `getattr(ip, field, None)`, so SDK models without a field still work.
- Bugs left: none.
- Files changed: `crc/azu/ip.py`, `crc/azu/README.md` (Safety Invariants / quirk notes),
  `tests/helpers_azure_ip.py` (fake gets `list(resource_group_name)`),
  `tests/test_azure_ip.py`, `tests/test_azure_ip_parity.py` (diverging cases marked with their
  bug ID in `DIVERGING`, oracle call `list_all` mapped to `list(group)`, all other cases still
  equal to the oracle), `tests/test_azure_logger.py` (the ip skip line is now
  `reason=in_use` instead of `reason=attached`), new `tests/test_azure_ip_fix.py`.
- Test count (`pytest --collect-only`): 42444 before (182466d), 42455 after (+11).
- Owner actions: none (no locked test, no `CLEANUP_SAFETY.md` change needed).

Notes for reviewers:

- Parity: every case lists `("list", group)` instead of `("list_all",)`, mapped in `_scoped`.
  Seven cases diverge on purpose and assert the new outcome plus that it differs from the
  oracle: `untagged-with-exception-raises`, `untagged-with-notags-raises`,
  `untagged-raises-in-dry-run` (BUG-013), `untagged-raises-even-if-filter-excludes`,
  `untagged-raises-after-earlier-deletes` (BUG-077),
  `untagged-with-exception-attached-ip-still-raises` (BUG-013, still kept as `in_use`) and
  `missing-ip-configuration-attribute` (BUG-076, `getattr` default).
- The `ip_configuration` skip reason changed from "attached to an IP configuration" (slug
  `attached`) to `in_use`, as the task asks. Only the skip count line and `Skipped.reason` change.
- Direction rule: the selections that change are inputs that used to abort the run
  (untagged IPs with exception/notags, a model without `ip_configuration`) and the listing
  scope (fewer resources are reachable). Production commands (`--cloud azure --resource_group
  "$RESOURCE_GROUP" --resource ip --filter_tags ...`) keep the same flags. With `--filter_tags`
  set, untagged IPs are still never selected.

## Owner decision

None.

## New bugs

- `crc/azu/ip.py` `decide()`: `filter_tags` with a string value (not a list) matches by
  substring (`tag in "testing"`), and a tag value of `None` with a string spec raises
  `TypeError` (covered by parity quirks `string-spec-value-matches-substring` and
  `tag-value-none-with-string-spec-raises`; exists on main: yes). Not fixed.
- `crc/azu/ip.py` `decide()`: no age gate; an empty `filter_tags` selects every unused IP of the
  group, including untagged ones (SAF-011; exists on main: yes). Already recorded in the README.
