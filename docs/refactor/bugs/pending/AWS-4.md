# Pending bugs and quirks: AWS-4 (`crc/aws/disk.py`)

Same columns as `docs/refactor/BUGS.md`; the integrator assigns the `BUG-NNN` IDs. Locations are
`main` lines of `crc/aws/disk.py` (verified with `git show main:crc/aws/disk.py`, frozen in
`tests/legacy/aws_disk.txt`). Every row is preserved by this rung and pinned by
`tests/test_aws_disk_parity.py`; none is fixed here. Existing rows that apply to this module:
BUG-004 (fail-open custom age tag), BUG-018 (EBS breaker), BUG-022 (yb_task / Kubernetes protection
only here and in the spot leftover volumes).

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | The sensitive `yb_task` test judges only the first tag whose key folds (case, `-` to `_`) to `yb_task`: with `yb_task=""` before `YB-Task=prod` the volume is deleted | `crc/aws/disk.py:173-178`, `:236-243` | yes | deletes what it should keep | high | AWS-4 | open |
| NEW | `detach_age` cannot see attachments to stopped instances (AWS/EBS metrics are published only for running instances): a volume detached moments ago from a stopped instance has an empty Complete series and passes; only the CreateTime floor protects it | `crc/aws/disk.py:33-45`, `:545-624` | yes | deletes what it should keep | high | AWS-4 | open |
| NEW | Errors never fail the run: per-volume, per-region and delete errors are logged and flagged in `_had_errors`, but `delete()` returns normally, so Jenkins stays green after a partial sweep | `crc/aws/disk.py:300-322`, `:338-341`, `:355-364`, `:649-651` | yes | error swallowed | medium | AWS-4 | open |
| NEW | A region `ClientError` with code `AuthFailure`, `UnauthorizedOperation`, `OptInRequired` or `InvalidClientTokenId` only logs a warning and does not set `_had_errors`, so the closing "did not complete" error line is not logged for a skipped region | `crc/aws/disk.py:326-337` | yes | error swallowed | medium | AWS-4 | open |
| NEW | A connectivity error from `delete_volume` is re-raised out of the per-volume handler and aborts the rest of the region (remaining candidates are neither deleted nor logged as failures); volumes already deleted in that region stay in `disks_to_delete`, and the region is logged as skipped | `crc/aws/disk.py:310-325`, `:645-650` | yes | error swallowed | medium | AWS-4 | open |
| NEW | A `delete_volume` error that is not a `ClientError` (for example `BotoCoreError`) is logged as "failed considering volume" and flagged; a `ClientError` is logged as "Failed to delete volume"; both are swallowed per volume and flagged | `crc/aws/disk.py:310-322`, `:645-651` | yes | error swallowed | low | AWS-4 | open |
| NEW | The Kubernetes CSI protection matches the prefixes `kubernetes.io/` and `ebs.csi.aws.com/` or the exact keys `KubernetesCluster` and `CSIVolumeName`: a bare `kubernetes.io` key is not protected | `crc/aws/disk.py:194-208` | yes | deletes what it should keep | low | AWS-4 | open |
| NEW | `_normalize_age` converts only `TypeError` and `ValueError` of `int()`: an overflowing value (`{'days': 1e999}`, `10**30` days) raises `OverflowError`, which escapes the constructor for `--age` and `--detach_age`, and for a custom age tag it is caught by the per-volume handler (volume skipped, error flagged) | `crc/aws/disk.py:159-162`, `:403-410`, `:384-421` | yes | wrong error type | low | AWS-4 | open |
| NEW | A tag with `Value: None` passes `_tag_map` and the yb_task lookup but raises in `fnmatch.fnmatchcase(None, ...)` when a `filter_tags` pattern list is set, skipping the volume with an error flag instead of a mismatch | `crc/aws/disk.py:170-171`, `:217-219` | yes | wrong error type | low | AWS-4 | open |
| NEW | A volume without a `VolumeId` is not rejected: the label is `region/None` and `delete_volume(VolumeId=None)` is called (botocore validation then fails and is logged) | `crc/aws/disk.py:367-369`, `:628-651` | yes | invalid call | low | AWS-4 | open |
| NEW | The zero `detach_age` window branch is dead code: `_normalize_age` rejects a zero window, so `_drop_recently_attached` never reaches the "window is zero" warning | `crc/aws/disk.py:166-168`, `:541-548` | yes | dead code | low | AWS-4 | open |
| NEW | `name_regex` and `exception_regex` search the `Name` tag, or the volume id when `Name` is absent or empty, never other tags | `crc/aws/disk.py:386`, `:223-233` | yes | surprising filter | low | AWS-4 | open |
