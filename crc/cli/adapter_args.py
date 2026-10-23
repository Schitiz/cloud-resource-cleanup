"""Constructor arguments `CRC` passes to the adapter classes of each cloud."""

from dataclasses import dataclass
from typing import Any

from crc.cli.base import CRCBase

Tags = dict[str, list[str]]


@dataclass(frozen=True)
class DiskArgs:
    """Every argument `delete_disks` receives, so the per-cloud builders take one value."""

    filter_tags: Tags
    exception_tags: Tags
    age: Any
    custom_age_tag_key: Any
    detach_age: Any
    name_regex: list[str]
    exception_regex: list[str]
    slack_notify_users: bool
    slack_user_label: Any


def vm_arguments(
    ops: CRCBase, filter_tags: Tags, exception_tags: Tags, age: Any, custom_age_tag_key: Any
) -> tuple[Any, ...]:
    """Positional arguments of the VM and spot VM adapters of `ops.cloud`.

    Azure takes the resource group first, GCP the project after the dry run flag, AWS and
    OCI neither.
    """
    common = (filter_tags, exception_tags, age, custom_age_tag_key, ops.notags)
    if ops.cloud == "azure":
        return (ops.resource_group, ops.dry_run, *common)
    if ops.cloud == "gcp":
        return (ops.dry_run, ops.project_id, *common)
    return (ops.dry_run, *common)


def ip_arguments(
    ops: CRCBase,
    filter_tags: Tags,
    exception_tags: Tags,
    name_regex: list[str],
    exception_regex: list[str],
) -> tuple[Any, ...]:
    """Positional arguments of the IP adapter of `ops.cloud` (aws, azure or gcp)."""
    if ops.cloud == "azure":
        return (ops.resource_group, ops.dry_run, filter_tags, exception_tags, ops.notags)
    if ops.cloud == "gcp":
        return (ops.dry_run, ops.project_id, name_regex, exception_regex)
    return (ops.dry_run, filter_tags, exception_tags, ops.notags)


def disk_arguments(ops: CRCBase, args: DiskArgs) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Positional and keyword arguments of the disk adapter of `ops.cloud`."""
    tags_and_age = (
        args.filter_tags,
        args.exception_tags,
        args.age,
        args.custom_age_tag_key,
        ops.notags,
    )
    if ops.cloud == "aws":
        return (
            ops.dry_run,
            *tags_and_age,
            args.name_regex,
            args.exception_regex,
            args.detach_age,
        ), {}
    if ops.cloud == "oci":
        return (ops.dry_run, *tags_and_age), {}
    if ops.cloud == "azure":
        return (ops.resource_group, ops.dry_run, *tags_and_age), {}
    return (), {
        "dry_run": ops.dry_run,
        "project_id": ops.project_id,
        "filter_labels": args.filter_tags,
        "exception_labels": args.exception_tags,
        "age": args.age,
        "custom_age_tag_key": args.custom_age_tag_key,
        "detach_age": args.detach_age,
        "notags": ops.notags,
        "name_regex": args.name_regex,
        "exception_regex": args.exception_regex,
        "slack_notify_users": args.slack_notify_users,
        "slack_user_label": args.slack_user_label,
    }
