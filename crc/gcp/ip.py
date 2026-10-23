# Copyright (c) Yugabyte, Inc.

"""GCP IP address cleaner. The import path `crc.gcp.ip` keeps working: `IpCleaner` is the
registered `Cleaner` (`ip_cleaner.py`) and `IP` the legacy adapter `crc.py` uses
(`ip_adapter.py`)."""

from crc.gcp.ip_adapter import IP
from crc.gcp.ip_cleaner import IpCleaner, build_ip_cleaner
from crc.gcp.ip_client import AddressView, ComputeIpClient, GcpIpClient, OperationView

__all__ = [
    "IP",
    "AddressView",
    "ComputeIpClient",
    "GcpIpClient",
    "IpCleaner",
    "OperationView",
    "build_ip_cleaner",
]
