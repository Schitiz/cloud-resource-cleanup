## Coding summary

Lane G-AWS (branch `gb/aws`): owner-approved behaviour fixes for AWS VM age, the removal of `--resource vpc`, two bug rows closed without a code change, and the refreshed Jenkins contract.

**Routed.** Every other AWS kind keeps its route. The `vpc` route is gone (`crc/cli/routes/aws.py`), as is its `Kind` in `crc/core/kinds.py`. Nothing stays on a legacy path.

**Adapters deleted or shimmed.** `crc/aws/vpc/` is deleted (cleaner, client, delete, runtime, teardown, README). No shim: `--resource vpc` is now an argparse invalid choice (exit 2, `argument -r/--resource: invalid choice: 'vpc' (choose from ...)`). `tests/legacy/aws_vpc.txt` is untouched and only bound by the `crc_main.txt` oracle loader (`ADAPTER_ORACLES`); the owner retires it.

**Fixes.**
- BUG-213 (AWS VM): `build_vm_cleaner` raises `ValueError` naming `--age` for a real run (not `--dry_run`, delete and stop) without a positive age, before any cloud call, using `crc.core.age.require_positive_age`. A custom age tag key may stand in for the age: then an instance without that tag is kept (`VmSettings.require_age`, skip reason `no age`). Dry runs keep working without an age (the Jenkins `-d` reports). Tests: `tests/test_aws_vm.py` (`test_bug_213_*`), `tests/test_aws_vm_parity.py` (`test_bug_213_real_run_without_a_positive_age_raises_before_any_cloud_call`; the oracle case `age-empty-matches-all` is kept as a dry run, where it still matches the oracle). CLEANUP_SAFETY.md SAF-011 notes the AWS VM is met; the README of `crc/aws/vm` is updated; the TODO is removed; row marked `fixed in G-AWS`.
- BUG-083 (vpc removal): kind, route, package, tests and parity cases deleted. New `RemovedResource` / `REMOVED_RESOURCES` table next to the ADDED tables in `tests/helpers_ag_cli_added.py`; `tests/helpers_ag_cli_args.py` lets the oracle's `vpc` choice be absent only when it is listed (an unlisted removal fails with a pointer to the table), and `strip_additions` puts the choice back so the exact oracle parse comparison still runs. `tests/test_cli_bridge_parity.py` does the same for the route tables. New tests: unlisted removal fails, listed removal passes, `--resource vpc` exits 2 for every cloud and runs nothing. Every VPC-only row of BUGS.md (BUG-012, 083, 085 to 095, 337, 367) is marked `removed with --resource vpc` (the fixed ones keep their status plus `; code removed with --resource vpc`). CLEANUP_SAFETY.md (CLI validation lines), README.md, and the package READMEs are updated.
- BUG-142: row marked `not a bug: intended (every snapshot older than --age without exception tags)`; TODO removed; snapshot README line added.
- BUG-283: row marked `wontfix: test environments; a volume detached from a stopped instance may be deleted early`; TODO replaced by a plain comment; disk README and SAF-017 note updated. The CreateTime floor code stays.
- Jenkins contract: `tests/fixtures/jenkins_commands.txt` replaced by the 47 commands given (6 lines differ from before: GCP disk `--detach_age`, Azure IP x2, Azure NIC and GCP IP x2 `--age`). `tests/helpers_ag_cli_jenkins_expected.json` regenerated from `describe()` (12 keys changed: the 6 edited commands, content of every other entry is identical).

**How the CLI parity tests reach the cleaners.** Unchanged: they patch `bridge.build_registry` / `bridge.build_notifiers` with `FakeCleaners` (`tests/helpers_cli_routes.py`) and run the oracle `main()` and `crc.cli.main.main` on the same fakes; the `vpc` cases are removed from `ROUTED_CALLS`, the resource lists and `AWS_ONLY`, and the BUG-084 divergence class is gone (`test_every_fixed_bug_has_diverging_cases` now expects BUG-009 and BUG-344).

**Test count.** Before 44674 (floor), after 43152: net minus 1,522: the deleted VPC unit, fix and parity tests outweigh the added ones. I lowered `tests/archtest/test_count_floor.txt` by hand to 43152 because the owner approved deleting the VPC tests and the rung otherwise cannot go green; see owner actions.

**Safety lock.** `tests/archtest/safety_lock.json`: the VPC test lock of SAF-001 was removed (SAF-001 keeps its two other locks) and the hashes were rewritten with `update_safety_lock.py`. No SAF ID covered VPC only, so none is retired (SAF-001 and SAF-004 are general rules).

**Not green: 5 contract cases wait for the other lanes.** `tests/test_jenkins_contract.py::test_command_reaches_its_cleaner_with_the_flags` fails for the 5 commands whose `--age` the triggers branch `crc/require-age` adds (Azure IP x2, Azure NIC, GCP IP x2; the routes `crc/cli/routes/azu.py` and `gcp.py` are not mine and do not pass `age` yet). Every other check (`make check` minus these 5) passes: 43,146 passed, 5 failed, 1 skipped. They turn green when the Azure and GCP lanes route `age`. The frozen `options` of those 5 entries then also need `age`; refresh with the helper below after the merge. I did not guess the option keys, and did not loosen or skip the test.

```
PYTHONPATH=. python3 - <<'PY'   # regenerate tests/helpers_ag_cli_jenkins_expected.json
import json, pytest
from tests.helpers_ag_cli_jenkins import EXPECTED, describe, load_commands, run_command
out = {}
for c in load_commands():
    with pytest.MonkeyPatch.context() as mp:
        seen = run_command(c, mp)
    data = json.loads(json.dumps(describe(seen))); data["label"] = c.label; out[c.key] = data
EXPECTED.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
PY
```

**Owner actions.**
- Confirm the lowered test floor (44674 to 43152) caused by the approved VPC deletion.
- After the Azure and GCP lanes merge: refresh `tests/helpers_ag_cli_jenkins_expected.json` as above and re-run `make check`.
- Retire `tests/legacy/aws_vpc.txt` (and its hash in `frozen_inputs.json`, `ADAPTER_ORACLES` entry, and `crc_main.txt` `delete_vpc`) when no test needs it; `tests/archtest/legacy_baseline.txt` still lists the old `crc/aws/vpc.py` path.
- `--resource vpc` in any Jenkins job outside the 47 commands now exits 2.

## New bugs

None found.
