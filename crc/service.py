# Copyright (c) Yugabyte, Inc.

import datetime
import os
from typing import Dict, List, Optional, Tuple, Union

from crc.core import age as core_age
from crc.utils import init_logging


class Service:
    """
    Service class provides a method to check if a resource is older than a specified age threshold.
    It also sets up logging for the class.

    Age handling lives in ``crc.core.age``; the methods below delegate to it.
    """

    # Directory where logs will be stored
    logs_dir = "logs"

    # File name of the log file
    logs_file = "crc.log"
    AGE_KEYS = core_age.AGE_KEYS

    def __init__(self) -> None:
        """
        Initializes the Client class and sets up logging.
        """
        log_filename = os.path.join(self.logs_dir, self.logs_file)
        init_logging(log_filename)

    def require_positive_age(
        self, age: Optional[Union[Dict[str, int], int]], label: str = "age"
    ) -> Dict[str, int]:
        """
        Require a non-empty, >0 age gate. ``is_old({})`` returns True, so
        destructive modules must reject missing/zero ages in ``__init__``.
        """
        return core_age.require_positive_age(age, label)

    def _lookup_custom_age_tag(
        self,
        tags: Union[Dict[str, str], List[Dict[str, str]]],
        key: str,
    ) -> Tuple[bool, Optional[str]]:
        """Return ``(present, raw_value)`` for ``custom_age_tag_key``."""
        return core_age.lookup_custom_age_tag(tags, key)

    def validated_retention_age(
        self,
        tags: Union[Dict[str, str], List[Dict[str, str]]],
        key: str,
    ) -> Optional[Dict[str, int]]:
        """
        Parse ``custom_age_tag_key`` and require a positive age.

        Returns ``None`` when the tag is absent (caller should use ``--age``).
        Raises ``ValueError`` when the tag is present but empty, unparseable,
        invalid, or zero — callers must skip the resource (fail closed), not
        fall back to ``--age``.
        """
        return core_age.validated_retention_age(tags, key)

    def get_min_age(self, dict1, dict2):
        """
        Return whichever of two ``days``/``hours`` dicts is the lesser duration
        (ties return ``dict2``).
        """
        return core_age.get_min_age(dict1, dict2)

    def is_old(
        self,
        age: Union[Dict[str, int], int],
        current_time: datetime.datetime,
        creation_time: datetime.datetime,
    ) -> bool:
        """
        Determines if a resource is older than a specified age threshold.

        ``age`` is an int (days) or a dict with 'days' and/or 'hours'. An empty age
        returns True. ``MAX_AGE`` can replace a longer threshold.
        """
        return core_age.is_old(age, current_time, creation_time)

    def _parse_literal(self, value: str, key: str) -> Optional[str]:
        """Helper function to safely parse a literal value."""
        return core_age.parse_literal(value, key)

    def get_retention_age(
        self, tags: Union[Dict[str, str], List[Dict[str, str]]], key: str
    ) -> Optional[str]:
        """
        Retrieve the parsed custom age tag value from the provided tags, or None
        when absent, empty or unparseable (fail open).
        """
        return core_age.get_retention_age(tags, key)
