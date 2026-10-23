# Copyright (c) Yugabyte, Inc.

"""AWS Elastic IP cleaner package.

`ElasticIpCleaner` (`cleaner.py`) is the registered `aws` / `ip` Cleaner; `ElasticIPs`
(`adapter.py`) is the legacy class `crc.py` uses. The old import path `crc.aws.elastic_ips`
keeps working.
"""

from .adapter import ElasticIPs
from .cleaner import ElasticIpCleaner, build_elastic_ip_cleaner
from .client import ElasticIpClient, ElasticIpRuntime

__all__ = [
    "ElasticIPs",
    "ElasticIpCleaner",
    "ElasticIpClient",
    "ElasticIpRuntime",
    "build_elastic_ip_cleaner",
]
