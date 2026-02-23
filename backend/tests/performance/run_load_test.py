#!/usr/bin/env python3
"""
Quick Enterprise Performance Load Test
=======================================
Tests 10k, 50k, 100k listings performance
"""

import asyncio
import time
import statistics
import random
from datetime import datetime, timezone
from bson import ObjectId
import os
import json

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'midconnect')


async def run_load_test(listing_count: int):
    """Run load test with specified listing count."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    timestamp = datetime.now().strftime("%H%M%S")
    results = {"listing_count": listing_count, "timestamp": timestamp}
    
    print(f"\n{'='*60}")
    print(f"LOAD TEST: {listing_count:,} listings")
    print(f"{'='*60}")
    
    try:
        # Create test category
        cat_id = ObjectId()
        await db.categories.insert_one({
            '_id': cat_id,
            'name': f'LoadTest_{timestamp}_{listing_count}',
            'isActive': True
        })
        
        # Create test product
        prod_id = ObjectId()
        await db.products.insert_one({
            '_id': prod_id,
            'name': f'LoadTest_Product_{timestamp}_{listing_count}',
            'categoryId': cat_id,
            'isActive': True
        })
        
        # Create test sellers
        seller_count = min(listing_count // 10, 1000)
        sellers = []
        for i in range(seller_count):
            sellers.append({
                '_id': ObjectId(),
                'firebaseUid': f'lt_{timestamp}_{i}',
                'email': f'lt_{timestamp}_{i}@loadtest.com',
                'profile': {
                    'businessName': f'LoadTest Seller {i}',
                    'city': random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad']),
                    'state': random.choice(['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Telangana'])
                },
                'roles': ['buyer', 'seller'],
                'isActive': True
            })
        await db.users.insert_many(sellers)
        print(f"Created {len(sellers)} test sellers")
        
        # Generate listings
        print(f"Generating {listing_count:,} listings...")
        batch_size = 5000
        
        power_vals = [5, 7.5, 10, 15, 20, 25, 30, 37, 45, 55, 75, 90, 110, 132]
        voltage_vals = ['220', '380', '415', '440', '690']
        efficiency_vals = ['IE1', 'IE2', 'IE3', 'IE4']
        mounting_vals = ['Foot', 'Flange', 'Face', 'Foot+Flange']
        
        created = 0
        for batch_start in range(0, listing_count, batch_size):
            batch_count = min(batch_size, listing_count - batch_start)
            listings = []
            
            for _ in range(batch_count):
                power = random.choice(power_vals)
                voltage = random.choice(voltage_vals)
                
                listings.append({
                    '_id': ObjectId(),
                    'productId': prod_id,
                    'sellerId': random.choice(sellers)['_id'],
                    'categoryId': cat_id,
                    'variantId': ObjectId(),
                    'status': 'active',
                    'sellerRole': random.choice(['manufacturer', 'dealer', 'distributor']),
                    'searchableAttributes': {
                        'power': power,
                        'voltage': voltage,
                        'efficiency': random.choice(efficiency_vals),
                        'mounting': random.choice(mounting_vals),
                        'poles': random.choice([2, 4, 6, 8]),
                    },
                    'attributeLabels': {
                        'power': 'Power (kW)', 
                        'voltage': 'Voltage (V)',
                        'efficiency': 'Efficiency Class',
                        'mounting': 'Mounting Type',
                        'poles': 'Poles'
                    },
                    'searchableText': f'motor {power}kW {voltage}V industrial electric',
                    'pricingTiers': [
                        {'minQty': 1, 'maxQty': 10, 'pricePerUnit': random.randint(5000, 50000)},
                        {'minQty': 11, 'maxQty': None, 'pricePerUnit': random.randint(4000, 45000)},
                    ],
                    'moq': random.choice([1, 5, 10]),
                    'stock': random.randint(0, 200),
                    'leadTime': random.choice([5, 7, 10, 14, 21]),
                    'isActive': True
                })
            
            await db.sellerListings.insert_many(listings)
            created += len(listings)
            print(f"  Progress: {created:,}/{listing_count:,}")
        
        # Ensure indexes (use existing if available)
        print("Ensuring indexes exist...")
        try:
            await db.sellerListings.create_index([('productId', 1), ('status', 1)])
        except:
            pass  # Index exists
        try:
            await db.sellerListings.create_index([('productId', 1), ('searchableAttributes.power', 1)])
        except:
            pass
        try:
            await db.sellerListings.create_index([('productId', 1), ('searchableAttributes.voltage', 1)])
        except:
            pass
        
        # Wait for indexes
        await asyncio.sleep(2)
        
        iterations = 30
        
        # Test 1: Enterprise endpoint (aggregation)
        print(f"\n--- Enterprise Endpoint ({iterations} iterations) ---")
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            pipeline = [
                {'$match': {'productId': prod_id, 'status': 'active'}},
                {'$lookup': {'from': 'users', 'localField': 'sellerId', 'foreignField': '_id', 'as': 'seller'}},
                {'$unwind': {'path': '$seller', 'preserveNullAndEmptyArrays': True}},
                {'$facet': {
                    'count': [{'$count': 'n'}],
                    'minPrice': [
                        {'$unwind': '$pricingTiers'}, 
                        {'$group': {'_id': None, 'min': {'$min': '$pricingTiers.pricePerUnit'}}}
                    ],
                    'variants': [{'$group': {'_id': '$variantId'}}, {'$count': 'n'}],
                    'listings': [
                        {'$sort': {'pricingTiers.0.pricePerUnit': 1}}, 
                        {'$limit': 20},
                        {'$project': {'_id': 1, 'sellerId': 1, 'searchableAttributes': 1, 'pricingTiers': 1, 'moq': 1}}
                    ]
                }}
            ]
            await db.sellerListings.aggregate(pipeline).to_list(1)
            times.append((time.perf_counter() - start) * 1000)
        
        times.sort()
        results['enterprise'] = {
            'avg': round(statistics.mean(times), 1),
            'p50': round(statistics.median(times), 1),
            'p95': round(times[int(len(times)*0.95)], 1),
            'p99': round(times[int(len(times)*0.99)], 1),
            'min': round(min(times), 1),
            'max': round(max(times), 1)
        }
        print(f"  Avg: {results['enterprise']['avg']}ms | P95: {results['enterprise']['p95']}ms | P99: {results['enterprise']['p99']}ms")
        
        # Test 2: Filter endpoint
        print(f"\n--- Filter Endpoint ({iterations} iterations) ---")
        times = []
        filter_combos = [
            {'searchableAttributes.power': {'$gte': 20, '$lte': 60}},
            {'searchableAttributes.voltage': '415'},
            {'searchableAttributes.efficiency': 'IE3'},
            {'searchableAttributes.power': {'$gte': 30}, 'searchableAttributes.voltage': '415'},
        ]
        for i in range(iterations):
            start = time.perf_counter()
            match = {'productId': prod_id, 'status': 'active'}
            match.update(filter_combos[i % len(filter_combos)])
            await db.sellerListings.find(match).sort('pricingTiers.0.pricePerUnit', 1).limit(20).to_list(20)
            await db.sellerListings.count_documents(match)
            times.append((time.perf_counter() - start) * 1000)
        
        times.sort()
        results['filter'] = {
            'avg': round(statistics.mean(times), 1),
            'p50': round(statistics.median(times), 1),
            'p95': round(times[int(len(times)*0.95)], 1),
            'p99': round(times[int(len(times)*0.99)], 1),
            'min': round(min(times), 1),
            'max': round(max(times), 1)
        }
        print(f"  Avg: {results['filter']['avg']}ms | P95: {results['filter']['p95']}ms | P99: {results['filter']['p99']}ms")
        
        # Test 3: Facets endpoint
        print(f"\n--- Facets Endpoint ({iterations} iterations) ---")
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            pipeline = [
                {'$match': {'productId': prod_id, 'status': 'active'}},
                {'$group': {'_id': None, 'attrs': {'$push': '$searchableAttributes'}, 'count': {'$sum': 1}}}
            ]
            await db.sellerListings.aggregate(pipeline).to_list(1)
            times.append((time.perf_counter() - start) * 1000)
        
        times.sort()
        results['facets'] = {
            'avg': round(statistics.mean(times), 1),
            'p50': round(statistics.median(times), 1),
            'p95': round(times[int(len(times)*0.95)], 1),
            'p99': round(times[int(len(times)*0.99)], 1),
            'min': round(min(times), 1),
            'max': round(max(times), 1)
        }
        print(f"  Avg: {results['facets']['avg']}ms | P95: {results['facets']['p95']}ms | P99: {results['facets']['p99']}ms")
        
        # Benchmark check for 50k
        if listing_count == 50000:
            results['benchmarks'] = {
                'filter_pass': results['filter']['p95'] < 200,
                'enterprise_pass': results['enterprise']['p95'] < 250,
                'facets_pass': results['facets']['p95'] < 150,
            }
            results['all_pass'] = all(results['benchmarks'].values())
        
    finally:
        # Cleanup
        print("\nCleaning up test data...")
        await db.sellerListings.delete_many({'productId': prod_id})
        await db.products.delete_one({'_id': prod_id})
        await db.categories.delete_one({'_id': cat_id})
        await db.users.delete_many({'email': {'$regex': f'^lt_{timestamp}_.*@loadtest.com$'}})
        
        # Drop temp indexes
        # (indexes are shared, don't drop)
        
        client.close()
    
    return results


async def main():
    all_results = []
    
    # Run tests for each scenario
    for count in [10000, 50000, 100000]:
        results = await run_load_test(count)
        all_results.append(results)
        print(f"\n{count:,} Results: Enterprise P95={results['enterprise']['p95']}ms, Filter P95={results['filter']['p95']}ms, Facets P95={results['facets']['p95']}ms")
    
    # Summary
    print("\n" + "="*60)
    print("LOAD TEST SUMMARY")
    print("="*60)
    
    print("\n| Scenario | Enterprise P95 | Filter P95 | Facets P95 | Pass |")
    print("|----------|----------------|------------|------------|------|")
    
    for r in all_results:
        count = r['listing_count']
        ep = r['enterprise']['p95']
        fp = r['filter']['p95']
        fap = r['facets']['p95']
        
        # Check against benchmarks
        if count == 50000:
            status = "YES" if r.get('all_pass', False) else "NO"
        else:
            # Use 50k benchmarks proportionally
            ep_pass = ep < (250 * count / 50000) if count < 50000 else ep < 250
            fp_pass = fp < (200 * count / 50000) if count < 50000 else fp < 200
            fap_pass = fap < (150 * count / 50000) if count < 50000 else fap < 150
            status = "YES" if (ep_pass and fp_pass and fap_pass) else "NO"
        
        print(f"| {count//1000}k      | {ep:>14.1f} | {fp:>10.1f} | {fap:>10.1f} | {status:>4} |")
    
    print("\nTarget benchmarks at 50k:")
    print("  - Filter < 200ms")
    print("  - Enterprise < 250ms")
    print("  - Facets < 150ms")
    
    # Save results
    with open('/app/test_reports/load_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    print("\nResults saved to /app/test_reports/load_test_results.json")
    
    return all_results


if __name__ == "__main__":
    asyncio.run(main())
