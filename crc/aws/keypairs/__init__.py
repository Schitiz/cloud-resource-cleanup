# Copyright (c) Yugabyte, Inc.

"""AWS EC2 key pair cleaner package.

`KeyPairCleaner` (`cleaner.py`) is the registered `aws` / `keypair` Cleaner; `crc/cli` runs it
through `crc.core.engine` (the `KeyPairs` adapter is gone, ENG-0).
"""

from .cleaner import KeyPairCleaner, build_keypair_cleaner
from .client import KeyPairClient

__all__ = [
    "KeyPairCleaner",
    "KeyPairClient",
    "build_keypair_cleaner",
]
