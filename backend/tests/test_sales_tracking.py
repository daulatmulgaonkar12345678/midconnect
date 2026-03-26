"""E2E test for referral sales tracking system."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone
import sys
sys.path.insert(0, '/app/backend')

async def test():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['midconnect']

    # Setup: referrer + referred seller
    referrer_id = ObjectId()
    referred_id = ObjectId()

    await db.users.insert_one({
        '_id': referrer_id, 'email': 'referrer@test.com',
        'referralCode': 'TEST_SALES_123', 'referralCount': 1,
        'accountType': 'seller', 'isActive': True,
        'createdAt': datetime.now(timezone.utc),
    })
    await db.users.insert_one({
        '_id': referred_id, 'email': 'referred@test.com',
        'referredBy': 'TEST_SALES_123', 'accountType': 'seller',
        'isActive': True, 'createdAt': datetime.now(timezone.utc),
    })

    # Paid invoice for referred seller
    inv_id = ObjectId()
    await db.invoices.insert_one({
        '_id': inv_id, 'sellerId': referred_id,
        'invoiceNumber': 'TEST-INV-001', 'total': 10000,
        'status': 'paid', 'createdAt': datetime.now(timezone.utc),
    })

    from routers.referral_router import init_referral_router
    rr = init_referral_router(db, None)
    record_commission = rr.record_referral_commission

    passed = 0
    failed = 0

    # Test 1: Commission recorded correctly
    invoice_doc = {'_id': inv_id, 'total': 10000, 'sellerId': referred_id}
    await record_commission(invoice_doc, str(referred_id))
    c = await db.referral_commissions.find_one({'invoiceId': inv_id})
    if c and c['commission'] == 2000.0 and c['referredBy'] == 'TEST_SALES_123' and c['status'] == 'pending':
        print(f'✅ Commission recorded: ₹{c["commission"]} (20% of ₹{c["orderAmount"]})')
        passed += 1
    else:
        print(f'❌ Commission not recorded correctly: {c}')
        failed += 1

    # Test 2: Duplicate prevention
    await record_commission(invoice_doc, str(referred_id))
    count = await db.referral_commissions.count_documents({'invoiceId': inv_id})
    if count == 1:
        print('✅ Duplicate prevention works')
        passed += 1
    else:
        print(f'❌ Duplicate: {count} records')
        failed += 1

    # Test 3: No commission for non-referred user
    inv2 = ObjectId()
    await record_commission({'_id': inv2, 'total': 5000, 'sellerId': referrer_id}, str(referrer_id))
    nc = await db.referral_commissions.find_one({'invoiceId': inv2})
    if not nc:
        print('✅ No commission for non-referred user')
        passed += 1
    else:
        print('❌ Commission wrongly created for non-referred user')
        failed += 1

    # Test 4: Zero-amount invoice ignored
    inv3 = ObjectId()
    await record_commission({'_id': inv3, 'total': 0, 'sellerId': referred_id}, str(referred_id))
    nc2 = await db.referral_commissions.find_one({'invoiceId': inv3})
    if not nc2:
        print('✅ Zero-amount invoice ignored')
        passed += 1
    else:
        print('❌ Commission created for zero-amount invoice')
        failed += 1

    # Cleanup
    await db.users.delete_many({'_id': {'$in': [referrer_id, referred_id]}})
    await db.invoices.delete_one({'_id': inv_id})
    await db.referral_commissions.delete_many({'referredBy': 'TEST_SALES_123'})

    print(f'\nResults: {passed}/{passed+failed} passed')
    return failed == 0

asyncio.run(test())
