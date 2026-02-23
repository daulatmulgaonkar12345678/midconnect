"""
Enterprise Endpoints Performance Load Testing Suite
====================================================

Tests the enterprise product endpoints under simulated load:
- GET /products/{id}/enterprise
- GET /products/{id}/facets
- POST /products/{id}/filter

Scenarios: 10k, 50k, 100k listings

Target benchmarks at 50k listings:
- Filter endpoint: < 200ms
- Enterprise endpoint: < 250ms
- Facets endpoint: < 150ms
"""

import asyncio
import time
import statistics
import random
import string
from datetime import datetime, timezone
from typing import Dict, List, Any
from bson import ObjectId
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "midconnect")

# Test scenarios
SCENARIOS = [
    {"name": "10k", "listing_count": 10000},
    {"name": "50k", "listing_count": 50000},
    {"name": "100k", "listing_count": 100000},
]

# Benchmarks (in milliseconds)
BENCHMARKS = {
    "50k": {
        "filter": 200,
        "enterprise": 250,
        "facets": 150,
    }
}


class PerformanceTestSuite:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_product_id = None
        self.test_category_id = None
        self.results: Dict[str, Any] = {}
        
    async def setup(self):
        """Initialize database connection."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        print(f"Connected to MongoDB: {DB_NAME}")
        
    async def cleanup(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            
    async def create_test_product(self) -> ObjectId:
        """Create a test product for load testing."""
        # Create test category
        category = {
            "_id": ObjectId(),
            "name": f"LoadTest_Category_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Category for load testing",
            "isActive": True,
            "createdAt": datetime.now(timezone.utc),
        }
        await self.db.categories.insert_one(category)
        self.test_category_id = category["_id"]
        
        # Create test product
        product = {
            "_id": ObjectId(),
            "name": f"LoadTest_Product_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "categoryId": category["_id"],
            "description": "Product for performance load testing",
            "slug": f"loadtest-product-{ObjectId()}",
            "images": [],
            "isActive": True,
            "specTemplateIds": [],
            "createdAt": datetime.now(timezone.utc),
        }
        await self.db.products.insert_one(product)
        self.test_product_id = product["_id"]
        
        print(f"Created test product: {product['_id']}")
        return product["_id"]
    
    async def generate_test_listings(self, count: int):
        """Generate synthetic listings for load testing."""
        print(f"Generating {count} test listings...")
        
        # Create test sellers first
        sellers = []
        seller_count = min(count // 10, 1000)  # Max 1000 unique sellers
        
        for i in range(seller_count):
            seller = {
                "_id": ObjectId(),
                "firebaseUid": f"loadtest_seller_{i}",
                "email": f"seller{i}@loadtest.com",
                "profile": {
                    "businessName": f"LoadTest Seller {i}",
                    "city": random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad"]),
                    "state": random.choice(["Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "West Bengal", "Telangana"]),
                },
                "roles": ["buyer", "seller"],
                "isActive": True,
            }
            sellers.append(seller)
        
        # Batch insert sellers
        if sellers:
            await self.db.users.insert_many(sellers)
            print(f"Created {len(sellers)} test sellers")
        
        # Generate listings in batches
        batch_size = 5000
        total_created = 0
        
        # Sample attribute values for realistic distribution
        power_values = [5, 7.5, 10, 15, 20, 25, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200]
        voltage_values = ["220", "380", "415", "440", "690"]
        frame_values = ["71", "80", "90", "100", "112", "132", "160", "180", "200", "225", "250", "280", "315"]
        mounting_values = ["Foot", "Flange", "Face", "Foot+Flange"]
        efficiency_values = ["IE1", "IE2", "IE3", "IE4"]
        
        for batch_start in range(0, count, batch_size):
            batch_count = min(batch_size, count - batch_start)
            listings = []
            
            for i in range(batch_count):
                seller = random.choice(sellers)
                power = random.choice(power_values)
                voltage = random.choice(voltage_values)
                
                # Generate searchable attributes
                searchable_attrs = {
                    "power": power,
                    "voltage": voltage,
                    "frame": random.choice(frame_values),
                    "mounting": random.choice(mounting_values),
                    "efficiency": random.choice(efficiency_values),
                    "poles": random.choice([2, 4, 6, 8]),
                    "rpm": random.choice([750, 1000, 1500, 3000]),
                }
                
                listing = {
                    "_id": ObjectId(),
                    "productId": self.test_product_id,
                    "sellerId": seller["_id"],
                    "categoryId": self.test_category_id,
                    "variantId": ObjectId(),
                    "status": "active",
                    "sellerRole": random.choice(["manufacturer", "dealer", "distributor"]),
                    "searchableAttributes": searchable_attrs,
                    "attributeLabels": {
                        "power": "Power (kW)",
                        "voltage": "Voltage (V)",
                        "frame": "Frame Size",
                        "mounting": "Mounting",
                        "efficiency": "Efficiency Class",
                        "poles": "Poles",
                        "rpm": "RPM",
                    },
                    "searchableText": f"motor {power}kW {voltage}V {searchable_attrs['efficiency']} industrial electric motor",
                    "pricingTiers": [
                        {"minQty": 1, "maxQty": 10, "pricePerUnit": random.randint(5000, 50000)},
                        {"minQty": 11, "maxQty": 50, "pricePerUnit": random.randint(4000, 45000)},
                        {"minQty": 51, "maxQty": None, "pricePerUnit": random.randint(3500, 40000)},
                    ],
                    "moq": random.choice([1, 5, 10, 25]),
                    "stock": random.randint(0, 500),
                    "leadTime": random.choice([3, 5, 7, 10, 14, 21, 30]),
                    "images": [],
                    "isActive": True,
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc),
                }
                listings.append(listing)
            
            # Batch insert
            if listings:
                await self.db.sellerListings.insert_many(listings)
                total_created += len(listings)
                print(f"  Progress: {total_created}/{count} listings created")
        
        print(f"Total listings created: {total_created}")
        return total_created
    
    async def ensure_indexes(self):
        """Ensure enterprise indexes exist."""
        print("Ensuring enterprise indexes...")
        
        # Product/status compound index
        await self.db.sellerListings.create_index(
            [("productId", 1), ("status", 1)],
            name="enterprise_product_status"
        )
        
        # Searchable attributes index
        await self.db.sellerListings.create_index(
            [("productId", 1), ("searchableAttributes.power", 1), ("searchableAttributes.voltage", 1)],
            name="enterprise_attrs_composite"
        )
        
        # Text search index (if not exists)
        try:
            await self.db.sellerListings.create_index(
                [("searchableText", "text"), ("description", "text")],
                name="enterprise_text_search",
                weights={"searchableText": 10, "description": 5}
            )
        except Exception:
            pass  # Index might already exist
        
        print("Indexes ensured")
    
    async def run_enterprise_endpoint_test(self, iterations: int = 50) -> Dict[str, float]:
        """Test GET /products/{id}/enterprise endpoint performance."""
        print(f"\nTesting /enterprise endpoint ({iterations} iterations)...")
        
        times = []
        
        for i in range(iterations):
            # Simulate the aggregation pipeline
            start = time.perf_counter()
            
            pipeline = [
                {"$match": {"productId": self.test_product_id, "status": "active"}},
                {"$lookup": {
                    "from": "users",
                    "localField": "sellerId",
                    "foreignField": "_id",
                    "as": "sellerData"
                }},
                {"$unwind": {"path": "$sellerData", "preserveNullAndEmptyArrays": True}},
                {"$facet": {
                    "totalCount": [{"$count": "count"}],
                    "minPrice": [
                        {"$unwind": "$pricingTiers"},
                        {"$group": {"_id": None, "min": {"$min": "$pricingTiers.pricePerUnit"}}}
                    ],
                    "variantCount": [
                        {"$group": {"_id": "$variantId"}},
                        {"$count": "count"}
                    ],
                    "listings": [
                        {"$sort": {"pricingTiers.0.pricePerUnit": 1}},
                        {"$limit": 20},
                        {"$project": {
                            "_id": 1, "sellerId": 1, "variantId": 1,
                            "searchableAttributes": 1, "attributeLabels": 1,
                            "pricingTiers": 1, "moq": 1, "stock": 1, "leadTime": 1,
                            "images": {"$slice": ["$images", 2]},
                            "sellerRole": 1,
                            "sellerProfile": {
                                "businessName": "$sellerData.profile.businessName",
                                "city": "$sellerData.profile.city",
                                "state": "$sellerData.profile.state"
                            }
                        }}
                    ],
                    "facets": [
                        {"$group": {"_id": None, "allAttributes": {"$push": "$searchableAttributes"}}}
                    ]
                }}
            ]
            
            result = await self.db.sellerListings.aggregate(pipeline).to_list(1)
            
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")
        
        return self._calculate_stats(times)
    
    async def run_facets_endpoint_test(self, iterations: int = 50) -> Dict[str, float]:
        """Test GET /products/{id}/facets endpoint performance."""
        print(f"\nTesting /facets endpoint ({iterations} iterations)...")
        
        times = []
        
        for i in range(iterations):
            start = time.perf_counter()
            
            pipeline = [
                {"$match": {"productId": self.test_product_id, "status": "active"}},
                {"$group": {
                    "_id": None,
                    "allAttributes": {"$push": "$searchableAttributes"},
                    "count": {"$sum": 1}
                }}
            ]
            
            result = await self.db.sellerListings.aggregate(pipeline).to_list(1)
            
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")
        
        return self._calculate_stats(times)
    
    async def run_filter_endpoint_test(self, iterations: int = 50) -> Dict[str, float]:
        """Test POST /products/{id}/filter endpoint performance."""
        print(f"\nTesting /filter endpoint ({iterations} iterations)...")
        
        times = []
        
        # Sample filter combinations
        filter_combos = [
            {"searchableAttributes.power": {"$gte": 10, "$lte": 50}},
            {"searchableAttributes.voltage": "415"},
            {"searchableAttributes.efficiency": "IE3"},
            {"searchableAttributes.power": {"$gte": 20}, "searchableAttributes.voltage": "415"},
            {"searchableAttributes.mounting": "Flange", "searchableAttributes.poles": 4},
        ]
        
        for i in range(iterations):
            start = time.perf_counter()
            
            # Rotate through filter combinations
            filter_match = filter_combos[i % len(filter_combos)]
            
            match = {"productId": self.test_product_id, "status": "active"}
            match.update(filter_match)
            
            # Execute filtered query
            results = await self.db.sellerListings.find(match)\
                .sort("pricingTiers.0.pricePerUnit", 1)\
                .limit(20)\
                .to_list(20)
            
            total = await self.db.sellerListings.count_documents(match)
            
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")
        
        return self._calculate_stats(times)
    
    async def run_text_search_test(self, iterations: int = 50) -> Dict[str, float]:
        """Test text search performance."""
        print(f"\nTesting text search ({iterations} iterations)...")
        
        times = []
        
        search_terms = [
            "motor 45kW",
            "industrial electric",
            "IE3 efficiency",
            "415V motor",
            "flange mount",
        ]
        
        for i in range(iterations):
            start = time.perf_counter()
            
            search_query = search_terms[i % len(search_terms)]
            
            # Text search query
            results = await self.db.sellerListings.find(
                {
                    "productId": self.test_product_id,
                    "status": "active",
                    "$text": {"$search": search_query}
                },
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(20).to_list(20)
            
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")
        
        return self._calculate_stats(times)
    
    def _calculate_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics."""
        times_sorted = sorted(times)
        
        return {
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "p50": statistics.median(times),
            "p95": times_sorted[int(len(times) * 0.95)],
            "p99": times_sorted[int(len(times) * 0.99)],
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        }
    
    async def cleanup_test_data(self):
        """Remove test data after testing."""
        print("\nCleaning up test data...")
        
        if self.test_product_id:
            await self.db.sellerListings.delete_many({"productId": self.test_product_id})
            await self.db.products.delete_one({"_id": self.test_product_id})
            print(f"Deleted listings for product {self.test_product_id}")
        
        if self.test_category_id:
            await self.db.categories.delete_one({"_id": self.test_category_id})
            print(f"Deleted test category {self.test_category_id}")
        
        # Clean up test sellers
        await self.db.users.delete_many({"email": {"$regex": "^seller.*@loadtest.com$"}})
        print("Deleted test sellers")
    
    async def run_scenario(self, listing_count: int, scenario_name: str):
        """Run a complete test scenario."""
        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario_name} ({listing_count:,} listings)")
        print(f"{'='*60}")
        
        # Create test product
        await self.create_test_product()
        
        # Generate listings
        await self.generate_test_listings(listing_count)
        
        # Ensure indexes
        await self.ensure_indexes()
        
        # Wait for indexes to be ready
        await asyncio.sleep(2)
        
        # Run performance tests
        results = {
            "scenario": scenario_name,
            "listing_count": listing_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        results["enterprise"] = await self.run_enterprise_endpoint_test()
        results["facets"] = await self.run_facets_endpoint_test()
        results["filter"] = await self.run_filter_endpoint_test()
        results["text_search"] = await self.run_text_search_test()
        
        # Check against benchmarks
        if scenario_name in BENCHMARKS:
            benchmarks = BENCHMARKS[scenario_name]
            results["benchmark_pass"] = {
                "filter": results["filter"]["p95"] < benchmarks["filter"],
                "enterprise": results["enterprise"]["p95"] < benchmarks["enterprise"],
                "facets": results["facets"]["p95"] < benchmarks["facets"],
            }
        
        # Cleanup
        await self.cleanup_test_data()
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted results."""
        print(f"\n{'='*60}")
        print(f"RESULTS: {results['scenario']} ({results['listing_count']:,} listings)")
        print(f"{'='*60}")
        
        for endpoint in ["enterprise", "facets", "filter", "text_search"]:
            if endpoint in results:
                stats = results[endpoint]
                print(f"\n{endpoint.upper()} Endpoint:")
                print(f"  Average:  {stats['avg']:.2f}ms")
                print(f"  P50:      {stats['p50']:.2f}ms")
                print(f"  P95:      {stats['p95']:.2f}ms")
                print(f"  P99:      {stats['p99']:.2f}ms")
                print(f"  Min/Max:  {stats['min']:.2f}ms / {stats['max']:.2f}ms")
        
        if "benchmark_pass" in results:
            print(f"\nBenchmark Results:")
            for endpoint, passed in results["benchmark_pass"].items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {endpoint}: {status}")


async def main():
    """Main entry point for load testing."""
    suite = PerformanceTestSuite()
    
    try:
        await suite.setup()
        
        all_results = []
        
        # Run scenarios (start with smaller for quick validation)
        for scenario in SCENARIOS:
            results = await suite.run_scenario(
                listing_count=scenario["listing_count"],
                scenario_name=scenario["name"]
            )
            suite.print_results(results)
            all_results.append(results)
        
        # Summary
        print(f"\n{'='*60}")
        print("LOAD TEST SUMMARY")
        print(f"{'='*60}")
        
        for result in all_results:
            print(f"\n{result['scenario']}:")
            print(f"  Enterprise P95: {result['enterprise']['p95']:.2f}ms")
            print(f"  Filter P95:     {result['filter']['p95']:.2f}ms")
            print(f"  Facets P95:     {result['facets']['p95']:.2f}ms")
            
            if "benchmark_pass" in result:
                all_pass = all(result["benchmark_pass"].values())
                print(f"  Benchmark:      {'✅ ALL PASS' if all_pass else '❌ SOME FAIL'}")
        
        return all_results
        
    finally:
        await suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
