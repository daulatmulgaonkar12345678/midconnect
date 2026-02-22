"""
Backend Utils Package

Contains utility functions used across the application.
"""

from utils.identity import (
    require_objectid,
    to_objectid_safe,
    validate_objectid_str,
    is_valid_objectid,
    serialize_objectid,
    validate_objectid_batch,
    detect_legacy_fields,
    assert_no_legacy_fields,
    assert_objectid_type,
    IdentityError,
)

__all__ = [
    "require_objectid",
    "to_objectid_safe",
    "validate_objectid_str",
    "is_valid_objectid",
    "serialize_objectid",
    "validate_objectid_batch",
    "detect_legacy_fields",
    "assert_no_legacy_fields",
    "assert_objectid_type",
    "IdentityError",
]
