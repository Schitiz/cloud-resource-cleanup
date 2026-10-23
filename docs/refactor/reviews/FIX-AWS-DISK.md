## Coding summary

Rung FIX-AWS-DISK (wave FIX-1): behaviour fixes in the AWS EBS disk cleaner (`crc/aws/disk/`; the module `crc/aws/disk.py` of the task notes is now this package).

- **Bugs fixed.**
  - BUG-282: `VolumeFilter.should_skip` judges every tag whose key folds to `yb_task` (case, `-` to `_`); one sensitive value keeps the volume. Label and `Disk.SENSITIVE_YB_TASK` are unchanged (the label still shows the first folded value).
  - BUG-283 (partly, fail closed without new permissions): when both `age` and `detach_age` are set, the CreateTime floor is the effective age (custom age tag if valid, else `age`) plus `detach_age`. A volume younger than that is kept with a DEBUG line `Skipping volume X: detach time unknown and CreateTime younger than age plus detach_age` and skip reason `detach_unknown_too_young`. Production command 1 now needs 10 days (7 + 3), command 2 needs 37 days (30 + 7); both keep the same flags and selection otherwise.
- **Bugs left.** None fully; BUG-283 keeps a residual gap, see Owner decision.
- **Files changed.** `crc/aws/disk/volumes.py`, `crc/aws/disk/README.md`, `crc/aws/README.md`, `tests/test_aws_disk_parity.py` (diverging cases `yb-task-key-variants` -> BUG-282 and `detach-age-and-age` -> BUG-283 asserted via `_check_divergence`; the quirk check of `yb-task-key-variants` is replaced by it), new `tests/test_aws_disk_fix.py` (26 tests), this file. Locked `tests/test_aws_disk.py` is unchanged and green. Oracle untouched.
- **Tests.** `pytest -q`: 42444 before (182466d), 42469 after (+25). `make check` green.
- **Owner actions.** See below.

## Owner decision

BUG-283 cannot be fixed completely without new API permissions. AWS/EBS CloudWatch metrics exist only while a volume is attached to a running instance, and the volume's last detach time is only available from CloudTrail (`cloudtrail:LookupEvents`) or instance state history, neither granted today. The fix therefore only makes the CreateTime floor stricter (age plus `detach_age`). Residual gaps:

- Detach-only runs (`--detach_age` without `--age`, not used by the production commands) keep the floor `detach_age`; a volume detached moments ago from a stopped instance and older than `detach_age` passes. Raising that floor would be arbitrary without an `age`, so it is left for the owner (options: require `--age` together with `--detach_age`, or grant CloudTrail read and use the real DetachVolume event time).
- With `age` set, a volume older than age plus `detach_age` that was detached moments ago from a stopped instance is still deleted. Only CloudTrail or a snapshot-style "available since" tag closes this.

## Owner action

`CLEANUP_SAFETY.md` (CODEOWNERS, not edited): proposed text for `CLEANUP_SAFETY.md:114-118` (`[SAF-025]` / `[SAF-019]`): "For CreateTime, when `--age` is omitted the floor is `max(retention_tag, detach_age)`; when `--age` is set without `--detach_age` it is `retention_age or self.age`; when both `--age` and `--detach_age` are set it is `(retention_age or self.age) + self.detach_age`, because the CloudWatch detach guard cannot see attachments to stopped instances (BUG-283)." And for the `yb_task` protection rule: "Every tag whose key folds (case, `-` to `_`) to `yb_task` is judged; one sensitive value keeps the volume (BUG-282)."

No locked-test change is needed.

## New bugs

- `crc/aws/disk/volumes.py` `tag_map` collapses duplicate exact keys (later value wins), so `yb_task=prod` followed by `yb_task=dev` is judged as `dev` and the volume can be deleted (already in `docs/refactor/BUGS.md` as `BUG-289`; exists on main: yes, `crc/aws/disk.py:170-171`). The same-key duplicates are not covered by BUG-282 (different keys that fold equal). The parity case `yb-task-key-variants` volume `f` still shows it. Not fixed.

## Round 1 (Argon)

Scope reviewed: `git diff 182466d..HEAD` (`crc/aws/disk/volumes.py`, `crc/aws/disk/README.md`, `crc/aws/README.md`, `tests/test_aws_disk_parity.py`, `tests/test_aws_disk_fix.py`, `docs/refactor/reviews/FIX-AWS-DISK.md`) against `docs/refactor/BUGS.md`, `CLEANUP_SAFETY.md`, `.cursor/skills/crc-python-refactor/BEHAVIOUR_FIX.md`, and `docs/refactor/LOGGING.md`.

### Checklist verification

1. **Each fixed bug is really fixed for the inputs its `BUGS.md` row describes, with a test that fails on `182466d` and passes now:**
   - **BUG-282** (`crc/aws/disk/volumes.py:59-67`, `:87-96`): `_sensitive_yb_task` checks every `(key, value)` pair in `tags` whose key folds (`key.casefold().replace("-", "_") == "yb_task"`) and returns the first stripped value matching `policy.is_sensitive_yb_task`. If any folded `yb_task` tag is sensitive (such as `yb_task=""` or `yb_task="dev"` before `YB-Task="prod"`), `VolumeFilter.should_skip` logs `"Skipping volume %s: sensitive yb_task=%s"` at `DEBUG`, counts `sensitive_yb_task` via `logger.current().skip`, and keeps the volume. `volume_label` still uses `_yb_task` (first folded key) so labels of non-sensitive volumes are unchanged. `test_bug_282_any_sensitive_folded_yb_task_keeps_the_volume` in `tests/test_aws_disk_fix.py` and case `yb-task-key-variants` in `tests/test_aws_disk_parity.py` fail on `182466d` and pass on `HEAD`.
   - **BUG-283** (`crc/aws/disk/volumes.py:197-214`): when both `settings.age` and `settings.detach_age` are set, `_detach_floor` adds `settings.detach_age` to the effective creation floor (`retention_age or settings.age`). A volume passing the base `floor` (`too_young`) but younger than `effective_age + detach_age` is kept before CloudWatch lookup with `DEBUG` log `"Skipping volume %s: detach time unknown and CreateTime younger than age plus detach_age"` and `logger.current().skip("detach_unknown_too_young")`. `test_bug_283_age_and_detach_age_floor_is_their_sum` (and companion tests in `tests/test_aws_disk_fix.py` and case `detach-age-and-age` in `tests/test_aws_disk_parity.py`) fail on `182466d` and pass on `HEAD`.
2. **Direction rule and parity tests:**
   - `_sensitive_yb_task` is a strict superset of single-first-tag `yb_task` checking, and `_detach_floor(floor)` is `>= floor` (equal when either `age` or `detach_age` is unset, strictly greater when both are positive). Nothing kept on `182466d` can be deleted on `HEAD`.
   - `tests/legacy/aws_disk.txt` is untouched (`git diff 182466d..HEAD -- tests/legacy/` is empty). All 147 unmarked cases in `tests/test_aws_disk_parity.py` assert full equality with the oracle; the 2 diverging cases (`yb-task-key-variants` -> `BUG-282`, `detach-age-and-age` -> `BUG-283`) assert both the oracle's old outcome and the exact new `calls`, `deleted`, `count`, `logs`, `stdout`, and `error`.
3. **Production Jenkins commands:**
   - Command 1 (`--filter_tags '{"yb_task":[...]}' --age '{"days": 7}' --detach_age '{"days": 3}' --max_age '{"days": 21}' --exception_tags '{"autoclean":[...],"auto_clean":[...],"crc":["gke"]}' --custom_age_tag_key max_retention_age`) and Command 2 (`--notags '{"yb_task":[]}' --age '{"days": 30}' --detach_age '{"days": 7}' --exception_tags '{"autoclean":[...],"auto_clean":[...],"crc":["gke"]}'`) run with identical flags and selection except for the intentional `BUG-282` and `BUG-283` safety floors (10 days and 37 days, or `custom_age + 3 days`). Pinned end-to-end in `test_production_command_1_end_to_end` and `test_production_command_2_end_to_end`.
4. **Fail-closed paths raise before any SDK mutation:**
   - Constructor/settings validation raises `ValueError` / `OverflowError` before any client call; `VolumeFilter.is_candidate` runs during read-only planning (`ARCH-005` passes).
5. **Protected files untouched:**
   - No edits to `tests/test_aws_disk.py`, `tests/archtest/safety_lock.json`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`, `docs/refactor/BUGS.md`, `CLEANUP_SAFETY.md`, `AGENTS.md`, `ARCHITECTURE.md`, `.cursor/**`, or `tests/archtest/**`.
6. **README Safety Invariants and Public API updated (`ARCH-002`):**
   - `crc/aws/disk/README.md` and `crc/aws/README.md` document `BUG-282` and `BUG-283` under Safety Invariants; public symbol lists match (`test_arch002_readmes.py` passes).
7. **Unfixed / residual items explained under `## Owner decision`:**
   - Residual `BUG-283` gaps (detach-only runs without `--age`, and volumes older than `age + detach_age` detached moments ago from a stopped instance without CloudTrail permissions) are documented under `## Owner decision`.

### BLOCKING (fixed)

1. **Incomplete divergence and fixed-quirk assertions in `tests/test_aws_disk_parity.py`** (`tests/test_aws_disk_parity.py:29-80`, `:1000-1015`, `:1090-1155`, `:1365-1385`):
   - `_check_divergence` previously checked only `_delete_ids(new.calls)`, `set(new.deleted) < set(old.deleted)`, and substring presence of `"Skipping volume <id>: "` instead of asserting the exact new `calls` (including the single-volume CloudWatch query in `detach-age-and-age`), exact `new.deleted` labels, `new.count`, `new.stdout`, and exact `new.logs` list as required by `BEHAVIOUR_FIX.md` section 3.
   - Removing `yb-task-key-variants` from `QUIRKS` without a replacement fixed-quirk test left `BEHAVIOUR_FIX.md` section 3 ("A quirk check that asserted the buggy behaviour for `BUG-NNN` is replaced by a check that asserts the fixed behaviour and names the bug") only indirectly covered, and `test_skip_lines_are_debug_only_in_new_code` skipped `DIVERGING` without verifying `logging.DEBUG` on their skip records.
   - Replaced `DIVERGING` tuples with `Divergence` specs pinning `old_deleted`, `new_deleted`, `new_delete_ids`, non-delete calls, and exact `new_logs`; added `FIXED_QUIRKS` / `test_fixed_quirk_is_pinned`; and asserted `logging.DEBUG` on all `"Skipping volume "` records of `DIVERGING` cases.
2. **Missing run-log skip-count assertions and end-to-end production-command tests in `tests/test_aws_disk_fix.py`** (`tests/test_aws_disk_fix.py:48-60`, `:98-112`, `:140-260`):
   - `test_bug_283_skip_is_logged_at_debug_and_counted` and `test_bug_282_any_sensitive_folded_yb_task_keeps_the_volume` did not call `logger.begin()` / `logger.finish()` to assert that `SKIPPED cloud=aws resource=disk reason=detach_unknown_too_young count=1` and `reason=sensitive_yb_task count=1` are recorded.
   - Added run-log `SKIPPED` assertions and added `test_production_command_1_end_to_end` and `test_production_command_2_end_to_end` exercising the full option sets of both production Jenkins commands through `Disk`.

### NIT (left — CODEOWNERS / protected files, not edited)

- **NIT** `CLEANUP_SAFETY.md:114-118` (`[SAF-025]`): currently states `For CreateTime, _creation_age_floor takes max(retention_tag, detach_age) only in detach_age-only mode (--age omitted); when --age is set it returns retention_age or self.age.` Proposed text: `For CreateTime, the floor is max(retention_tag, detach_age) in detach_age-only mode (--age omitted), retention_age or self.age when only --age is set, and (retention_age or self.age) + self.detach_age when both --age and --detach_age are set because CloudWatch cannot see attachments on stopped instances (BUG-283). Every tag whose key folds (case, - to _) to yb_task is judged for sensitive values (BUG-282).`

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` | Success: no issues found in 229 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 42473 passed |

Test count: 42444 before (`182466d`), 42469 before review (`13596ce`), 42473 after review (+29 total).

VERDICT: APPROVE
