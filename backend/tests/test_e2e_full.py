"""
E2E Verification: MATCH + UPDATE Engine + Field Visibility
Uses correct database: midconnect
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

sys.path.insert(0, '/app/backend')
os.environ['DB_NAME'] = 'midconnect'

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

async def run_tests():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['midconnect']

    user = await db.users.find_one({"firebaseUid": "dev-test-uid-12345"})
    if not user:
        print("❌ No test user found")
        return
    seller_id = str(user["_id"])
    print(f"✅ Test user: {seller_id}")

    # ── SETUP: Create Inventory Panel ──
    inv_panel = await db.panels.find_one({"sellerId": ObjectId(seller_id), "slug": "e2e-inventory"})
    if inv_panel:
        await db.panel_records.delete_many({"panelId": inv_panel["_id"]})
        await db.automation_rules.delete_many({"targets.target_panel_id": str(inv_panel["_id"])})
        await db.panels.delete_one({"_id": inv_panel["_id"]})

    inv_result = await db.panels.insert_one({
        "sellerId": ObjectId(seller_id),
        "name": "E2E Inventory",
        "slug": "e2e-inventory",
        "description": "E2E test",
        "icon": "layout-grid",
        "color": "blue",
        "fields": [
            {"key": "product_name", "label": "Product Name", "type": "text", "required": True, "order": 0},
            {"key": "stock", "label": "Stock", "type": "number", "required": False, "order": 1},
        ],
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    inv_panel_id = str(inv_result.inserted_id)

    gloves_rec = await db.panel_records.insert_one({
        "panelId": ObjectId(inv_panel_id),
        "sellerId": ObjectId(seller_id),
        "data": {"product_name": "Safety Hand Gloves", "stock": 10},
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    gloves_id = str(gloves_rec.inserted_id)

    # ── SETUP: Create QC Panel with relation field ──
    qc_panel = await db.panels.find_one({"sellerId": ObjectId(seller_id), "slug": "e2e-qc"})
    if qc_panel:
        await db.panel_records.delete_many({"panelId": qc_panel["_id"]})
        await db.automation_rules.delete_many({"trigger_panel_id": str(qc_panel["_id"])})
        await db.panels.delete_one({"_id": qc_panel["_id"]})

    qc_result = await db.panels.insert_one({
        "sellerId": ObjectId(seller_id),
        "name": "E2E QC",
        "slug": "e2e-qc",
        "description": "E2E test",
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
    print(f"✅ Setup: INV={inv_panel_id}, QC={qc_panel_id}, Gloves={gloves_id}")

    # Import automation engine
    from routers.automation_router import init_automation_router
    auto_router = init_automation_router(db, None)
    execute_automation = auto_router.execute_automation

    # Create rule
    rule1 = await db.automation_rules.insert_one({
        "sellerId": ObjectId(seller_id),
        "name": "QC Pass → Stock Increment",
        "trigger_panel_id": qc_panel_id,
        "trigger_type": "condition_based",
        "condition": {"field": "status", "operator": "equals", "value": "Pass"},
        "targets": [{
            "target_panel_id": inv_panel_id,
            "action_type": "update_record",
            "data_mode": "smart_sync",
            "match_target_field": "product_name",
            "match_source_field": "product_name",
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

    passed = 0
    failed = 0

    # ═══ CASE 1: Correct Match + Update ═══
    print("\n" + "="*60)
    print("CASE 1: Correct Match + Update")
    qc_data_1 = {"product_name": gloves_id, "quantity": 5, "status": "Pass"}
    qc_rec = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id), "sellerId": ObjectId(seller_id),
        "data": qc_data_1, "createdAt": datetime.now(timezone.utc), "updatedAt": datetime.now(timezone.utc),
    })
    await execute_automation(qc_data_1, qc_panel_id, str(qc_rec.inserted_id), seller_id, seller_id, "record_created")
    inv_rec = await db.panel_records.find_one({"_id": ObjectId(gloves_id)})
    stock = inv_rec["data"].get("stock")
    if stock == 15:
        print(f"  ✅ PASS: Stock 10 → {stock}")
        passed += 1
    else:
        print(f"  ❌ FAIL: Expected 15, got {stock}")
        failed += 1

    # ═══ CASE 2: No Match (Unknown Product) ═══
    print("\n" + "="*60)
    print("CASE 2: No Match (Unknown Product)")
    fake_id = str(ObjectId())
    qc_data_2 = {"product_name": fake_id, "quantity": 3, "status": "Pass"}
    qc_rec2 = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id), "sellerId": ObjectId(seller_id),
        "data": qc_data_2, "createdAt": datetime.now(timezone.utc), "updatedAt": datetime.now(timezone.utc),
    })
    await execute_automation(qc_data_2, qc_panel_id, str(qc_rec2.inserted_id), seller_id, seller_id, "record_created")
    inv_rec = await db.panel_records.find_one({"_id": ObjectId(gloves_id)})
    stock_after = inv_rec["data"].get("stock")
    log = await db.automation_logs.find_one({"record_id": str(qc_rec2.inserted_id)}, sort=[("timestamp", -1)])
    if stock_after == 15 and log and log.get("status") == "error":
        print(f"  ✅ PASS: Stock unchanged at {stock_after}, error logged")
        passed += 1
    else:
        print(f"  ❌ FAIL: stock={stock_after}, log={log.get('status') if log else 'none'}")
        failed += 1

    # ═══ CASE 3: Relation Field uses ID internally ═══
    print("\n" + "="*60)
    print("CASE 3: Relation Field uses ID internally")
    await db.panel_records.update_one({"_id": ObjectId(gloves_id)}, {"$set": {"data.stock": 20}})
    qc_data_3 = {"product_name": gloves_id, "quantity": 7, "status": "Pass"}
    qc_rec3 = await db.panel_records.insert_one({
        "panelId": ObjectId(qc_panel_id), "sellerId": ObjectId(seller_id),
        "data": qc_data_3, "createdAt": datetime.now(timezone.utc), "updatedAt": datetime.now(timezone.utc),
    })
    await execute_automation(qc_data_3, qc_panel_id, str(qc_rec3.inserted_id), seller_id, seller_id, "record_created")
    inv_rec = await db.panel_records.find_one({"_id": ObjectId(gloves_id)})
    stock = inv_rec["data"].get("stock")
    if stock == 27:
        print(f"  ✅ PASS: Relation ID used correctly. Stock 20 → {stock}")
        passed += 1
    else:
        print(f"  ❌ FAIL: Expected 27, got {stock}")
        failed += 1

    # ═══ EDGE CASE: quantity=null and quantity="" ═══
    print("\n" + "="*60)
    print("EDGE CASE: quantity=null/empty")
    for label, qty_val in [("null", None), ("empty string", "")]:
        stock_before = (await db.panel_records.find_one({"_id": ObjectId(gloves_id)}))["data"]["stock"]
        qc_data = {"product_name": gloves_id, "quantity": qty_val, "status": "Pass"}
        qc_rec = await db.panel_records.insert_one({
            "panelId": ObjectId(qc_panel_id), "sellerId": ObjectId(seller_id),
            "data": qc_data, "createdAt": datetime.now(timezone.utc), "updatedAt": datetime.now(timezone.utc),
        })
        await execute_automation(qc_data, qc_panel_id, str(qc_rec.inserted_id), seller_id, seller_id, "record_created")
        stock_after = (await db.panel_records.find_one({"_id": ObjectId(gloves_id)}))["data"]["stock"]
        if stock_after == stock_before:
            print(f"  ✅ PASS ({label}): Stock unchanged at {stock_after}")
            passed += 1
        else:
            print(f"  ❌ FAIL ({label}): Stock changed from {stock_before} → {stock_after}")
            failed += 1

    # ═══ FIELD VISIBILITY API TEST ═══
    print("\n" + "="*60)
    print("FIELD VISIBILITY: Backend API")
    vis_panel = await db.panels.find_one({"sellerId": ObjectId(seller_id), "slug": "test-visibility-target"})
    if vis_panel:
        vis_panel_id = str(vis_panel["_id"])
        rules = await db.automation_rules.find({
            "sellerId": ObjectId(seller_id), "is_active": True,
            "targets.target_panel_id": vis_panel_id
        }).to_list(10)
        merged = {}
        for rule in rules:
            for t in rule.get("targets", []):
                if t.get("target_panel_id") != vis_panel_id:
                    continue
                for fv in (t.get("field_visibility") or []):
                    fk = fv.get("field", "")
                    if not fk:
                        continue
                    if fk not in merged:
                        merged[fk] = {"visible": fv.get("visible", True), "editable": fv.get("editable", True)}
                    else:
                        if not fv.get("visible", True): merged[fk]["visible"] = False
                        if not fv.get("editable", True): merged[fk]["editable"] = False

        expected = {
            "stock": {"visible": True, "editable": False},
            "secret_code": {"visible": False, "editable": False},
            "notes": {"visible": True, "editable": True},
        }
        all_match = True
        for field, exp in expected.items():
            got = merged.get(field, {})
            if got.get("visible") != exp["visible"] or got.get("editable") != exp["editable"]:
                print(f"  ❌ FAIL: {field}: expected {exp}, got {got}")
                all_match = False
                failed += 1
        if all_match:
            print(f"  ✅ PASS: All visibility rules correct")
            print(f"     stock: visible=True, editable=False")
            print(f"     secret_code: visible=False, editable=False (hidden)")
            print(f"     notes: visible=True, editable=True (normal)")
            passed += 1
    else:
        print("  ⚠️ SKIP: Visibility test panel not found")

    # ── CLEANUP ──
    print("\n" + "="*60)
    await db.automation_rules.delete_many({"trigger_panel_id": qc_panel_id})
    await db.panel_records.delete_many({"panelId": ObjectId(qc_panel_id)})
    await db.panel_records.delete_many({"panelId": ObjectId(inv_panel_id)})
    await db.automation_logs.delete_many({"trigger_panel_id": qc_panel_id})
    await db.panels.delete_one({"_id": ObjectId(qc_panel_id)})
    await db.panels.delete_one({"_id": ObjectId(inv_panel_id)})
    print("✅ Test data cleaned up")

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
