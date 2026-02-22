"""
Setup spec templates and fix products
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone

async def setup():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['b2b_marketplace']
    
    now = datetime.now(timezone.utc)
    
    # Get the template we created
    template = await db.specTemplates.find_one({})
    if template:
        template_id = template['_id']  # Keep as ObjectId
        print(f'Found template: {template_id}')
        
        # Update products with this template - use ObjectId, not string
        result = await db.products.update_many(
            {'categoryId': ObjectId('6981a9a74108b0cbd93aa630')},
            {'$set': {'specTemplateId': template_id}}  # ObjectId, not str
        )
        print(f'Updated {result.modified_count} products')
    else:
        print('No template found')
    
    # Verify
    product = await db.products.find_one({'categoryId': ObjectId('6981a9a74108b0cbd93aa630')})
    if product:
        print(f'Product specTemplateId: {product.get("specTemplateId")}')
    
    client.close()

asyncio.run(setup())
