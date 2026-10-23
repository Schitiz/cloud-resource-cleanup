# Copyright (c) Yugabyte, Inc.

"""AWS KMS key cleaner package.

`KmsCleaner` (`cleaner.py`) is the registered `aws` / `kms` Cleaner; `Kms` (`adapter.py`) is
the legacy class `crc.py` uses. The old import path `crc.aws.kms` keeps working.
"""

from .adapter import Kms
from .cleaner import KmsCleaner, build_kms_cleaner
from .client import KmsClient, KmsPaginator, KmsRuntime
from .settings import KmsSettings

__all__ = [
    "Kms",
    "KmsCleaner",
    "KmsClient",
    "KmsPaginator",
    "KmsRuntime",
    "KmsSettings",
    "build_kms_cleaner",
]
