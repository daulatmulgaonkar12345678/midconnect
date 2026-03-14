"""
Activity Log Service - Shared utility for creating activity log entries
"""

from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class ActivityLogService:
    def __init__(self, db):
        self.db = db

    async def log(self, seller_id: str, user_id: str, action: str, module: str, entity_id: str = None, details: str = None):
        """Create an activity log entry."""
        doc = {
            "sellerId": ObjectId(seller_id),
            "userId": ObjectId(user_id) if user_id else None,
            "action": action,
            "module": module,
            "entityId": entity_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc)
        }
        await self.db.activity_logs.insert_one(doc)
        logger.info(f"Activity logged: {action} in {module} by {user_id}")
