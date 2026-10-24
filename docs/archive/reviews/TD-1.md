## Coding summary

Lane TD-1 (no production behaviour change): tracked TODOs for open high-risk bugs, the
ARCH-012 check, the todo-to-issue workflow, the oracle note and the adapter-wording cleanup.

- **Routed kinds:** none changed. No cleaner, route table or flag was touched; only comments,
  docs, one workflow and one archtest check were added.
- **Adapters deleted or shimmed:** none in this lane. The wording about adapter classes was
  removed from comments and READMEs in `crc/`: `crc/README.md`, `crc/cli/README.md`,
  `crc/cli/bridge.py`, `runner.py`, `scan.py`, `routes/azu.py`, `routes/gcp.py`,
  `crc/azu/ip/cleaner.py`, `crc/aws/keypairs/__init__.py`. `git grep -niw adapter crc` still
  finds two hits in `crc/cli/scan.py` (`_NO_SCAN_CLASSES`): they are the class paths printed in
  the `NotImplementedError` message of `--scan_tag` for Azure, GCP and OCI, which is output the
  parity tests compare, so changing them is a behaviour change (left for the owner).
- **CLI parity tests:** unchanged; they still reach the cleaners through `crc.cli.bridge`
  (`build_registry` / `build_notifiers` patched, `FakeCleaners`).
- **Test count:** 44,572 before, 44,597 after (+25, the ARCH-012 self-tests); floor raised
  with `make raise-test-floor`. `make check` is green (44,596 passed, 1 skipped).

### What was done

1. **TODOs.** Critical/high rows still open or partly fixed in `docs/refactor/BUGS.md`
   (recomputed from the table; every one was re-read against this branch and is still true):
   BUG-062, 075, 083 (partly fixed), 112, 124, 142, 173, 183, 213, 283 (partly fixed). Each has
   one `TODO(BUG-NNN)` with a `labels: bug, risk-high, crc` line above the function that holds
   the behaviour:

   | Bug | Where |
   |-----|-------|
   | BUG-062 | `crc/gcp/ip_cleaner.py` `IpCleaner.plan_region` |
   | BUG-075 | `crc/azu/ip/cleaner.py` `AzureIpCleaner.decide` |
   | BUG-083 | `crc/aws/vpc/cleaner.py` `VpcCleaner.plan_region` |
   | BUG-112 | `crc/azu/nic/cleaner.py` `AzureNicCleaner.decide` |
   | BUG-124 | `crc/gcp/disk_cleaner.py` `DiskCleaner._older_than_detach_age` |
   | BUG-142 | `crc/aws/snapshot/cleaner.py` `SnapshotCleaner._decide` |
   | BUG-173 | `crc/azu/disk/cleaner.py` `AzureDiskCleaner._is_old_enough` |
   | BUG-183 | `crc/gcp/vm_cleaner.py` `VmCleaner._is_old` |
   | BUG-213 | `crc/aws/vm/judge.py` `_judge` |
   | BUG-283 | `crc/aws/disk/detach.py` `volume_recently_attached` (see also `volumes.py` `_detach_floor`) |

   BUG-355: `tests/test_jenkins_contract.py` passes (142 cases) and the Azure Spot fixture line in
   `tests/fixtures/jenkins_commands.txt` carries `--age '{"days": 1}'`; the row is marked
   "fixed in cloud-resource-cleanup-triggers #29" and has no TODO.
2. **Workflow** `.github/workflows/todo-to-issue.yml`: push to `main` and `workflow_dispatch`
   only, guarded by `github.repository == 'yugabyte/cloud-resource-cleanup'`, `contents: read`
   and `issues: write`, action pinned to `37bb7b56...` (v5.1.15), `CLOSE_ISSUES: "true"`,
   `AUTO_ASSIGN: "false"`, `IDENTIFIERS` TODO only, `IGNORE` `tests/legacy/.*,docs/archive/.*`.
3. **ARCH-012** (`tests/archtest/todo_bugs.py`, `test_arch012_todo_bugs.py`, README row, AGENTS.md,
   `fix-bug.md`, BUGS.md rule 5): a TODO(BUG-NNN) must name an open or partly fixed row; each
   open or partly fixed critical/high row has exactly one; a TODO without a BUG id fails; a
   duplicate fails. The self-tests build the keyword from two string pieces so the action does
   not open issues for test strings.
4. **Oracle note** in `tests/legacy/README.md` ("Retiring an oracle") and one line in `AGENTS.md`.
5. **Adapter wording** removed as described above.

### Owner actions

- Enable Settings > Actions > General > Workflow permissions "Read and write" in
  `yugabyte/cloud-resource-cleanup`, or the workflow cannot create or close issues.
  `INSERT_ISSUE_URLS` stays off.
- Decide whether `_NO_SCAN_CLASSES` in `crc/cli/scan.py` may stop naming `adapter` classes in the
  `--scan_tag` error message (behaviour change, parity-tested).
- `tests/README.md` (outside this lane's edit list) still says "adapter" in four lines.

### New bugs

None. Note: `crc/aws/disk/README.md` line 50 says BUG-283 is "(fixed)" while the register row
says "partly fixed"; the row wins and keeps its TODO (the lane could not edit that README's
status wording beyond comments; the owner may align it).

### Left for later

Nothing from the task list. `make check` is the gate and passed.
