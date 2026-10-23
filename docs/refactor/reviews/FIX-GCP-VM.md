## Coding summary

Rung FIX-GCP-VM (wave FIX-1), branch `fix/gcp-vm`.

- Fixed: BUG-185 (wait for the zone operation before recording a delete or stop) and BUG-186
  (an error on one instance or in one zone listing is recorded and the run goes on).
- Left: none of the two. BUG-183 (age) is not in this rung and is untouched.
- Files changed: `crc/gcp/vm.py`, new `crc/gcp/vm_client.py` (the client protocols and
  `ComputeVmClient` moved out so `vm.py` stays under the ARCH-004 400-line limit; re-exported by
  `crc.gcp.vm`), `crc/gcp/README.md`, `tests/test_gcp_vm.py` (fake client gets
  `get_zone_operation`, delete/stop return an operation name, call lists include the poll),
  `tests/test_gcp_vm_parity.py` (diverging cases marked BUG-185 / BUG-186 with the exact new
  outcome), new `tests/test_gcp_vm_fix.py`. No locked test, oracle, PLAN/STATUS/BUGS or
  CLEANUP_SAFETY.md edited.
- Tests: `pytest -q` 42444 passed at 182466d, 42462 after (18 new tests in
  `tests/test_gcp_vm_fix.py`; parity cases keep their count).
- Owner actions: none.

### What changed

BUG-185: `VmCleaner.apply_instance()` still calls `instances().delete()` / `.stop()` and logs
"Deleting instance" / "Stopping instance" right after the call, then polls
`zoneOperations().get()` (new `GcpVmClient.get_zone_operation`) every 5 s for at most 180 s
(`VmSettings.wait_sec`, `poll_sec`, as the Spot cleaner). The instance is recorded and the
ACTION line logged only when the operation is `DONE` without `error`. A response without an
operation name, a poll error, an operation error or a timeout raises inside the existing
per-instance `try`: `Error occurred while delete instance <id>: ...` is logged, `fail()` is
recorded, nothing is recorded as deleted. So it can only record less than before. A dry run
makes no call and no poll.

BUG-186: `plan_zone()` wraps each instance evaluation (status, labels, tags, age, candidate
build): an error logs `Error occurred while evaluating instance <name>: ...`, calls
`fail(zone, name, e)` and keeps the instance (fail closed). The per-zone `list_instances()` call
and the iteration are wrapped: an error logs `Zone <z>: failed listing GCP instances: ...`,
calls `region_skipped()` and `fail(zone, "-", e)` and ends that zone (no REGION line); instances
already yielded stay processed. The loop continues with the next instance / zone. An invalid
`MAX_AGE` therefore no longer aborts the run: every instance fails to evaluate, is recorded and
kept, nothing is deleted.

Production commands: same flags, same selection; the only differences are the extra
`zoneOperations().get()` polls after each delete/stop and the recorded-and-continue handling of
errors. With a clean run the logs are the same as before (no extra log lines on success).

## Owner decision

- `zones().list()` (project-level zone list) and a zone entry without a `name` still raise.
  Skipping them would turn an auth or connectivity failure into a successful run that did
  nothing; nothing has been acted on at that point, so raising is the fail-closed outcome
  (SKILL 4.2). BUG-186 row text lists "zone listing"; the per-zone instance listing is what is
  isolated now. Confirm this reading, or ask for the project-level listing to be isolated too.
- Exit code: like the Spot cleaner, recorded failures (`fail()`) show in the ERRORS / RESULT
  footer of the run log but do not change the exit code. Before, such an error was an uncaught
  exception (non-zero exit); now the run exits 0 unless the CLI reports failures.
  If Jenkins should still turn red on such errors, the owner must decide how (a CLI-level change
  is out of this rung).

## New bugs

- `crc/gcp/vm.py` `VM.__init__` / `ComputeVmClient._compute()`: the discovery service is closed
  by the `with` in `list_zones()` and then reused for delete/stop/poll (exists on main: yes,
  `crc.py:1429` shape). It works because googleapiclient reopens connections; not changed.
