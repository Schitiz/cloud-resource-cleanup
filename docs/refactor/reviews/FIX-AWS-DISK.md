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

`CLEANUP_SAFETY.md` (CODEOWNERS, not edited): proposed text for the SAF-010 age-floor invariant, appended: "When both `age` and `detach_age` are set, the CreateTime floor is the effective age (custom age tag or `age`) plus `detach_age`, because the CloudWatch detach guard cannot see attachments to stopped instances (BUG-283)." And for the yb_task rule: "Every tag whose key folds to `yb_task` is judged; one sensitive value keeps the volume (BUG-282)."

No locked-test change is needed.

## New bugs

- `crc/aws/disk/volumes.py` `tag_map` collapses duplicate exact keys (later value wins), so `yb_task=prod` followed by `yb_task=dev` is judged as `dev` and the volume can be deleted (already in the AWS-4 pending list as the duplicate `Key` row; exists on main: yes, `crc/aws/disk.py:170-171`). The same-key duplicates are not covered by BUG-282 (different keys that fold equal). The parity case `yb-task-key-variants` volume `f` still shows it. Not fixed.
