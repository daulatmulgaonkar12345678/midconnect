"""
Sitemap product source — regression tests (disposable MongoDB only).

Runs against PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME. Skips when unset.
Each test uses a unique tag and deletes only the documents it inserted.
"""
import asyncio
import os
import uuid

import pytest
from bson import ObjectId

import os as _os
import sys as _sys
_BACKEND = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
_sys.path.insert(0, _BACKEND)
_sys.path.insert(0, _os.path.join(_BACKEND, "tests"))
from phase1_db_guard import validate_test_target
from services.sitemap_product_service import fetch_sitemap_products, SitemapProductOverflowError

URL = os.getenv("PHASE1_TEST_MONGO_URL")
DB_NAME = os.getenv("PHASE1_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(
    not (URL and DB_NAME),
    reason="PHASE1_TEST_MONGO_URL / PHASE1_TEST_DB_NAME not set (disposable DB required)",
)


def _run(coro):
    return asyncio.run(coro)


def _product(tag, slug, **fields):
    doc = {"_id": ObjectId(), "tag": tag, "name": "p", "slug": slug, "isActive": True}
    doc.update(fields)
    return doc


async def _visible_slugs(build):
    """Insert via build(db, tag); return the visible slugs for that tag. Always cleans up."""
    from motor.motor_asyncio import AsyncIOMotorClient

    validate_test_target(URL, DB_NAME)
    client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    tag = "smp-" + uuid.uuid4().hex[:8]
    try:
        await build(db, tag)
        rows = await fetch_sitemap_products(db, 1000)
        return [r["productSlug"] for r in rows if r["productSlug"].startswith(tag)], tag
    finally:
        await db.products.delete_many({"tag": tag})
        await db.sellerListings.delete_many({"tag": tag})
        client.close()


def test_active_product_without_listings_is_listed():
    async def build(db, tag):
        await db.products.insert_one(_product(tag, f"{tag}-no-listings"))

    slugs, tag = _run(_visible_slugs(build))
    assert slugs == [f"{tag}-no-listings"]


def test_product_with_only_inactive_listings_is_listed():
    async def build(db, tag):
        pid = ObjectId()
        await db.products.insert_one(_product(tag, f"{tag}-inactive-listings", _id=pid))
        await db.sellerListings.insert_one({
            "tag": tag, "status": "inactive", "productId": pid, "sellerId": ObjectId(), "city": "pune",
        })

    slugs, tag = _run(_visible_slugs(build))
    assert slugs == [f"{tag}-inactive-listings"]


def test_product_with_eligible_listing_is_listed_once():
    async def build(db, tag):
        pid = ObjectId()
        await db.products.insert_one(_product(tag, f"{tag}-eligible", _id=pid))
        await db.sellerListings.insert_one({
            "tag": tag, "status": "active", "productId": pid, "sellerId": ObjectId(), "city": "pune",
        })

    slugs, tag = _run(_visible_slugs(build))
    assert slugs == [f"{tag}-eligible"]


def test_inactive_product_is_not_listed():
    async def build(db, tag):
        await db.products.insert_one(_product(tag, f"{tag}-off", isActive=False))

    slugs, _ = _run(_visible_slugs(build))
    assert slugs == []


@pytest.mark.parametrize("deleted_fields", [
    {"deletedAt": "2024-01-01T00:00:00Z"},
    {"isDeleted": True},
])
def test_deleted_product_is_not_listed(deleted_fields):
    async def build(db, tag):
        await db.products.insert_one(_product(tag, f"{tag}-deleted", **deleted_fields))

    slugs, _ = _run(_visible_slugs(build))
    assert slugs == []


@pytest.mark.parametrize("bad_slug", ["", "Has Upper", "under_score", "trailing-", "-leading", "double--hyphen"])
def test_non_canonical_slug_is_not_listed(bad_slug):
    from motor.motor_asyncio import AsyncIOMotorClient

    async def run():
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        tag = "smp-" + uuid.uuid4().hex[:8]
        try:
            await db.products.insert_one(_product(tag, bad_slug))
            # Compare against the FULL service output: no tag-based filtering of the result.
            rows = await fetch_sitemap_products(db, 1000)
            return [r["productSlug"] for r in rows if r["productSlug"] == bad_slug]
        finally:
            await db.products.delete_many({"tag": tag})
            client.close()

    assert _run(run()) == []


def test_existing_eligible_product_slug_is_emitted_unchanged():
    async def build(db, tag):
        await db.products.insert_one(_product(tag, f"{tag}-steel-pipe-1"))

    slugs, tag = _run(_visible_slugs(build))
    assert slugs == [f"{tag}-steel-pipe-1"]


def test_overflow_raises_instead_of_truncating():
    from motor.motor_asyncio import AsyncIOMotorClient

    async def go():
        validate_test_target(URL, DB_NAME)
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        tag = "smp-" + uuid.uuid4().hex[:8]
        try:
            await db.products.insert_many([_product(tag, f"{tag}-{i}") for i in range(3)])
            with pytest.raises(SitemapProductOverflowError):
                await fetch_sitemap_products(db, 2)
        finally:
            await db.products.delete_many({"tag": tag})
            client.close()

    _run(go())
