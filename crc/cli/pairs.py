"""Which (cloud, resource) pairs a run supports, and the error for one that is not."""

from typing import Any

from crc.cli.constants import CLOUDS

UNSUPPORTED_PAIR_MESSAGES: dict[str, str] = {
    "keypair": "Keypair operation is only supported on AWS.",
    "nic": "NICs operation is only supported on Azure.",
    "kms": "KMS operation is only supported on AWS.",
}

SUPPORTED_CLOUDS: dict[str, tuple[str, ...]] = {
    "keypair": ("aws",),
    "nic": ("azure",),
    "kms": ("aws",),
    "ip": ("aws", "azure", "gcp"),
    "snapshot": ("aws",),
    "vpc": ("aws",),
}

AWS_ONLY_RESOURCES = ("snapshot", "vpc")

AWS_DISK_OPT_IN_MESSAGE = (
    "AWS EBS volume cleanup requires '--cloud aws --resource disk'. "
    "Refusing to continue so --cloud all / --resource all does not "
    "skip EBS and then delete other AWS resources, and so "
    "--cloud all --resource disk does not reach other clouds' disks."
)


def is_supported_pair(cloud: Any, resource: Any) -> bool:
    """False for a (cloud, resource) pair whose `CRC` method raises for that cloud."""
    allowed = SUPPORTED_CLOUDS.get(resource)
    return allowed is None or cloud in allowed


def _unsupported_message(cloud: Any, resource: Any) -> str:
    if resource in AWS_ONLY_RESOURCES:
        return f"--resource {resource} is AWS-only; use --cloud aws (got --cloud {cloud})"
    if resource == "ip":
        return f"Invalid cloud provided: {cloud}. Supported clouds are {CLOUDS}"
    return UNSUPPORTED_PAIR_MESSAGES[resource]
