"""
GST verification contract — regression tests (no database, no network).

Canonical contract:
    gst = {"number": ..., "status": "pending" | "verified" | "rejected", "verified": bool}

Covers:
- admin GST approve/reject handlers write the canonical fields and unset gst.isVerified;
- the pending GST queue filter excludes verified and rejected sellers;
- SellerGovernanceService.isGstVerified derives only from gst.verified is True;
- enterprise and raw-material seller responses expose an explicit gstVerified boolean
  and use "Seller" (never "Verified Seller") as the missing-name fallback.

The handlers are the production closures; the database is a minimal in-memory
stand-in that applies the same $set / $unset / query operators these handlers use.
"""
import asyncio
import copy
import inspect
import os
import re
import sys

import pytest
from bson import ObjectId
from fastapi import APIRouter

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, _BACKEND)


# ---------------------------------------------------------------------------
# Minimal in-memory users collection (only the operators the handlers use)
# ---------------------------------------------------------------------------
def _get(doc, dotted):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def _matches(doc, query):
    for key, cond in query.items():
        val, present = _get(doc, key)
        if isinstance(cond, dict) and any(k.startswith("$") for k in cond):
            for op, arg in cond.items():
                if op == "$exists":
                    if present != arg:
                        return False
                elif op == "$ne":
                    if present and val == arg:
                        return False
                    if not present and arg is None:
                        return False
                elif op == "$nin":
                    if present and val in arg:
                        return False
                elif op == "$in":
                    if not (present and val in arg):
                        return False
                else:
                    raise AssertionError(f"unsupported operator {op}")
        else:
            if not present:
                return False
            if val == cond:
                continue
            # Mongo equality on an array field matches when any element equals cond.
            if isinstance(val, list) and cond in val:
                continue
            return False
    return True


class _UpdateResult:
    def __init__(self, n):
        self.modified_count = n


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def limit(self, n):
        return _Cursor(self._docs[:n])

    async def to_list(self, n):
        return list(self._docs)


class FakeUsers:
    def __init__(self, docs):
        self.docs = docs

    async def update_one(self, query, update):
        for doc in self.docs:
            if _matches(doc, query):
                for k, v in update.get("$set", {}).items():
                    _set(doc, k, copy.deepcopy(v))
                for k in update.get("$unset", {}):
                    _unset(doc, k)
                return _UpdateResult(1)
        return _UpdateResult(0)

    def find(self, query, projection=None):
        return _Cursor([copy.deepcopy(d) for d in self.docs if _matches(d, query)])

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if _matches(d, query):
                return copy.deepcopy(d)
        return None


def _set(doc, dotted, value):
    parts = dotted.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _unset(doc, dotted):
    parts = dotted.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur.get(part, {})
    cur.pop(parts[-1], None)


class FakeDb:
    def __init__(self, users):
        self.users = FakeUsers(users)


class _Admin:
    _id = ObjectId()


def _route(router: APIRouter, name: str):
    for r in router.routes:
        if getattr(r, "name", None) == name:
            return r.endpoint
    raise AssertionError(f"route {name} not found")


class _NoopAudit:
    def __init__(self, db):
        pass

    async def log_gst_decision(self, **kwargs):
        return None


@pytest.fixture
def gov(monkeypatch):
    import services.admin_audit_service as audit_mod

    monkeypatch.setattr(audit_mod, "AdminAuditService", _NoopAudit)
    import routers.admin_governance_router as gov_mod

    monkeypatch.setattr(gov_mod, "AdminAuditService", _NoopAudit, raising=False)
    return gov_mod


def _seller(**gst):
    base = {"number": "27ABCDE1234F1Z5", "documentUrl": "https://x/doc.pdf"}
    base.update(gst)
    return {"_id": ObjectId(), "roles": "seller", "email": "s@example.com",
            "profile": {"businessName": "Acme"}, "gst": base}


def _build(gov_mod, db):
    return gov_mod.create_admin_governance_router(db, lambda: _Admin())


# ---------------------------------------------------------------------------
# Approval / rejection write the canonical contract
# ---------------------------------------------------------------------------
def test_approve_writes_canonical_fields_and_removes_legacy(gov):
    seller = _seller(isVerified=False, status="pending")
    db = FakeDb([seller])
    router = _build(gov, db)
    handler = _route(router, "approve_gst")

    from fastapi import Request
    req = type("R", (), {"client": None})()
    admin = _Admin._id
    res = asyncio.run(handler(str(seller["_id"]), req, current_user={"_id": admin}))

    assert res["success"] is True
    stored = db.users.docs[0]["gst"]
    assert stored["verified"] is True
    assert stored["status"] == "verified"
    assert "isVerified" not in stored
    assert stored["verifiedAt"] is not None
    assert stored["verifiedBy"] == admin
    assert stored["number"] == "27ABCDE1234F1Z5"


def test_approve_never_writes_approved_status(gov):
    seller = _seller(status="pending")
    db = FakeDb([seller])
    handler = _route(_build(gov, db), "approve_gst")
    asyncio.run(handler(str(seller["_id"]), type("R", (), {"client": None})(), current_user={"_id": _Admin._id}))
    assert db.users.docs[0]["gst"]["status"] != "approved"


def test_reject_writes_canonical_fields_and_keeps_reason(gov):
    seller = _seller(isVerified=True, status="verified", verified=True)
    db = FakeDb([seller])
    handler = _route(_build(gov, db), "reject_gst")
    from routers.admin_governance_router import GstDecisionRequest

    asyncio.run(handler(str(seller["_id"]), GstDecisionRequest(reason="Mismatch in GSTIN"),
                        type("R", (), {"client": None})(), current_user={"_id": _Admin._id}))

    stored = db.users.docs[0]["gst"]
    assert stored["verified"] is False
    assert stored["status"] == "rejected"
    assert "isVerified" not in stored
    assert stored["rejectionReason"] == "Mismatch in GSTIN"
    assert stored["rejectedAt"] is not None


# ---------------------------------------------------------------------------
# Pending queue excludes verified and rejected sellers
# ---------------------------------------------------------------------------
def test_pending_queue_excludes_verified_and_rejected(gov):
    pending = _seller(status="pending", verified=False)
    verified = _seller(status="verified", verified=True)
    rejected = _seller(status="rejected", verified=False)
    legacy_verified = _seller(isVerified=True)  # legacy field alone must not hide/show; canonical missing
    db = FakeDb([pending, verified, rejected, legacy_verified])
    handler = _route(_build(gov, db), "get_pending_gst_verifications")

    out = asyncio.run(handler(limit=50, current_user={"_id": ObjectId()}))
    ids = {p["sellerId"] for p in out["pendingVerifications"]}

    assert str(pending["_id"]) in ids
    assert str(verified["_id"]) not in ids
    assert str(rejected["_id"]) not in ids
    # Canonical gst.verified is absent on the legacy-only seller, so it is still pending.
    assert str(legacy_verified["_id"]) in ids


def test_pending_queue_query_uses_canonical_fields_only():
    src = open(os.path.join(_BACKEND, "routers", "admin_governance_router.py"),
               encoding="utf-8").read()
    body = src[src.index("async def get_pending_gst_verifications"):]
    body = body[: body.index("return router")]
    assert "gst.verified" in body
    assert "gst.isVerified" not in body


# ---------------------------------------------------------------------------
# Seller governance: isGstVerified derives only from gst.verified is True
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "gst, expected",
    [
        ({"verified": True}, True),
        ({"verified": False}, False),
        ({}, False),
        ({"isVerified": True}, False),  # legacy alone must not verify
        ({"verified": "true"}, False),  # only boolean True counts
        ({"status": "verified"}, False),  # status alone must not verify
    ],
)
def test_governance_is_gst_verified_canonical(gst, expected):
    from services.seller_governance_service import SellerGovernanceService

    seller = {"_id": ObjectId(), "roles": ["seller"], "status": "active", "gst": gst}
    svc = SellerGovernanceService(FakeDb([seller]))
    status = asyncio.run(svc.get_seller_status(seller["_id"]))
    assert status["isGstVerified"] is expected


def test_governance_missing_seller_is_unverified():
    from services.seller_governance_service import SellerGovernanceService

    svc = SellerGovernanceService(FakeDb([]))
    status = asyncio.run(svc.get_seller_status(ObjectId()))
    assert status["exists"] is False


def test_governance_projection_uses_canonical_field():
    src = open(os.path.join(_BACKEND, "services", "seller_governance_service.py"),
               encoding="utf-8").read()
    assert "gst.isVerified" not in src
    assert '.get("verified") is True' in src


# ---------------------------------------------------------------------------
# Enterprise and raw-material response mapping
# ---------------------------------------------------------------------------
def test_enterprise_pipeline_projection_derives_gst_only_from_canonical():
    src = open(os.path.join(_BACKEND, "routers", "enterprise_products.py"),
               encoding="utf-8").read()
    assert '"$sellerData.gst.verified"' in src
    assert "gstVerified" in src
    assert "Verified Seller" not in src
    assert "isVerified" not in src


def test_enterprise_seller_profile_mapping_is_explicit_bool():
    # The listing response mapping must coerce to a strict bool.
    src = open(os.path.join(_BACKEND, "routers", "enterprise_products.py"),
               encoding="utf-8").read()
    assert re.search(r'"gstVerified":\s*seller_profile\.get\("gstVerified"\)\s*is True', src)
    assert re.search(r'r\["gstVerified"\]\s*=\s*seller_data\.get\("gstVerified"\)\s*is True', src)


def test_raw_material_projection_uses_canonical_and_seller_fallback():
    src = open(os.path.join(_BACKEND, "routers", "raw_material_router.py"),
               encoding="utf-8").read()
    assert '"$seller.gst.verified"' in src
    assert '"gstVerified": l.get("gstVerified") is True' in src
    assert '"Verified Seller"' not in src
    assert 'l.get("sellerName", "Seller")' in src


def test_enterprise_seller_missing_record_defaults_false():
    # Mirror of the fallback dict used when a seller record is missing.
    src = open(os.path.join(_BACKEND, "routers", "enterprise_products.py"),
               encoding="utf-8").read()
    assert '{"businessName": "Seller", "badgeType": "none", "gstVerified": False}' in src
