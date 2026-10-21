"""Pure, SDK-free building blocks for CRC (no cloud, notification or service imports)."""

from crc.core.age import (
    AGE_KEYS,
    AgeSpec,
    get_min_age,
    get_retention_age,
    is_old,
    lookup_custom_age_tag,
    parse_literal,
    require_positive_age,
    validated_retention_age,
)

__all__ = [
    "AGE_KEYS",
    "AgeSpec",
    "get_min_age",
    "get_retention_age",
    "is_old",
    "lookup_custom_age_tag",
    "parse_literal",
    "require_positive_age",
    "validated_retention_age",
]
