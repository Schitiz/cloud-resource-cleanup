# Copyright (c) Yugabyte, Inc.

"""`delete_vpc` with retries on `DependencyViolation` only (BUG-087)."""

import logging
from collections.abc import Callable

from botocore.exceptions import ClientError

from crc.aws.vpc.client import Ec2Client, Vpc
from crc.core import logger

_DELETE_RETRIES = 5
_DELETE_RETRY_SLEEP_SEC = 3.0
_DEPENDENCY_VIOLATION = "DependencyViolation"

Sleeper = Callable[[float], None]


def _is_dependency_violation(error: Exception) -> bool:
    if not isinstance(error, ClientError):
        return False
    code = str(error.response.get("Error", {}).get("Code"))
    return code == _DEPENDENCY_VIOLATION


def delete_vpc_with_retries(
    client: Ec2Client, vpc: Vpc, region: str | None, sleep: Sleeper
) -> bool:
    """`delete_vpc`, retried only on `DependencyViolation` (BUG-087). Any other error is
    recorded and the VPC is skipped. Returns True when the VPC was deleted."""
    run = logger.current()
    last_error: Exception | None = None
    for attempt in range(1, _DELETE_RETRIES + 1):
        try:
            client.delete_vpc(VpcId=vpc.id)
        except Exception as e:
            logging.error(e)
            if not _is_dependency_violation(e):
                logging.error(f"Failed deleting VPC {vpc.id}: not a DependencyViolation, skipped")
                run.fail(region, vpc.id, e)
                return False
            last_error = e
            if attempt < _DELETE_RETRIES:
                logging.error(f"Failed deleting VPC {vpc.id}. Retrying...")
                sleep(_DELETE_RETRY_SLEEP_SEC)
        else:
            run.action("deleted", region, vpc.id)
            return True
    logging.error(f"Failed to Delete VPC {vpc.id} after {_DELETE_RETRIES} retries")
    run.fail(region, vpc.id, last_error or "delete_vpc failed")
    return False
