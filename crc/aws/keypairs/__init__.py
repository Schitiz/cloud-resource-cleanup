# Copyright (c) Yugabyte, Inc.

"""AWS EC2 key pair cleaner package.

`KeyPairCleaner` (`cleaner.py`) is the registered `aws` / `keypair` Cleaner; `KeyPairs`
(`adapter.py`) is the legacy class `crc.py` uses. The old import path `crc.aws.keypairs`
keeps working.
"""

from .adapter import KeyPairs
from .cleaner import KeyPairCleaner, build_keypair_cleaner
from .client import KeyPairClient, KeyPairRuntime

__all__ = [
    "KeyPairCleaner",
    "KeyPairClient",
    "KeyPairRuntime",
    "KeyPairs",
    "build_keypair_cleaner",
]
