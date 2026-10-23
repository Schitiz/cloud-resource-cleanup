# Copyright (c) Yugabyte, Inc.

"""GCP VM cleaner. The import path `crc.gcp.vm` keeps working: `VmCleaner` is the registered
`Cleaner` (`vm_cleaner.py`) and `VM` the legacy adapter `crc.py` uses (`vm_adapter.py`)."""

from crc.gcp.vm_adapter import VM
from crc.gcp.vm_cleaner import VmCleaner, build_vm_cleaner
from crc.gcp.vm_client import ComputeVmClient, GcpVmClient, InstanceView
from crc.gcp.vm_settings import VmSettings

__all__ = [
    "VM",
    "ComputeVmClient",
    "GcpVmClient",
    "InstanceView",
    "VmCleaner",
    "VmSettings",
    "build_vm_cleaner",
]
