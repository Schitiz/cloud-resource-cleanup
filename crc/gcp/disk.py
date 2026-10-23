# Copyright (c) Yugabyte, Inc.

"""GCP disk cleaner. The import path `crc.gcp.disk` keeps working: `DiskCleaner` is the
registered `Cleaner` (`disk_cleaner.py`) and `Disk` the legacy adapter `crc.py` uses
(`disk_adapter.py`)."""

from crc.gcp.disk_adapter import Disk
from crc.gcp.disk_cleaner import DiskCleaner, build_disk_cleaner
from crc.gcp.disk_client import ComputeDiskClient, DiskView, GcpDiskClient
from crc.gcp.disk_settings import DiskSettings

__all__ = [
    "ComputeDiskClient",
    "Disk",
    "DiskCleaner",
    "DiskSettings",
    "DiskView",
    "GcpDiskClient",
    "build_disk_cleaner",
]
