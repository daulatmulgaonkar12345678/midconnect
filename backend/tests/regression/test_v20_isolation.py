"""Disposable-database isolation guarantees for the V20 test suite.

Pure tests: they exercise phase1_db_guard.validate_test_target and the
generated-name / cleanup helpers without connecting to any database. They
are the regression guard for the isolation contract:
- only the explicitly configured disposable target is accepted;
- production database names are rejected;
- generated test database names are unique;
- cleanup runs in `finally`, even when the body raises;
- credentials / connection strings are never printed.
"""
import ast
import os
import re
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "tests"))

from phase1_db_guard import UnsafeTestDatabase, validate_test_target  # noqa: E402

LOOPBACK = "mongodb://127.0.0.1:27117/"
GOOD_NAME = "midconnect_phase1_test"


@pytest.mark.parametrize("name", ["midconnect", "b2b_marketplace", "admin", "config", "local"])
def test_production_and_system_database_names_are_rejected(name):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_target(LOOPBACK, name)


@pytest.mark.parametrize("name", [
    "midconnect_prod", "midconnect_phase1_testX", "b2b_marketplace_phase1_test",
    "midconnect_phase1_test_", "midconnect_phase1_test_ABC",  # uppercase suffix
    "midconnect_phase1_test_abc_def",
])
def test_non_disposable_names_are_rejected(name):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_target(LOOPBACK, name)


@pytest.mark.parametrize("url", [
    "mongodb://db.example.com:27117/",       # non-loopback host
    "mongodb://127.0.0.1:27018/",            # wrong port
    "mongodb://127.0.0.1/",                  # default port (27017), not allowed
    "mongodb+srv://cluster0.example.net/",   # Atlas-style production host
])
def test_non_loopback_or_wrong_port_targets_are_rejected(url):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_target(url, GOOD_NAME)


def test_loopback_disposable_target_is_accepted():
    validate_test_target(LOOPBACK, GOOD_NAME)
    validate_test_target("mongodb://localhost:27117/", GOOD_NAME + "_a1b2c3d4")


def test_generated_names_are_unique_and_accepted():
    import uuid
    names = {GOOD_NAME + "_" + uuid.uuid4().hex[:8] for _ in range(200)}
    assert len(names) == 200, "generated database names must not collide"
    for name in names:
        validate_test_target(LOOPBACK, name)


def test_no_test_reads_the_production_url_or_database_env():
    """Tests must never use MONGO_URL. Only PHASE1_TEST_* may configure a DB."""
    here = os.path.dirname(os.path.abspath(__file__))
    offenders = []
    for fname in ("test_v20_post_verification.py", "test_category_slug_resolution.py",
                  "test_v20_exit_codes.py"):
        src = open(os.path.join(here, fname), encoding="utf-8").read()
        # Tests may mention MONGO_URL only inside comments/docstrings or as the
        # stub environment value that is never connected to; no code reads it.
        for line in src.splitlines():
            code = line.split("#", 1)[0]
            if re.search(r"getenv\(\s*['\"]MONGO_URL['\"]", code) or \
               re.search(r"environ\[\s*['\"]MONGO_URL['\"]", code):
                offenders.append(f"{fname}: {line.strip()}")
    assert offenders == [], "tests must not read MONGO_URL: " + "; ".join(offenders)


_ISO_EXPR = 'DB_NAME + "_" + uuid.uuid4().hex[:8]'


def _norm(text):
    """Normalise an expression so formatting and quote style do not matter."""
    return ast.unparse(ast.parse(text, mode="eval").body)


def _calls(node, name):
    """Calls to `name`, whether invoked bare or as an attribute (x.name(...))."""
    return [
        n for n in ast.walk(node)
        if isinstance(n, ast.Call) and (
            (isinstance(n.func, ast.Name) and n.func.id == name)
            or (isinstance(n.func, ast.Attribute) and n.func.attr == name)
        )
    ]


def _sets_env(node, key, var):
    """True if node contains `<obj>.setenv("key", var)`."""
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "setenv" and len(n.args) == 2
                and isinstance(n.args[0], ast.Constant) and n.args[0].value == key
                and isinstance(n.args[1], ast.Name) and n.args[1].id == var):
            return True
    return False


def _finally_drops_then_closes(fn):
    """True if some finally block runs `await client.drop_database(iso_name)`
    before `client.close()`."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Try) and node.finalbody:
            drop = close = None
            for i, stmt in enumerate(node.finalbody):
                text = ast.unparse(stmt)
                if drop is None and text == "await client.drop_database(iso_name)":
                    drop = i
                if close is None and text == "client.close()":
                    close = i
            if drop is not None and close is not None and drop < close:
                return True
    return False


def test_db_backed_tests_drop_generated_database_in_finally():
    """Every DB-backed V20 test that creates a generated database must drop it
    in a finally block, so cleanup happens even when an assertion fails."""
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "test_v20_post_verification.py"), encoding="utf-8").read()
    # Each generated database is created with iso_name and must be dropped in
    # the finally block of the same go() coroutine.
    assert src.count("iso_name = DB_NAME + \"_\" + uuid.uuid4().hex[:8]") >= 3
    assert src.count("await client.drop_database(iso_name)") >= 3
    for block in src.split("async def go():")[1:]:
        body = block.split("\n    report,")[0].split("\n    rc1,")[0]
        assert "finally:" in body, "DB-backed block must clean up in finally"
        assert "drop_database(iso_name)" in body

    # --- test_v20_coverage_gaps.py: same isolation contract, checked structurally.
    cov_path = os.path.join(here, "test_v20_coverage_gaps.py")
    cov_src = open(cov_path, encoding="utf-8").read()
    cov_tree = ast.parse(cov_src)

    # Generated-name helper must build DB_NAME + "_" + 8-char uuid suffix.
    helper = [n for n in cov_tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "_iso_db_name"]
    assert len(helper) == 1, "_iso_db_name helper must exist exactly once"
    returns = [n for n in ast.walk(helper[0]) if isinstance(n, ast.Return)]
    assert len(returns) == 1 and ast.unparse(returns[0].value) == _norm(_ISO_EXPR), (
        "_iso_db_name must return DB_NAME + '_' + uuid4().hex[:8]")

    db_tests = [
        n for n in cov_tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_") and _calls(n, "validate_test_target")
    ]
    assert len(db_tests) == 4, (
        f"expected exactly 4 DB-backed tests, found {[t.name for t in db_tests]}")

    migration_tests = []
    for fn in db_tests:
        name = fn.name
        # 2. unique generated name per test
        iso_assigns = [
            n for n in ast.walk(fn) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "iso_name" for t in n.targets)
        ]
        assert iso_assigns, f"{name}: must assign iso_name"
        value = iso_assigns[0].value
        generated = (
            (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
             and value.func.id == "_iso_db_name")
            or ast.unparse(value) == _norm(_ISO_EXPR)
        )
        assert generated, f"{name}: iso_name must be a generated DB_NAME + uuid suffix"

        # 3. validate_test_target(URL, iso_name) before any client is created
        validates = [
            c for c in _calls(fn, "validate_test_target")
            if len(c.args) == 2
            and ast.unparse(c.args[0]) == "URL"
            and ast.unparse(c.args[1]) == "iso_name"
        ]
        assert validates, f"{name}: must call validate_test_target(URL, iso_name)"
        clients = _calls(fn, "AsyncIOMotorClient")
        assert clients, f"{name}: must create a MongoDB client"
        assert min(v.lineno for v in validates) < min(c.lineno for c in clients), (
            f"{name}: validate_test_target must run before the client is created")

        # 4. connect via client[iso_name]
        subscripts = [
            n for n in ast.walk(fn) if isinstance(n, ast.Subscript)
            and ast.unparse(n.value) == "client" and ast.unparse(n.slice) == "iso_name"
        ]
        assert subscripts, f"{name}: must use client[iso_name]"

        # 5. finally: drop_database(iso_name) then client.close()
        assert _finally_drops_then_closes(fn), (
            f"{name}: finally must await client.drop_database(iso_name) before client.close()")

        if _calls(fn, "run_migration"):
            migration_tests.append(fn)

    # 6. exactly the two migration tests point DB_NAME at the generated database
    assert len(migration_tests) == 2, (
        f"expected 2 migration tests, found {[t.name for t in migration_tests]}")
    for fn in migration_tests:
        assert _sets_env(fn, "DB_NAME", "iso_name"), (
            f"{fn.name}: must monkeypatch DB_NAME to iso_name")

    # 7. no shared-DB cleanup by deletion or index dropping in this file
    assert "delete_many" not in cov_src, "coverage-gap tests must not use delete_many()"
    assert "drop_index" not in cov_src, "coverage-gap tests must not use drop_index()"

def test_cleanup_runs_in_finally_even_when_body_raises():
    """Behavioural: a finally-style cleanup executes when the body raises."""
    cleaned = []

    def body_with_cleanup():
        try:
            raise AssertionError("simulated assertion failure mid-test")
        finally:
            cleaned.append("dropped")

    with pytest.raises(AssertionError):
        body_with_cleanup()
    assert cleaned == ["dropped"]


def test_validation_errors_do_not_echo_credentials():
    """A sentinel password in the URL userinfo must never appear in any guard
    message: the guard names only the host, port or database name."""
    sentinel = "SENTINEL-PW-7f3a9c"
    for url in (f"mongodb://appuser:{sentinel}@db.example.com:27017/",
                f"mongodb://appuser:{sentinel}@127.0.0.1:27018/"):
        with pytest.raises(UnsafeTestDatabase) as info:
            validate_test_target(url, GOOD_NAME)
        assert sentinel not in str(info.value)
        assert "appuser" not in str(info.value)
