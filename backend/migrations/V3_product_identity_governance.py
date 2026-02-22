"""
Migration V3: Product Identity Governance - Adds unique compound index and spec hashes

This migration:
1. Computes normalized_spec_hash for all existing products
2. Creates unique compound index: (name, category_id, spec_template_id, normalized_spec_hash)
3. Identifies and reports potential duplicates
4. Does NOT auto-merge duplicates (requires manual review)

Run with: python -m migrations.V3_product_identity_governance
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import hashlib
import json

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "midconnect").strip()


def normalize_spec_value(value):
    """Normalize a single specification value"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower().strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ",".join(sorted([normalize_spec_value(v) for v in value]))
    return str(value).lower().strip()


def normalize_specifications(specs):
    """Normalize all specifications to a canonical form"""
    if not specs:
        return {}
    
    normalized = {}
    for key in sorted(specs.keys()):
        norm_key = key.lower().strip()
        norm_value = normalize_spec_value(specs[key])
        if norm_value:
            normalized[norm_key] = norm_value
    
    return normalized


def generate_spec_hash(specs):
    """Generate SHA256 hash of normalized specifications"""
    normalized = normalize_specifications(specs)
    spec_string = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(spec_string.encode('utf-8')).hexdigest()


async def run_migration():
    """Run the product identity governance migration"""
    print("=" * 60)
    print("MIGRATION V3: Product Identity Governance")
    print("=" * 60)
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    if not MONGO_URL:
        print("ERROR: MONGO_URL not configured")
        return False
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Step 1: Count existing products
        total_products = await db.products.count_documents({})
        print(f"Step 1: Found {total_products} products in collection")
        print()
        
        # Step 2: Compute and store normalized_spec_hash for each product
        print("Step 2: Computing spec hashes for existing products...")
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        async for product in db.products.find({}):
            product_id = product["_id"]
            product_name = product.get("name", "Unknown")
            
            try:
                # Build specs from spec_schema if available
                specs = {}
                if product.get("spec_schema"):
                    for spec in product["spec_schema"]:
                        key = spec.get("key", spec.get("name", ""))
                        if spec.get("type") == "dropdown" and spec.get("options"):
                            # Use empty string as placeholder for dropdown specs
                            # The actual value will come from seller listings
                            specs[key] = ""
                        else:
                            specs[key] = spec.get("default", "")
                
                # If no spec_schema, try to use existing normalized_specs
                if not specs and product.get("normalized_specs"):
                    specs = product["normalized_specs"]
                
                # Generate hash
                spec_hash = generate_spec_hash(specs)
                normalized_specs = normalize_specifications(specs)
                
                # Check if already has the same hash
                if product.get("normalized_spec_hash") == spec_hash:
                    skipped_count += 1
                    continue
                
                # Update product with hash
                await db.products.update_one(
                    {"_id": product_id},
                    {
                        "$set": {
                            "normalized_spec_hash": spec_hash,
                            "normalized_specs": normalized_specs,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                updated_count += 1
                print(f"  ✅ Updated: {product_name} (hash: {spec_hash[:8]}...)")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error processing {product_name}: {e}")
        
        print()
        print(f"Step 2 Complete:")
        print(f"  - Updated: {updated_count}")
        print(f"  - Skipped (already had hash): {skipped_count}")
        print(f"  - Errors: {error_count}")
        print()
        
        # Step 3: Find potential duplicates
        print("Step 3: Checking for potential duplicates...")
        
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "name": {"$toLower": "$name"},
                        "category_id": "$category_id",
                        "spec_hash": "$normalized_spec_hash"
                    },
                    "count": {"$sum": 1},
                    "products": {"$push": {
                        "_id": "$_id",
                        "name": "$name",
                        "created_at": "$created_at"
                    }}
                }
            },
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        duplicates = await db.products.aggregate(pipeline).to_list(length=100)
        
        if duplicates:
            print(f"  ⚠️  Found {len(duplicates)} potential duplicate groups:")
            for dup in duplicates:
                print(f"    - Name: {dup['_id']['name']}")
                print(f"      Category: {dup['_id']['category_id']}")
                print(f"      Count: {dup['count']}")
                for p in dup['products']:
                    print(f"        * {p['_id']} - {p['name']}")
            print()
            print("  NOTE: Duplicates require manual review before merging.")
            print("  Use the deduplication endpoint to merge seller_listings to canonical product.")
        else:
            print("  ✅ No duplicates found!")
        print()
        
        # Step 4: Create unique compound index
        print("Step 4: Creating unique compound index...")
        
        try:
            # Drop existing index if it exists (might have different options)
            try:
                await db.products.drop_index("unique_product_identity")
                print("  Dropped existing index")
            except Exception:
                pass  # Index doesn't exist, that's fine
            
            # Create new unique index with sparse option for legacy data
            await db.products.create_index(
                [
                    ("name", 1),
                    ("category_id", 1),
                    ("spec_template_id", 1),
                    ("normalized_spec_hash", 1)
                ],
                unique=True,
                sparse=True,
                name="unique_product_identity"
            )
            print("  ✅ Created unique compound index: unique_product_identity")
            print("     Fields: (name, category_id, spec_template_id, normalized_spec_hash)")
            
        except Exception as e:
            if "duplicate key error" in str(e).lower() or "E11000" in str(e):
                print(f"  ❌ Cannot create unique index - duplicates exist!")
                print(f"     Error: {e}")
                print("     Please resolve duplicates first using Step 3 data.")
                return False
            raise
        
        print()
        
        # Step 5: Verify index
        print("Step 5: Verifying indexes...")
        indexes = await db.products.index_information()
        
        print("  Current indexes on 'products' collection:")
        for name, info in indexes.items():
            print(f"    - {name}: {info.get('key')}")
            if info.get('unique'):
                print(f"      (UNIQUE)")
        
        print()
        print("=" * 60)
        print("MIGRATION V3 COMPLETE")
        print("=" * 60)
        print(f"End time: {datetime.now(timezone.utc).isoformat()}")
        print()
        print("NEXT STEPS:")
        print("1. The unique index is now enforcing product identity uniqueness")
        print("2. New product creation will check for duplicates automatically")
        print("3. Run deduplication if duplicates were found in Step 3")
        print()
        
        return True
        
    except Exception as e:
        print(f"MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
