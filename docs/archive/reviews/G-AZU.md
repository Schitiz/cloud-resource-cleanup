## Coding summary

Lane G-AZU (owner-approved behaviour fixes, branch `gb/azu`). No new kind was routed and no
adapter was deleted or shimmed in `crc/`; the Azure disk, ip and nic cleaners were already
routed through `crc.core.engine`.

- BUG-173 (Azure disk): `build_disk_cleaner` calls `crc.azu._common.real_run_age`, which raises
  `ValueError("Azure disk cleanup requires a positive --age on a real run: ...")` before any
  cloud call when the run is not `--dry_run` and `--age` is missing, empty, zero or malformed.
  Dry runs keep working without an age.
- BUG-075 (Azure IP) and BUG-112 (Azure NIC): same requirement in `build_ip_cleaner` and
  `build_nic_cleaner`; the routes (`crc/cli/routes/azu.py`) now pass `options.age` (only when
  given, so a dry run without `--age` hands the cleaner the same options as before).
  With an age, the new `crc/azu/_created.py` (`AgeGate`) reads creation times from
  `azure-mgmt-resource` (`ResourceManagementClient(credential, subscription_id).resources
  .list_by_resource_group(group, filter="resourceType eq 'Microsoft.Network/...'",
  expand="createdTime")`), built from the same `Base` credential (`Base.get_resource_client`),
  one call per run and type, ids matched case-insensitively. A resource with no creation time,
  a younger one, or every resource when the lookup fails (logged as an error) is kept, with
  skip reasons `no creation time`, `not older than the age threshold`,
  `creation time lookup failed`. Ages are compared with `crc.core.age.is_old`.
- Dependencies: `azure-mgmt-resource` added to `requirements.txt`; `constraints.txt` pins
  `azure-mgmt-resource==24.0.0` and its dependency `azure-common==1.1.28`;
  `tests/archtest/frozen_inputs.json` regenerated with `update_frozen_inputs.py`. No mypy
  override was needed (`azure.*` is already covered).
- Docs: `CLEANUP_SAFETY.md` SAF-011 now records that Azure disk, ip and nic meet it; READMEs of
  `crc/azu` and its disk, ip and nic packages updated; BUGS.md rows BUG-075, BUG-112 and
  BUG-173 are "fixed in G-AZU" and their `TODO(BUG-NNN)` comments are removed. The BUGS.md
  summary count line was not edited.
- Tests: new `tests/test_azure_age_required_fix.py` (20 tests; 19 fail without the `crc/` change,
  the 20th pins the unchanged disk age gate). Test count before: 44,674 collected (the floor); after: 44,694 collected (44,693 passed, 1 skipped); floor raised with `make raise-test-floor`.
- How the CLI and parity tests reach the cleaners: the frozen-oracle parity tests and the CLI
  bridge test run real (non dry-run) cases with no age, which the factories now refuse. They load
  the autouse fixture `tests/helpers_azu_age_shim.py`, which passes the `age` option through
  unchecked and treats every IP and NIC as old enough, so the cleaner logic stays pinned to the
  oracle; the refusal and the creation-time gate are tested without the shim in the new file.
  No parity case was edited and no oracle changed, so no case is marked as diverging.

### Owner actions

- Merge with Lane G-AWS: the 47-command fixture and its expected outcomes must carry
  `--age '{"days": 1}'` for Azure IP x2 and Azure NIC (triggers repo `crc/require-age`). With the
  current fixture `tests/test_jenkins_contract.py` still passes because the routes omit `age`
  when it is not given; with the new fixture the expected options include `age`.
- The service principal used by Jenkins needs read access to generic resources of the resource
  group (`Microsoft.Resources/subscriptions/resources/read`, normally included in Reader).
  Without it the lookup fails and every Azure IP and NIC is kept (fail closed).
- Review the shim approach for the parity tests (above); an alternative is to give each parity
  case an age and a fake resource client.

### New bugs

None found.
