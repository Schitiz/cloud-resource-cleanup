## Coding summary

Lane CL2-GCP (test-only): `tests/test_cli_bridge_gcp.py` and `tests/helpers_gcp_bridge.py` no longer
run the current legacy CLI code. No production code changed.

**What is routed.** Unchanged: every GCP pair (`disk`, `ip`, `vm`, `spot_instances`) already runs
through `crc/cli/bridge.py`. The routed side of the tests still builds the current `CRC` through
`make_crc` as the context object and calls `dispatch._run_pair`.

**Adapters deleted or shimmed.** None (test-only lane).

**How the CLI parity tests now reach the cleaners.**
- Legacy side: `tests/helpers_cl2_gcp_oracle.py` (new) loads `tests.helpers_oracle.load_legacy_crc()`
  (`main`'s `CRC` bound to `tests/legacy/gcp_*.txt`) and calls `delete_disks`, `delete_ip`,
  `delete_vm`, `stop_vm`, `delete_spot_instances` as `main` dispatched them. The oracle adapters
  call the SDK directly, so `patch_sdk` replaces `googleapiclient.discovery.build` and the
  `compute_v1` Disks/Instances/Addresses/Regions clients with fakes that delegate to the same
  `FakeGcp` the routed path uses (same recorded calls, same fault injection, `close()` on exit).
- Run-log lines: the oracles log none. `tests/helpers_cl2_gcp_runlog.py` (new, data only) holds the
  RUN START / REGION / ACTION / SKIPPED / ERRORS / RESULT lines the pre-CL2 legacy handlers logged for
  all 123 case/switch/fault combinations (captured while that code still existed). The routed run
  is asserted against them, with the same per-kind comparison as before.
- Fixed-bug divergences: `tests/helpers_cl2_gcp_diverge.py` (new, data only) lists, per combination,
  the BUG ids, the exact outcome fields (Slack, Influx, stdout, error, GCP calls) that differ from
  `main`, and the values the routed run must produce (frozen from the pre-CL2 legacy run, not from
  the routed run). `assert_equal` requires that exactly those fields differ from the oracle and that
  the routed run equals the frozen values, so a divergence can neither grow nor disappear silently.
  Bugs: BUG-001 (`ip` exception regex inverted in `main`), BUG-005 (`disk` notags ignored), BUG-006
  (`disk` name_regex ignored), BUG-127 (`disk` listing error aborts the run in `main`), BUG-186
  (`vm` zone listing error aborts the run in `main`). `spot_instances` and the dry-run Spot cases
  show no divergence.
- Test fake fix: `FakeGcp.delete_disk` took `(project, zone, disk)` but the Spot client calls
  `(project, scope, location, disk)`, so every routed and pre-CL2 leftover-disk delete of a Spot VM
  failed with a `TypeError` that the Spot cleaner logs and swallows. The leftover disk deletes were
  therefore never compared. The fake now accepts both shapes; the frozen run-log data was captured
  with the fixed fake, and the Spot cases now compare leftover disk deletes, Slack and Influx
  against the oracle.
- Assertions kept: the owner-ping known difference test, the BUG-400 "deletes fewer, never more"
  test, and the close-error test (which now states both the oracle's names and the routed names).

**Test count.** Before 44400 (`tests/test_cli_bridge_gcp.py`: 126), after 44400 (126). `make check` is
green; the floor is unchanged, so no `make raise-test-floor`.

**Grep.** `tests/test_cli_bridge_gcp.py`, `tests/helpers_gcp_bridge.py` and `tests/helpers_cl2_gcp_*`
import none of `crc.cli.resource_ops`, `vm_ops`, `notify`, `adapter_args`, `report_calls`,
`tests.helpers_legacy_handlers` and call no `delete_*`/`stop_*`/`notify_*` of `crc.cli.runner.CRC`
(the only such calls are on `main`'s CRC oracle and on the fake SDK client).

**Owner actions.** None. A later lane can delete `tests/helpers_legacy_handlers.py` once the other
bridge tests stop using it; this lane no longer does.

## New bugs

- `tests/helpers_gcp_bridge.py` (before this lane): `FakeGcp.delete_disk` had the wrong signature for the
  Spot client; fixed here (test-only), no production bug.
- None in production code found.
