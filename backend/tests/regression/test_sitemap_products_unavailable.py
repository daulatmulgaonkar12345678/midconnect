"""
/api/seo/sitemap-products — database-unavailable HTTP test (isolated).

Kept in its own module because it reloads the app against a closed loopback
port, which would orphan the Motor client used by the other HTTP tests.
Uses a real refused connection (no mocks). No disposable DB needed for the
unavailable target itself; the guard still checks the module's target env.
"""
import os
import socket
import sys

import pytest
from fastapi.testclient import TestClient

import os as _os
import sys as _sys
_BACKEND = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
_sys.path.insert(0, _BACKEND)
_sys.path.insert(0, _os.path.join(_BACKEND, "tests"))
from phase1_db_guard import validate_test_target

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)

ROUTE = "/api/seo/sitemap-products"


def _closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_database_unavailable_returns_generic_503(monkeypatch):
    """Real connection refusal on a closed loopback port; no mocks."""
    validate_test_target(URL, DB_NAME)
    unreachable = f"mongodb://127.0.0.1:{_closed_port()}/"
    os.environ["MONGO_URL"] = unreachable
    os.environ["DB_NAME"] = DB_NAME
    os.environ.setdefault("ENVIRONMENT", "test")
    for name in [m for m in sys.modules if m == "server" or m.startswith("server.")]:
        del sys.modules[name]
    import server  # noqa: WPS433
    with TestClient(server.app, raise_server_exceptions=False) as client:
        resp = client.get(ROUTE)
    assert resp.status_code == 503
    assert resp.json() == {"detail": "Sitemap product data temporarily unavailable"}
    text = resp.text.lower()
    # No connection details, host, port or traceback may leak.
    assert "127.0.0.1" not in text
    assert "traceback" not in text
    assert "serverselection" not in text
