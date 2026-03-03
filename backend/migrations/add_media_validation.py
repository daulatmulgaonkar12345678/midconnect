"""
Migration: Add MongoDB Schema Validation for Images & Videos

This migration adds JSON Schema validation to the sellerListings collection
to enforce:
- Max 5 images per listing
- Max 2 videos per listing

Run: python -m migrations.add_media_validation
"""

import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    """Add schema validation for images and videos."""
    
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "midconnect")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    logger.info(f"Connected to database: {db_name}")
    
    # Define the validation schema
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "properties": {
                "images": {
                    "bsonType": "array",
                    "maxItems": 5,
                    "items": {"bsonType": "string"},
                    "description": "Max 5 images per listing (5MB each)"
                },
                "videos": {
                    "bsonType": "array",
                    "maxItems": 2,
                    "items": {"bsonType": "string"},
                    "description": "Max 2 videos per listing (30s, 5MB each)"
                }
            }
        }
    }
    
    try:
        # Check if collection exists
        collections = await db.list_collection_names()
        
        if "sellerListings" not in collections:
            # Create collection with validation
            await db.create_collection(
                "sellerListings",
                validator=validator,
                validationLevel="moderate",  # Only validate inserts and updates
                validationAction="error"     # Reject invalid documents
            )
            logger.info("Created sellerListings collection with validation")
        else:
            # Modify existing collection
            result = await db.command({
                "collMod": "sellerListings",
                "validator": validator,
                "validationLevel": "moderate",
                "validationAction": "error"
            })
            logger.info(f"Updated sellerListings validation: {result}")
        
        # Verify validation is set
        collection_info = await db.command({
            "listCollections": 1,
            "filter": {"name": "sellerListings"}
        })
        
        if collection_info.get("cursor", {}).get("firstBatch"):
            info = collection_info["cursor"]["firstBatch"][0]
            logger.info(f"Validation options: {info.get('options', {}).get('validator', 'Not set')}")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
