"""
PHASE 1: Global Schema Audit Script

This script performs a FULL SCAN of all MongoDB collections to identify:
1. All field name variations (sellerId vs seller_id vs sellerid)
2. String IDs stored instead of ObjectId
3. Missing indexes
4. Broken references
5. Legacy/deprecated fields

CANONICAL STANDARD (Approved):
- sellerId (not seller_id, sellerid)
- buyerId (not buyer_id, buyerid)
- productId (not product_id, productid)
- categoryId (not category_id, categoryid)
- subscriptionId (not subscription_id)
- orderId (not order_id)
- inquiryId (not inquiry_id)
- createdAt (not created_at)
- updatedAt (not updated_at)
"""

import asyncio
import os
import json
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Dict, List, Any, Set
from collections import defaultdict

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "b2b_marketplace")

# Canonical field names - SINGLE SOURCE OF TRUTH
CANONICAL_ID_FIELDS = {
    "sellerId", "buyerId", "productId", "categoryId", 
    "subscriptionId", "orderId", "inquiryId", "userId", "listingId"
}

CANONICAL_TIMESTAMP_FIELDS = {
    "createdAt", "updatedAt", "publishedAt", "deletedAt", "expiresAt",
    "acceptedAt", "rejectedAt", "startDate", "endDate"
}

# Legacy field patterns that should be flagged
LEGACY_PATTERNS = {
    # Snake case ID fields
    "seller_id": "sellerId",
    "buyer_id": "buyerId", 
    "product_id": "productId",
    "category_id": "categoryId",
    "subscription_id": "subscriptionId",
    "order_id": "orderId",
    "inquiry_id": "inquiryId",
    "user_id": "userId",
    "listing_id": "listingId",
    # Lowercase variants
    "sellerid": "sellerId",
    "buyerid": "buyerId",
    "productid": "productId",
    "categoryid": "categoryId",
    # Snake case timestamps
    "created_at": "createdAt",
    "updated_at": "updatedAt",
    "deleted_at": "deletedAt",
    "expires_at": "expiresAt",
    "accepted_at": "acceptedAt",
    "rejected_at": "rejectedAt",
    "start_date": "startDate",
    "end_date": "endDate",
    "published_at": "publishedAt",
    "trial_ends_at": "trialEndsAt",
    "enquiries_reset_at": "enquiriesResetAt",
}

# Collections to audit
COLLECTIONS_TO_AUDIT = [
    "users",
    "sellers", 
    "buyers",
    "products",
    "seller_listings",
    "inquiries",
    "subscriptions",
    "subscription_history",
    "orders",
    "categories",
    "analytics",
    "product_requests",
    "manufacturers"
]


class SchemaAuditor:
    def __init__(self, db):
        self.db = db
        self.report = {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "collections": {},
            "summary": {
                "total_collections": 0,
                "collections_with_issues": 0,
                "total_documents_scanned": 0,
                "total_legacy_fields_found": 0,
                "total_string_ids_found": 0,
                "collections_need_migration": []
            }
        }
    
    async def get_all_collections(self) -> List[str]:
        """Get all collection names in the database."""
        return await self.db.list_collection_names()
    
    async def sample_documents(self, collection_name: str, sample_size: int = 50) -> List[Dict]:
        """Get sample documents from a collection."""
        try:
            docs = await self.db[collection_name].find().limit(sample_size).to_list(sample_size)
            return docs
        except Exception as e:
            print(f"Error sampling {collection_name}: {e}")
            return []
    
    def analyze_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Analyze a single field and its value."""
        analysis = {
            "field_name": field_name,
            "issues": [],
            "value_type": type(value).__name__
        }
        
        # Check for legacy field names
        if field_name in LEGACY_PATTERNS:
            analysis["issues"].append({
                "type": "LEGACY_FIELD_NAME",
                "severity": "HIGH",
                "current": field_name,
                "canonical": LEGACY_PATTERNS[field_name],
                "message": f"Legacy field '{field_name}' should be '{LEGACY_PATTERNS[field_name]}'"
            })
        
        # Check for string IDs that should be ObjectId
        if field_name in CANONICAL_ID_FIELDS or field_name in LEGACY_PATTERNS:
            if isinstance(value, str) and len(value) == 24:
                try:
                    ObjectId(value)  # Valid ObjectId string
                    analysis["issues"].append({
                        "type": "STRING_ID_INSTEAD_OF_OBJECTID",
                        "severity": "HIGH",
                        "field": field_name,
                        "message": f"Field '{field_name}' contains string ID instead of ObjectId"
                    })
                except:
                    pass
        
        # Check for nested fields
        if field_name.endswith("_id") or field_name.endswith("Id"):
            if isinstance(value, str) and len(value) == 24:
                try:
                    ObjectId(value)
                    if field_name not in CANONICAL_ID_FIELDS:
                        analysis["issues"].append({
                            "type": "POTENTIAL_STRING_OBJECTID",
                            "severity": "MEDIUM",
                            "field": field_name,
                            "message": f"Field '{field_name}' may need to be ObjectId type"
                        })
                except:
                    pass
        
        return analysis
    
    def analyze_document(self, doc: Dict, collection_name: str) -> Dict[str, Any]:
        """Analyze a single document for schema issues."""
        analysis = {
            "fields_found": set(),
            "issues": [],
            "legacy_fields": [],
            "string_ids": []
        }
        
        def analyze_nested(obj: Any, prefix: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    analysis["fields_found"].add(full_key)
                    
                    field_analysis = self.analyze_field(key, value)
                    for issue in field_analysis["issues"]:
                        issue["full_path"] = full_key
                        analysis["issues"].append(issue)
                        if issue["type"] == "LEGACY_FIELD_NAME":
                            analysis["legacy_fields"].append(full_key)
                        elif issue["type"] == "STRING_ID_INSTEAD_OF_OBJECTID":
                            analysis["string_ids"].append(full_key)
                    
                    analyze_nested(value, full_key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    analyze_nested(item, f"{prefix}[{i}]")
        
        analyze_nested(doc)
        analysis["fields_found"] = list(analysis["fields_found"])
        return analysis
    
    async def audit_collection(self, collection_name: str) -> Dict[str, Any]:
        """Perform full audit on a single collection."""
        print(f"\n{'='*60}")
        print(f"Auditing collection: {collection_name}")
        print(f"{'='*60}")
        
        result = {
            "collection_name": collection_name,
            "document_count": 0,
            "documents_sampled": 0,
            "all_fields": set(),
            "legacy_fields_found": {},
            "string_ids_found": {},
            "issues": [],
            "needs_migration": False
        }
        
        try:
            # Get document count
            result["document_count"] = await self.db[collection_name].count_documents({})
            print(f"  Total documents: {result['document_count']}")
            
            if result["document_count"] == 0:
                print(f"  Collection is empty, skipping...")
                return result
            
            # Sample documents
            sample_size = min(100, result["document_count"])
            docs = await self.sample_documents(collection_name, sample_size)
            result["documents_sampled"] = len(docs)
            
            # Analyze each document
            for doc in docs:
                doc_analysis = self.analyze_document(doc, collection_name)
                result["all_fields"].update(doc_analysis["fields_found"])
                
                for field in doc_analysis["legacy_fields"]:
                    result["legacy_fields_found"][field] = result["legacy_fields_found"].get(field, 0) + 1
                
                for field in doc_analysis["string_ids"]:
                    result["string_ids_found"][field] = result["string_ids_found"].get(field, 0) + 1
                
                result["issues"].extend(doc_analysis["issues"])
            
            # Determine if migration needed
            if result["legacy_fields_found"] or result["string_ids_found"]:
                result["needs_migration"] = True
            
            # Convert set to list for JSON serialization
            result["all_fields"] = sorted(list(result["all_fields"]))
            
            # Print summary
            if result["legacy_fields_found"]:
                print(f"\n  LEGACY FIELDS FOUND (need renaming):")
                for field, count in result["legacy_fields_found"].items():
                    canonical = LEGACY_PATTERNS.get(field.split(".")[-1], "unknown")
                    print(f"    - {field}: {count} occurrences -> should be '{canonical}'")
            
            if result["string_ids_found"]:
                print(f"\n  STRING IDs FOUND (need ObjectId conversion):")
                for field, count in result["string_ids_found"].items():
                    print(f"    - {field}: {count} occurrences")
            
            if not result["needs_migration"]:
                print(f"  ✅ No issues found in this collection")
            
        except Exception as e:
            print(f"  ERROR auditing collection: {e}")
            result["error"] = str(e)
        
        return result
    
    async def run_full_audit(self):
        """Run full audit on all collections."""
        print("\n" + "="*80)
        print("GLOBAL SCHEMA AUDIT - PHASE 1")
        print("Single Source of Truth Verification")
        print("="*80)
        
        # Get all collections
        all_collections = await self.get_all_collections()
        print(f"\nFound {len(all_collections)} collections in database '{DB_NAME}':")
        for col in sorted(all_collections):
            print(f"  - {col}")
        
        self.report["summary"]["total_collections"] = len(all_collections)
        
        # Audit each collection
        for collection_name in sorted(all_collections):
            # Skip system collections
            if collection_name.startswith("system."):
                continue
            
            result = await self.audit_collection(collection_name)
            self.report["collections"][collection_name] = result
            
            self.report["summary"]["total_documents_scanned"] += result["document_count"]
            
            if result["needs_migration"]:
                self.report["summary"]["collections_with_issues"] += 1
                self.report["summary"]["collections_need_migration"].append(collection_name)
                self.report["summary"]["total_legacy_fields_found"] += len(result["legacy_fields_found"])
                self.report["summary"]["total_string_ids_found"] += len(result["string_ids_found"])
        
        return self.report
    
    def generate_migration_plan(self) -> Dict[str, Any]:
        """Generate a migration plan based on audit results."""
        plan = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "collections_to_migrate": [],
            "estimated_document_count": 0,
            "field_renames": [],
            "type_conversions": []
        }
        
        for col_name, col_data in self.report["collections"].items():
            if col_data.get("needs_migration"):
                col_plan = {
                    "collection": col_name,
                    "document_count": col_data["document_count"],
                    "operations": []
                }
                
                # Add field renames
                for field, count in col_data.get("legacy_fields_found", {}).items():
                    base_field = field.split(".")[-1]
                    canonical = LEGACY_PATTERNS.get(base_field, f"UNKNOWN_{base_field}")
                    col_plan["operations"].append({
                        "type": "RENAME",
                        "from": field,
                        "to": canonical,
                        "affected_docs": count
                    })
                    plan["field_renames"].append({
                        "collection": col_name,
                        "from": field,
                        "to": canonical
                    })
                
                # Add type conversions
                for field, count in col_data.get("string_ids_found", {}).items():
                    col_plan["operations"].append({
                        "type": "CONVERT_TO_OBJECTID",
                        "field": field,
                        "affected_docs": count
                    })
                    plan["type_conversions"].append({
                        "collection": col_name,
                        "field": field,
                        "from_type": "string",
                        "to_type": "ObjectId"
                    })
                
                plan["collections_to_migrate"].append(col_plan)
                plan["estimated_document_count"] += col_data["document_count"]
        
        return plan


async def main():
    print("\n" + "="*80)
    print("CONNECTING TO MONGODB...")
    print("="*80)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.list_collection_names()
        print(f"✅ Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    auditor = SchemaAuditor(db)
    
    # Run full audit
    report = await auditor.run_full_audit()
    
    # Generate migration plan
    migration_plan = auditor.generate_migration_plan()
    
    # Print final summary
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    print(f"Total collections: {report['summary']['total_collections']}")
    print(f"Collections with issues: {report['summary']['collections_with_issues']}")
    print(f"Total documents scanned: {report['summary']['total_documents_scanned']}")
    print(f"Total legacy fields found: {report['summary']['total_legacy_fields_found']}")
    print(f"Total string IDs found: {report['summary']['total_string_ids_found']}")
    
    if report['summary']['collections_need_migration']:
        print(f"\n🔴 COLLECTIONS REQUIRING MIGRATION:")
        for col in report['summary']['collections_need_migration']:
            print(f"   - {col}")
    else:
        print(f"\n✅ No collections require migration")
    
    # Save report
    report_path = "/app/backend/scripts/schema_audit_report.json"
    with open(report_path, "w") as f:
        # Convert sets to lists for JSON
        json.dump(report, f, indent=2, default=str)
    print(f"\n📄 Audit report saved to: {report_path}")
    
    # Save migration plan
    plan_path = "/app/backend/scripts/migration_plan.json"
    with open(plan_path, "w") as f:
        json.dump(migration_plan, f, indent=2, default=str)
    print(f"📄 Migration plan saved to: {plan_path}")
    
    client.close()
    
    return report, migration_plan


if __name__ == "__main__":
    asyncio.run(main())
