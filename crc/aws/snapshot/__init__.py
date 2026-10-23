# Copyright (c) Yugabyte, Inc.

"""AWS EBS snapshot cleaner package.

`SnapshotCleaner` (`cleaner.py`) is the registered `aws` / `snapshot` Cleaner; `Snapshot`
(`adapter.py`) is the legacy class `crc.py` uses. The old import path `crc.aws.snapshot`
keeps working.
"""

from .adapter import Snapshot
from .cleaner import SnapshotCleaner, build_snapshot_cleaner
from .client import SnapshotClient, SnapshotRuntime

__all__ = [
    "Snapshot",
    "SnapshotCleaner",
    "SnapshotClient",
    "SnapshotRuntime",
    "build_snapshot_cleaner",
]
