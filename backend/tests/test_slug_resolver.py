"""
DETERMINISTIC SLUG RESOLVER TESTS (Batch 5, 2026-11-19)
=======================================================
Contract tests for SlugResolverService.resolve_slug after the Batch 5 fix:

Valid product addresses (resolve):
1. Exact canonical slug — no redirect
2. Case-normalized canonical slug — redirect to canonical
3. ObjectId (24-hex legacy URL) — redirect to canonical
4. Explicit legacySlugs / legacyIds mapping — redirect to canonical

Invalid / unrelated identifiers (must NOT resolve — callers return 404):
- random garbage
- a single shared/common token of a product (the old ANY-token fallback defect)
- a prefix hit on another product's token (e.g. "notebook" -> "Notebooks")
- tokens mixed from several products
- stop-word-only slugs
- city-suffixed canonical slugs (city tolerance removed)
- product names typed as slugs

These are pure unit tests against an in-memory fake of the three Mongo
operations the resolver uses (no network, no database). Database-backed and
HTTP-route coverage lives in tests/regression/test_slug_resolver_deterministic.py.

The legacy live-URL assertions in this file previously pinned the REMOVED
token-based fuzzy matching (partial slugs, word-order, city tolerance,
ANY-token fallback) — the exact behavior Batch 5 outlaws; they were replaced
by the deterministic contract below.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

import pytest
from bson import ObjectId

import os as _os
import sys as _sys

_BACKEND = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
_sys.path.insert(0, _BACKEND)
from services.slug_resolver_service import SlugResolverService

CANONICAL_SLUG = "vfd-vfd-plc-hmi-control-equipments-supplier-india"
CANONICAL_NAME = "VFD"
PRODUCT_ID = ObjectId("6a44cd478b430643bfad1873")
LEGACY_ID = "507f1f77bcf86cd799439011"
LEGACY_SLUG = "vfd-old-name-supplier-india"

NOTEBOOKS_SLUG = "notebooks-office-supplies-supplier-india"
NOTEBOOKS_NAME = "Notebooks"

PRODUCTS = [
    {
        "_id": PRODUCT_ID,
        "name": CANONICAL_NAME,
        "slug": CANONICAL_SLUG,
        "seoTitle": "Compare VFD Prices in India (2026) | UdyogConnect",
        "seoDescription": "Variable frequency drives for smooth motor speed control",
        "legacySlugs": [LEGACY_SLUG],
        "legacyIds": [LEGACY_ID],
    },
    {
        "_id": ObjectId(),
        "name": NOTEBOOKS_NAME,
        "slug": NOTEBOOKS_SLUG,
        "seoTitle": "Notebooks",
        "seoDescription": "Notebooks",
    },
]

PROJECTION = {"_id": 1, "name": 1, "slug": 1, "seoTitle": 1, "seoDescription": 1}


def _match(doc: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    for key, expected in cond.items():
        if key == "$or":
            if not any(_match(doc, sub) for sub in expected):
                return False
        elif isinstance(expected, dict) and "$regex" in expected:
            flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
            actual = doc.get(key)
            if not isinstance(actual, str) or not re.search(expected["$regex"], actual, flags):
                return False
        else:
            actual = doc.get(key)
            if isinstance(actual, list):
                # Mongo: scalar query matches an array field if any element equals it
                if expected not in actual:
                    return False
            elif actual != expected:
                return False
    return True


class FakeCollection:
    """Just enough Mongo surface for resolve_slug: find_one / find().limit().to_list()."""

    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs

    def _filtered(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [d for d in self.docs if _match(d, query)]

    async def find_one(self, query, projection=None):
        matches = self._filtered(query)
        return dict(matches[0]) if matches else None

    def find(self, query, projection=None):
        outer = self

        class Cursor:
            def limit(self, _n):
                return self

            async def to_list(self, _n):
                return [dict(d) for d in outer._filtered(query)]

        return Cursor()


class FakeDB:
    def __init__(self, products: List[Dict[str, Any]]):
        self.products = FakeCollection(products)


def _resolver() -> SlugResolverService:
    return SlugResolverService(FakeDB([dict(p) for p in PRODUCTS]))


def _resolve(identifier: str, **kwargs):
    return asyncio.run(_resolver().resolve_slug(identifier, **kwargs))


# ----------------------------- valid slugs -----------------------------

class TestValidSlugs:
    def test_exact_canonical_slug_resolves_without_redirect(self):
        product, needs_redirect, canonical, all_matches = _resolve(CANONICAL_SLUG)
        assert product is not None
        assert product["slug"] == CANONICAL_SLUG
        assert product["name"] == CANONICAL_NAME
        assert needs_redirect is False
        assert canonical == CANONICAL_SLUG
        assert len(all_matches) == 1

    def test_case_normalized_slug_resolves_with_redirect_to_canonical(self):
        product, needs_redirect, canonical, _ = _resolve(CANONICAL_SLUG.upper())
        assert product is not None
        assert product["slug"] == CANONICAL_SLUG
        assert needs_redirect is True
        assert canonical == CANONICAL_SLUG

    def test_legacy_slug_redirects_to_canonical(self):
        product, needs_redirect, canonical, _ = _resolve(LEGACY_SLUG)
        assert product is not None
        assert product["slug"] == CANONICAL_SLUG
        assert needs_redirect is True
        assert canonical == CANONICAL_SLUG

    def test_legacy_id_redirects_to_canonical(self):
        product, needs_redirect, canonical, _ = _resolve(LEGACY_ID)
        assert product is not None
        assert product["slug"] == CANONICAL_SLUG
        assert needs_redirect is True
        assert canonical == CANONICAL_SLUG

    def test_objectid_url_redirects_to_canonical(self):
        product, needs_redirect, canonical, _ = _resolve(str(PRODUCT_ID))
        assert product is not None
        assert product["slug"] == CANONICAL_SLUG
        assert needs_redirect is True
        assert canonical == CANONICAL_SLUG

    def test_surrounding_whitespace_is_stripped(self):
        product, needs_redirect, canonical, _ = _resolve(f"  {CANONICAL_SLUG}  ")
        assert product is not None
        assert needs_redirect is False
        assert canonical == CANONICAL_SLUG

    def test_return_all_matches_reports_the_single_deterministic_match(self):
        product, _, _, all_matches = _resolve(CANONICAL_SLUG, return_all_matches=True)
        assert product is not None
        assert [p["slug"] for p in all_matches] == [CANONICAL_SLUG]

    def test_second_product_exact_slug_resolves_to_itself(self):
        product, needs_redirect, canonical, _ = _resolve(NOTEBOOKS_SLUG)
        assert product is not None
        assert product["slug"] == NOTEBOOKS_SLUG
        assert needs_redirect is False
        assert canonical == NOTEBOOKS_SLUG


# ----------------------------- invalid slugs -----------------------------

class TestInvalidSlugs:
    def test_random_garbage_slug_returns_none(self):
        product, needs_redirect, canonical, all_matches = _resolve(
            "xyzzy-plugh-zorkmidconnect-42"
        )
        assert product is None
        assert needs_redirect is False
        assert canonical is None
        assert all_matches == []

    def test_single_common_token_does_not_select_a_product(self):
        # "vfd" is a token of the VFD product's name/slug but not a slug:
        # the old resolver resolved it via token matching; it must now 404.
        assert _resolve("vfd")[0] is None

    def test_prefix_hit_on_another_product_token_does_not_resolve(self):
        # "notebook" prefix-matches "Notebooks"; the old ANY-token fallback
        # returned the unrelated Notebooks product. Regression for the exact
        # reported defect (invalid URL -> HTTP 200 Notebooks page).
        assert _resolve("notebook")[0] is None
        assert _resolve("notebook-xyzzyq-plugh")[0] is None

    def test_tokens_from_unrelated_products_do_not_merge(self):
        assert _resolve("vfd-notebooks-supplier-india")[0] is None

    def test_stop_word_only_slug_returns_none(self):
        assert _resolve("buy-online-best-supplier-india")[0] is None

    def test_city_suffixed_canonical_slug_returns_none(self):
        # City tolerance was part of the removed fuzzy matching; canonical
        # city pages live on /products/{slug}/in/{city}, not on mutated slugs.
        assert _resolve(f"{CANONICAL_SLUG}-mumbai")[0] is None

    def test_product_name_typed_as_slug_returns_none(self):
        assert _resolve("vfd plc hmi control equipments")[0] is None
        assert _resolve("notebooks office supplies")[0] is None

    def test_unknown_slug_of_similar_shape_returns_none(self):
        assert _resolve("vfd-vfd-plc-hmi-control-equipments-supplier-indy")[0] is None

    def test_empty_identifier_returns_none(self):
        assert _resolve("")[0] is None


# ----------------------------- integration regression -----------------------------

class TestUnresolvedInvalidSlugs:
    def test_invalid_slug_never_returns_a_product_payload(self):
        for bad in (
            "vfd",
            "notebook",
            "buy-online-best-supplier-india",
            "xyzzy-plugh-zorkmidconnect-42",
            f"{CANONICAL_SLUG}-mumbai",
        ):
            product, _, _, _ = _resolve(bad)
            assert product is None, f"invalid slug unexpectedly resolved: {bad}"
