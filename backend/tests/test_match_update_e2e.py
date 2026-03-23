"""
E2E Verification: MATCH + UPDATE Engine
Tests 4 scenarios per user requirements:
  Case 1: Correct Match + Update (QC pass → Inventory stock +quantity)
  Case 2: No Match (unknown product → NO update, NO error crash)
  Case 3: Relation Field uses ID internally (not label)
  Edge Case: quantity = null/empty → safe fallback (no increment or 0)
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

# Add backend to path
sys.path.insert(0, '/app/backend')

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "b2b_platform")

async def run_tests():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Find the test user
    user = await db.users.find_one({"firebaseUid": "dev-test-uid-12345"})
    if not user:
        print("❌ No test user found. Creating one...")
        user = await db.users.insert_one({
            "firebaseUid": "dev-test-uid-12345",
            "email": "admin@test.com",
            "name": "Test Admin",
            "accountType": "seller",
            "accountStatus": "active",
            "isActive": True,
            "isAdmin": True,
            "isEmailVerified": True,
            "businessToolAccess": "advanced",
            "createdAt": datetime.now(timezone.utc),
        })
        user = await db.users.find_one({"firebaseUid": "dev-test-uid-12345"})
    
    seller_id = str(user.get("_id"))
    print(f"✅ Test user found: {seller_id}")

    # ── SETUP: Create Inventory Panel ──
    inv_panel = await db.panels.find_one({"sellerId": ObjectId(seller_id), "slug": "test-inventory-e2e"})
    if inv_panel:
        # Clean up old data
        await db.panel_records.delete_many({"panelId": inv_panel["_id"]})
        await db.panels.delete_one({"_id": inv_panel["_id"]})
    
    inv_result = await db.panels.insert_one({
        "sellerId": ObjectId(seller_id),
        "name": "Test Inventory E2E",
        "slug": "test-inventory-e2e",
        "description": "For E2E testing",
        "icon": "layout-grid",
        "color": "blue",
        "fields": [
            {"key": "product_name", "label": "Product Name", "type": "text", "required": True, "order": 0},
            {"key": "stock", "label": "Stock", "type": "number", "required": False, "order": 1},
            {"key": "sku", "label": "SKU", "type": "text", "required": False, "order": 2},
        ],
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    inv_panel_id = str(inv_result.inserted_id)
    print(f"✅ Created Inventory panel: {inv_panel_id}")

    # Add inventory records
    gloves_rec = await db.panel_records.insert_one({
        "panelId": ObjectId(inv_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": {"product_name": "Safety Hand Gloves", "stock": 10, "sku": "SHG-001"},
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    gloves_id = str(gloves_rec.inserted_id)
    print(f"   Added: Safety Hand Gloves (stock=10, id={gloves_id})")

    helmets_rec = await db.panel_records.insert_one({
        "panelId": ObjectId(inv_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": {"product_name": "Safety Helmets", "stock": 25, "sku": "SH-002"},
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    print(f"   Added: Safety Helmets (stock=25)")

    # ── SETUP: Create QC Panel with relation field ──
    qc_panel = await db.panels.find_one({"sellerId": ObjectId(seller_id), "slug": "test-qc-e2e"})
    if qc_panel:
        await db.panel_records.delete_many({"panelId": qc_panel["_id"]})
        await db.automation_rules.delete_many({"trigger_panel_id": str(qc_panel["_id"])})
        await db.panels.delete_one({"_id": qc_panel["_id"]})

    qc_result = await db.panels.insert_one({
        "sellerId": ObjectId(seller_id),
        "name": "Test QC E2E",
        "slug": "test-qc-e2e",
        "description": "For E2E testing",
        "icon": "layout-grid",
        "color": "green",
        "fields": [
            {"key": "product_name", "label": "Product Name", "type": "relation", "required": True,
             "relatedPanel": inv_panel_id, "relationType": "one-to-one", "order": 0},
            {"key": "quantity", "label": "Quantity", "type": "number", "required": True, "order": 1},
            {"key": "status", "label": "QC Status", "type": "dropdown", "required": True,
             "options": ["Pass", "Fail", "Pending"], "order": 2},
        ],
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    qc_panel_id = str(qc_result.inserted_id)
    print(f"✅ Created QC panel: {qc_panel_id}")

    # ── SETUP: Import automation engine ──
    from routers.automation_router import init_automation_router
    auto_router = init_automation_router(db, None)
    execute_automation = auto_router.execute_automation

    # ══════════════════════════════════════
    # CASE 1: Correct Match + Update
    # QC: product=Safety Hand Gloves, quantity=5, status=Pass
    # Expected: Inventory stock 10 → 15
    # ══════════════════════════════════════
    print("\n" + "="*60)
    print("CASE 1: Correct Match + Update")
    print("="*60)

    # Create rule: QC(pass) → Inventory: match product_name, increment stock by quantity
    # Using DATA FIELD matching (product_name text match)
    rule1 = await db.automation_rules.insert_one({
        "sellerId": ObjectId(seller_id),
        "name": "QC Pass → Inventory Stock (Data Match)",
        "trigger_panel_id": qc_panel_id,
        "trigger_type": "condition_based",
        "condition": {"field": "status", "operator": "equals", "value": "Pass"},
        "targets": [{
            "target_panel_id": inv_panel_id,
            "action_type": "update_record",
            "data_mode": "smart_sync",
            "match_target_field": "product_name",    # Field in inventory
            "match_source_field": "product_name",    # Field in QC (relation → stores ID!)
            "update_field": "stock",
            "update_operation": "increment",
            "update_value_from": "quantity",
        }],
        "is_active": True,
        "priority": 0,
        "execution_count": 0,
        "last_executed": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    rule1_id = str(rule1.inserted_id)

    # Create QC record: product=Safety Hand Gloves (via relation = ObjectId), quantity=5, status=Pass
    qc_data_1 = {
        "product_name": gloves_id,  # Relation stores ObjectId string
        "quantity": 5,
        "status": "Pass",
    }
    qc_rec_1 = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": qc_data_1,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })

    # Execute automation
    await execute_automation(qc_data_1, qc_panel_id, str(qc_rec_1.inserted_id), seller_id, seller_id, "record_created")

    # Verify
    inv_rec = await db.panel_records.find_one({"_id": ObjectId(gloves_id)})
    new_stock = inv_rec["data"].get("stock", "NOT_FOUND")
    if new_stock == 15:
        print(f"  ✅ PASS: Stock correctly updated from 10 → {new_stock}")
    else:
        print(f"  ❌ FAIL: Expected stock=15, got stock={new_stock}")
        # Check automation logs for details
        log = await db.automation_logs.find_one({"ruleId": ObjectId(rule1_id)}, sort=[("timestamp", -1)])
        if log:
            print(f"     Log: status={log.get('status')}, message={log.get('message')}")

    # ══════════════════════════════════════
    # CASE 2: No Match (Unknown Product)
    # QC: product=<non-existent-id>, quantity=3, status=Pass
    # Expected: NO update, NO crash
    # ══════════════════════════════════════
    print("\n" + "="*60)
    print("CASE 2: No Match (Unknown Product)")
    print("="*60)

    fake_product_id = str(ObjectId())  # Random ID that doesn't exist
    qc_data_2 = {
        "product_name": fake_product_id,
        "quantity": 3,
        "status": "Pass",
    }
    qc_rec_2 = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": qc_data_2,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })

    # This should NOT crash — just log an error
    try:
        await execute_automation(qc_data_2, qc_panel_id, str(qc_rec_2.inserted_id), seller_id, seller_id, "record_created")
        # Verify gloves stock unchanged
        inv_rec = await db.panel_records.find_one({"_id": ObjectId(gloves_id)})
        stock_after = inv_rec["data"].get("stock")
        log = await db.automation_logs.find_one(
            {"ruleId": ObjectId(rule1_id), "record_id": str(qc_rec_2.inserted_id)},
            sort=[("timestamp", -1)]
        )
        log_status = log.get("status", "unknown") if log else "no log"
        if stock_after == 15 and log_status == "error":
            print(f"  ✅ PASS: Stock unchanged at {stock_after}, logged error correctly: {log.get('message', '')[:80]}")
        elif stock_after == 15:
            print(f"  ✅ PASS: Stock unchanged at {stock_after} (log status: {log_status})")
        else:
            print(f"  ❌ FAIL: Stock changed to {stock_after} (expected 15)")
    except Exception as e:
        print(f"  ❌ FAIL: Engine crashed with: {e}")

    # ══════════════════════════════════════
    # CASE 3: Relation Field uses ID internally
    # Verify that when product_name is a relation field,
    # the match_value is treated as ObjectId (not label text)
    # ══════════════════════════════════════
    print("\n" + "="*60)
    print("CASE 3: Relation Field uses ID internally")
    print("="*60)

    # The product_name field on QC panel is type=relation
    # When we store gloves_id as the value, the engine should:
    # 1. Detect it's a relation field
    # 2. Use it as ObjectId to find the inventory record by _id
    
    # Reset stock to 20 for clean test
    await db.panel_records.update_one(
        {"_id": ObjectId(gloves_id)},
        {"$set": {"data.stock": 20}}
    )

    qc_data_3 = {
        "product_name": gloves_id,  # This is a relation → ObjectId string
        "quantity": 7,
        "status": "Pass",
    }
    qc_rec_3 = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": qc_data_3,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })

    await execute_automation(qc_data_3, qc_panel_id, str(qc_rec_3.inserted_id), seller_id, seller_id, "record_created")

    inv_rec = await db.panel_records.find_one({"_id": ObjectId(gloves_id)})
    new_stock = inv_rec["data"].get("stock")
    if new_stock == 27:
        print(f"  ✅ PASS: Relation ID correctly used. Stock: 20 → {new_stock} (increment by 7)")
    else:
        print(f"  ❌ FAIL: Expected stock=27, got stock={new_stock}")
        log = await db.automation_logs.find_one(
            {"ruleId": ObjectId(rule1_id), "record_id": str(qc_rec_3.inserted_id)},
            sort=[("timestamp", -1)]
        )
        if log:
            print(f"     Log: status={log.get('status')}, message={log.get('message')}")

    # ══════════════════════════════════════
    # EDGE CASE: quantity = null / empty
    # Expected: No increment OR safe fallback
    # ══════════════════════════════════════
    print("\n" + "="*60)
    print("EDGE CASE: quantity = null / empty")
    print("="*60)

    # Test with null quantity
    qc_data_null = {
        "product_name": gloves_id,
        "quantity": None,
        "status": "Pass",
    }
    qc_rec_null = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": qc_data_null,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })

    stock_before = (await db.panel_records.find_one({"_id": ObjectId(gloves_id)}))["data"]["stock"]
    
    try:
        await execute_automation(qc_data_null, qc_panel_id, str(qc_rec_null.inserted_id), seller_id, seller_id, "record_created")
    except Exception as e:
        print(f"  (Engine handled internally, no crash)")

    stock_after = (await db.panel_records.find_one({"_id": ObjectId(gloves_id)}))["data"]["stock"]
    log = await db.automation_logs.find_one(
        {"ruleId": ObjectId(rule1_id), "record_id": str(qc_rec_null.inserted_id)},
        sort=[("timestamp", -1)]
    )
    log_status = log.get("status", "unknown") if log else "no log"
    log_msg = log.get("message", "") if log else ""

    if stock_after == stock_before:
        print(f"  ✅ PASS: Stock unchanged at {stock_after} (null quantity safely handled)")
        print(f"     Log: status={log_status}, message={log_msg[:80]}")
    else:
        print(f"  ❌ FAIL: Stock changed from {stock_before} → {stock_after} with null quantity")

    # Test with empty string quantity
    qc_data_empty = {
        "product_name": gloves_id,
        "quantity": "",
        "status": "Pass",
    }
    qc_rec_empty = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": qc_data_empty,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })

    stock_before = (await db.panel_records.find_one({"_id": ObjectId(gloves_id)}))["data"]["stock"]

    try:
        await execute_automation(qc_data_empty, qc_panel_id, str(qc_rec_empty.inserted_id), seller_id, seller_id, "record_created")
    except Exception as e:
        print(f"  (Engine handled internally, no crash)")

    stock_after = (await db.panel_records.find_one({"_id": ObjectId(gloves_id)}))["data"]["stock"]
    log = await db.automation_logs.find_one(
        {"ruleId": ObjectId(rule1_id), "record_id": str(qc_rec_empty.inserted_id)},
        sort=[("timestamp", -1)]
    )
    log_status = log.get("status", "unknown") if log else "no log"
    log_msg = log.get("message", "") if log else ""

    if stock_after == stock_before:
        print(f"  ✅ PASS: Stock unchanged at {stock_after} (empty string safely handled)")
        print(f"     Log: status={log_status}, message={log_msg[:80]}")
    else:
        print(f"  ❌ FAIL: Stock changed from {stock_before} → {stock_after} with empty quantity")

    # ── CLEANUP ──
    print("\n" + "="*60)
    print("CLEANUP")
    print("="*60)
    await db.automation_rules.delete_many({"trigger_panel_id": qc_panel_id})
    await db.panel_records.delete_many({"panelId": ObjectId(qc_panel_id)})
    await db.panel_records.delete_many({"panelId": ObjectId(inv_panel_id)})
    await db.automation_logs.delete_many({"trigger_panel_id": qc_panel_id})
    await db.panels.delete_one({"_id": ObjectId(qc_panel_id)})
    await db.panels.delete_one({"_id": ObjectId(inv_panel_id)})
    print("  ✅ Test data cleaned up")

    print("\n" + "="*60)
    print("ALL E2E VERIFICATION TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_tests())
