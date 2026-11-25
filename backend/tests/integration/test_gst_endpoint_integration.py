import asyncio
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from bson import ObjectId
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from routers.enterprise_products import create_enterprise_product_router
from routers.raw_material_router import create_raw_material_router


MONGO_URL = "mongodb://localhost:27017"
TEST_DB_NAME = "midconnect_gst_test"


async def allow_admin():
    return True


def test_gst_verification_through_real_endpoints():
    async def run():
        assert TEST_DB_NAME == "midconnect_gst_test"
        assert TEST_DB_NAME != "midconnect"

        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[TEST_DB_NAME]
        run_id = str(uuid.uuid4())

        product_id = ObjectId()
        category_id = ObjectId()

        sellers = {
            "verified": ObjectId(),
            "unverified": ObjectId(),
            "missing_gst": ObjectId(),
            "legacy_only": ObjectId(),
            "missing_seller": ObjectId(),
        }

        app = FastAPI()
        app.include_router(create_enterprise_product_router(db))
        app.include_router(create_raw_material_router(db, allow_admin))

        try:
            await client.admin.command("ping")

            # Product used by both real endpoints.
            await db.products.insert_one({
                "_id": product_id,
                "gstIntegrationRun": run_id,
                "name": "GST Integration Test Product",
                "slug": f"gst-integration-test-{run_id}",
                "categoryId": category_id,
                "product_type": "raw_material",
                "isActive": True,
            })

            # Current users collection: canonical GST verification.
            await db.users.insert_many([
                {
                    "_id": sellers["verified"],
                    "gstIntegrationRun": run_id,
                    "businessName": "Verified Test Seller",
                    "profile": {"businessName": "Verified Test Seller"},
                    "gst": {"verified": True, "status": "verified"},
                    "isActive": True,
                    "sellerStatus": "active",
                },
                {
                    "_id": sellers["unverified"],
                    "gstIntegrationRun": run_id,
                    "businessName": "Unverified Test Seller",
                    "profile": {"businessName": "Unverified Test Seller"},
                    "gst": {"verified": False},
                    # These must NOT create a GST badge.
                    "isVerified": True,
                    "badgeType": "choice",
                    "isActive": True,
                    "sellerStatus": "active",
                },
                {
                    "_id": sellers["missing_gst"],
                    "gstIntegrationRun": run_id,
                    "businessName": "Missing GST Test Seller",
                    "profile": {"businessName": "Missing GST Test Seller"},
                    "isActive": True,
                    "sellerStatus": "active",
                },
            ])

            # Legacy seller exists, but has no corresponding users record.
            # Even a legacy GST flag must not create a verified GST badge.
            await db.sellers.insert_one({
                "_id": sellers["legacy_only"],
                "gstIntegrationRun": run_id,
                "businessName": "Legacy Only Test Seller",
                "gst": {"verified": True},
                "badgeType": "trusted",
            })

            # Five active listings shared by both endpoint tests.
            listing_docs = []
            for index, (scenario, seller_id) in enumerate(sellers.items()):
                listing_docs.append({
                    "_id": ObjectId(),
                    "gstIntegrationRun": run_id,
                    "productId": product_id,
                    "sellerId": seller_id,
                    "variantId": ObjectId(),
                    "status": "active",
                    "isActive": True,
                    "rate_per_kg": 100 + index,
                    "material_supported": "steel",
                    "pricingTiers": [
                        {"minQuantity": 1, "pricePerUnit": 100 + index}
                    ],
                    "searchableAttributes": {"material": "steel"},
                    "stock": 10,
                    "moq": 1,
                })

            await db.sellerListings.insert_many(listing_docs)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as http:
                # Actual enterprise endpoint.
                enterprise_response = await http.get(
                    f"/products/gst-integration-test-{run_id}/enterprise"
                )
                assert enterprise_response.status_code == 200, (
                    enterprise_response.status_code,
                    enterprise_response.text,
                )

                enterprise = enterprise_response.json()
                enterprise_sellers = {
                    item["sellerId"]: item for item in enterprise["sellers"]
                }

                assert len(enterprise_sellers) == 5

                assert enterprise_sellers[str(sellers["verified"])]["gstVerified"] is True
                assert enterprise_sellers[str(sellers["unverified"])]["gstVerified"] is False
                assert enterprise_sellers[str(sellers["missing_gst"])]["gstVerified"] is False
                assert enterprise_sellers[str(sellers["legacy_only"])]["gstVerified"] is False
                assert enterprise_sellers[str(sellers["missing_seller"])]["gstVerified"] is False

                assert enterprise_sellers[str(sellers["legacy_only"])]["companyName"] == (
                    "Legacy Only Test Seller"
                )
                assert enterprise_sellers[str(sellers["missing_seller"])]["companyName"] == (
                    "Seller"
                )

                # Summary must count eligible users with canonical GST only.
                assert enterprise["summary"]["sellerCount"] == 3
                assert enterprise["summary"]["verifiedSellerCount"] == 1

                # Actual raw-material seller endpoint.
                raw_response = await http.get(
                    f"/sellers/raw-material/{product_id}",
                    params={"material": "steel"},
                )
                assert raw_response.status_code == 200, (
                    raw_response.status_code,
                    raw_response.text,
                )

                raw_sellers = {
                    item["sellerId"]: item for item in raw_response.json()
                }

                assert len(raw_sellers) == 5

                assert raw_sellers[str(sellers["verified"])]["gstVerified"] is True
                assert raw_sellers[str(sellers["unverified"])]["gstVerified"] is False
                assert raw_sellers[str(sellers["missing_gst"])]["gstVerified"] is False
                assert raw_sellers[str(sellers["legacy_only"])]["gstVerified"] is False
                assert raw_sellers[str(sellers["missing_seller"])]["gstVerified"] is False

                assert raw_sellers[str(sellers["legacy_only"])]["sellerName"] == "Seller"
                assert raw_sellers[str(sellers["missing_seller"])]["sellerName"] == "Seller"

        finally:
            # Delete ONLY documents created by this test run.
            for collection_name in (
                "sellerListings",
                "users",
                "sellers",
                "products",
            ):
                await db[collection_name].delete_many({
                    "gstIntegrationRun": run_id
                })

            client.close()

    asyncio.run(run())
