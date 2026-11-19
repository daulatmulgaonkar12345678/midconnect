"""
Phase 1 disposable-database safety guard.

Used by the Phase 1 eligibility tests. Refuses to run against anything that is
not an explicitly disposable, loopback-only, test-named database.
"""
import os
import re
from urllib.parse import urlparse

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORT = 27117
REQUIRED_DB_PATTERN = re.compile(r"^midconnect_phase1_test(_[a-z0-9]{4,12})?$")
FORBIDDEN_DB_NAMES = {"b2b_marketplace", "midconnect", "admin", "config", "local"}


class UnsafeTestDatabase(RuntimeError):
    pass


def validate_test_target(url: str, db_name: str) -> None:
    """Raise UnsafeTestDatabase unless the target is the disposable test instance."""
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise UnsafeTestDatabase(f"host {parsed.hostname!r} is not loopback")
    if parsed.port != ALLOWED_PORT:
        raise UnsafeTestDatabase(f"port {parsed.port!r} is not {ALLOWED_PORT}")
    if db_name in FORBIDDEN_DB_NAMES or not REQUIRED_DB_PATTERN.match(db_name):
        raise UnsafeTestDatabase(f"database name {db_name!r} is not a Phase 1 test database")


def test_db_url_from_env() -> str | None:
    return os.getenv("PHASE1_TEST_MONGO_URL")


def test_db_name_from_env() -> str | None:
    return os.getenv("PHASE1_TEST_DB_NAME")
