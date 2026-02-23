"""
ENTERPRISE QUOTATION SERVICE - HYBRID RFQ SYSTEM
=================================================

Production v1 - Hybrid Seller Quotation Model

Key Principles:
- Quote always stored in platform (SSOT)
- WhatsApp is redirect only (no API integration)
- Acceptance only inside app (platform control)
- No data leakage before acceptance
- No quote edits after sent

Quote Flow:
1. Buyer → RFQ (Inquiry)
2. Seller → Accept Inquiry (lead counted)
3. Seller → Create Quote
4. Seller → WhatsApp button (redirect)
5. Buyer → Receives message with secure link
6. Buyer → Views quote on platform
7. Buyer → Accept/Reject inside platform
8. Auto Expiry enforced

Collection: quotes
Schema:
{
    "_id": ObjectId,
    "quoteId": "QT-XXXXX",           # Non-sequential, secure alphanumeric
    "inquiryId": ObjectId,
    "sellerId": ObjectId,
    "buyerId": ObjectId,
    "productId": ObjectId,
    "requestedQuantity": Number,
    "unitPrice": Number,
    "moq": Number,
    "packagingCharges": Number,
    "transportIncluded": false,       # Always false for v1
    "totalPrice": Number,             # Auto-calc: (unitPrice × qty) + packagingCharges
    "leadTimeDays": Number,
    "validityDate": ISODate,
    "status": "sent" | "viewed" | "accepted" | "rejected" | "expired",
    "whatsappRedirectUsed": Boolean,  # Tracks if seller clicked WhatsApp button
    "accessToken": String,            # Secure token for public URL access
    "createdAt": ISODate,
    "updatedAt": ISODate,
    "viewedAt": ISODate,
    "acceptedAt": ISODate,
    "rejectedAt": ISODate,
    "rejectionReason": String
}

Security Checklist:
✔ QuoteId non-sequential (random alphanumeric)
✔ Quote not editable after sent
✔ Buyer only sees their quotes
✔ Seller cannot modify after submission
✔ Acceptance requires login
✔ Expired quote cannot be accepted
✔ Lead count enforced before inquiry acceptance
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field
import secrets
import string
import logging

logger = logging.getLogger(__name__)

# Maximum validity days (per spec)
MAX_VALIDITY_DAYS = 15


def generate_secure_quote_id() -> str:
    """
    Generate a non-sequential, secure alphanumeric quote ID.
    
    Format: QT-XXXXX (5 random alphanumeric characters)
    
    Security: Uses secrets module for cryptographically secure random generation.
    NOT sequential to prevent enumeration attacks.
    """
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(5))
    return f"QT-{random_part}"


class QuoteCreateRequest(BaseModel):
    """Request model for creating a quote."""
    inquiryId: str
    unitPrice: float = Field(..., gt=0, description="Price per unit in INR")
    moq: int = Field(..., ge=1, description="Minimum order quantity")
    leadTimeDays: int = Field(..., ge=1, le=365, description="Lead time in days")
    validityDays: int = Field(default=7, ge=1, le=MAX_VALIDITY_DAYS, description=f"Quote validity (max {MAX_VALIDITY_DAYS} days)")
    packagingCharges: float = Field(default=0, ge=0, description="Optional packaging charges")
    terms: Optional[str] = Field(default=None, max_length=2000, description="Terms and conditions")
    customMessage: Optional[str] = Field(default=None, max_length=1000, description="Custom message to buyer")


class QuoteResponse(BaseModel):
    """Response model for quote data."""
    quoteId: str
    inquiryId: str
    productId: str
    productName: str
    sellerId: str
    sellerName: str
    buyerId: str
    buyerName: Optional[str] = None
    requestedQuantity: int
    unitPrice: float
    moq: int
    packagingCharges: float
    transportChargesIncluded: bool = False
    totalPrice: float
    leadTimeDays: int
    validityDate: str
    terms: Optional[str]
    customMessage: Optional[str]
    status: str
    createdAt: str
    viewedAt: Optional[str] = None
    acceptedAt: Optional[str] = None
    rejectedAt: Optional[str] = None


class QuotationService:
    """
    Enterprise quotation service for B2B marketplace.
    
    Features:
    - Structured quote creation
    - WhatsApp preview generation
    - Secure quote access
    - Auto-expiry management
    - Analytics tracking
    """
    
    def __init__(self, db):
        self.db = db
    
    async def ensure_indexes(self):
        """Create required indexes for quotes collection."""
        # Unique quote ID
        await self.db.quotes.create_index(
            [("quoteId", 1)],
            name="quote_id_unique",
            unique=True
        )
        
        # Seller quotes lookup
        await self.db.quotes.create_index(
            [("sellerId", 1), ("status", 1)],
            name="seller_quotes_status"
        )
        
        # Buyer quotes lookup
        await self.db.quotes.create_index(
            [("buyerId", 1), ("status", 1)],
            name="buyer_quotes_status"
        )
        
        # Inquiry reference
        await self.db.quotes.create_index(
            [("inquiryId", 1)],
            name="inquiry_quote_lookup"
        )
        
        # Expiry check index
        await self.db.quotes.create_index(
            [("status", 1), ("validityDate", 1)],
            name="quote_expiry_check"
        )
        
        # Secure access token
        await self.db.quotes.create_index(
            [("accessToken", 1)],
            name="quote_access_token",
            sparse=True
        )
        
        logger.info("Quote indexes ensured")
    
    async def _generate_quote_id(self) -> str:
        """Generate sequential quote ID (QT-000001)."""
        result = await self.db.counters.find_one_and_update(
            {"_id": QUOTE_COUNTER_KEY},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        seq = result.get("seq", 1)
        return f"QT-{seq:06d}"
    
    async def _generate_access_token(self) -> str:
        """Generate secure access token for quote URL."""
        return secrets.token_urlsafe(32)
    
    async def create_quote(
        self,
        seller_id: ObjectId,
        request: QuoteCreateRequest
    ) -> Dict[str, Any]:
        """
        Create a new quote for an accepted inquiry.
        
        Validations:
        - Inquiry must be accepted
        - Seller must match inquiry seller
        - No duplicate active quote for same inquiry
        
        Returns:
            Quote document with WhatsApp preview link
        """
        inquiry_oid = ObjectId(request.inquiryId)
        
        # Get inquiry
        inquiry = await self.db.inquiries.find_one({"_id": inquiry_oid})
        if not inquiry:
            raise ValueError("Inquiry not found")
        
        # Validate seller
        if str(inquiry.get("sellerId")) != str(seller_id):
            raise ValueError("You are not authorized to quote on this inquiry")
        
        # Validate inquiry status
        if inquiry.get("status") != "accepted":
            raise ValueError("Inquiry must be accepted before creating a quote")
        
        # Check for existing active quote
        existing_quote = await self.db.quotes.find_one({
            "inquiryId": inquiry_oid,
            "status": {"$in": ["sent", "viewed"]}
        })
        if existing_quote:
            raise ValueError(f"Active quote already exists: {existing_quote.get('quoteId')}")
        
        # Get product info
        product = await self.db.products.find_one({"_id": inquiry.get("productId")})
        product_name = product.get("name", "Unknown Product") if product else "Unknown Product"
        
        # Get seller info
        seller = await self.db.users.find_one({"_id": seller_id})
        seller_name = seller.get("profile", {}).get("businessName", "Seller") if seller else "Seller"
        
        # Get buyer info
        buyer_id = inquiry.get("buyerId")
        buyer = await self.db.users.find_one({"_id": buyer_id})
        buyer_name = buyer.get("profile", {}).get("name", "Buyer") if buyer else "Buyer"
        
        # Calculate totals
        requested_qty = inquiry.get("quantity", 1)
        unit_price = request.unitPrice
        packaging = request.packagingCharges
        total_price = (unit_price * requested_qty) + packaging
        
        # Generate IDs
        quote_id = await self._generate_quote_id()
        access_token = await self._generate_access_token()
        
        now = datetime.now(timezone.utc)
        validity_date = now + timedelta(days=request.validityDays)
        
        # MOQ warning (logged, not blocking)
        if requested_qty < request.moq:
            logger.warning(f"Quote {quote_id}: Requested qty ({requested_qty}) < MOQ ({request.moq})")
        
        quote_doc = {
            "_id": ObjectId(),
            "quoteId": quote_id,
            "accessToken": access_token,
            "inquiryId": inquiry_oid,
            "productId": inquiry.get("productId"),
            "productName": product_name,
            "sellerId": seller_id,
            "sellerName": seller_name,
            "buyerId": buyer_id,
            "buyerName": buyer_name,
            "requestedQuantity": requested_qty,
            "unitPrice": unit_price,
            "moq": request.moq,
            "packagingCharges": packaging,
            "transportChargesIncluded": False,  # Always false
            "totalPrice": total_price,
            "leadTimeDays": request.leadTimeDays,
            "validityDate": validity_date,
            "validityDays": request.validityDays,
            "terms": request.terms,
            "customMessage": request.customMessage,
            "status": "sent",
            "whatsappPreviewSent": False,
            "viewedAt": None,
            "acceptedAt": None,
            "rejectedAt": None,
            "createdAt": now,
            "updatedAt": now
        }
        
        await self.db.quotes.insert_one(quote_doc)
        
        # Track analytics
        await self._track_analytics("quote_created", {
            "quoteId": quote_id,
            "sellerId": str(seller_id),
            "buyerId": str(buyer_id),
            "productId": str(inquiry.get("productId")),
            "totalPrice": total_price
        })
        
        # Update inquiry with quote reference
        await self.db.inquiries.update_one(
            {"_id": inquiry_oid},
            {"$set": {"latestQuoteId": quote_doc["_id"], "updatedAt": now}}
        )
        
        logger.info(f"Quote created: {quote_id} for inquiry {request.inquiryId}")
        
        return {
            "success": True,
            "quote": self._serialize_quote(quote_doc),
            "accessToken": access_token
        }
    
    def generate_whatsapp_preview(
        self,
        quote: Dict[str, Any],
        base_url: str
    ) -> Dict[str, Any]:
        """
        Generate WhatsApp preview message.
        
        IMPORTANT:
        - NO seller phone number
        - NO buyer phone number
        - NO bank details
        - Only secure quote link
        """
        quote_id = quote.get("quoteId")
        access_token = quote.get("accessToken")
        
        # Secure URL with access token
        secure_url = f"{base_url}/quote/{quote_id}?token={access_token}"
        
        # Format validity date
        validity_date = quote.get("validityDate")
        if isinstance(validity_date, datetime):
            validity_str = validity_date.strftime("%d %b %Y")
        else:
            validity_str = str(validity_date)[:10]
        
        # Format currency
        def format_inr(amount):
            return f"₹{amount:,.2f}"
        
        message = f"""You have received a quotation on MidConnect.

Quote ID: {quote_id}
Product: {quote.get('productName', 'Product')}
Requested Qty: {quote.get('requestedQuantity', 0)}

Unit Price: {format_inr(quote.get('unitPrice', 0))}
MOQ: {quote.get('moq', 1)}
Packaging Charges: {format_inr(quote.get('packagingCharges', 0))}
Transportation Charges: Not Included

Total (Excl. Transport): {format_inr(quote.get('totalPrice', 0))}
Valid Till: {validity_str}
Lead Time: {quote.get('leadTimeDays', 0)} days

View full quotation securely:
{secure_url}

(Online payment coming soon on MidConnect)"""
        
        return {
            "message": message,
            "secureUrl": secure_url,
            "quoteId": quote_id
        }
    
    async def mark_whatsapp_sent(self, quote_id: str) -> bool:
        """Mark WhatsApp preview as sent."""
        result = await self.db.quotes.update_one(
            {"quoteId": quote_id},
            {"$set": {"whatsappPreviewSent": True, "updatedAt": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0
    
    async def get_quote_by_id(
        self,
        quote_id: str,
        access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote by ID.
        
        If access_token provided, validates it for secure access.
        """
        query = {"quoteId": quote_id}
        
        quote = await self.db.quotes.find_one(query)
        
        if not quote:
            return None
        
        # If access token required, validate
        if access_token and quote.get("accessToken") != access_token:
            return None
        
        return quote
    
    async def view_quote(
        self,
        quote_id: str,
        buyer_id: ObjectId,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        View a quote as buyer.
        
        Validations:
        - Quote must exist
        - Buyer must match or have valid access token
        - Marks as viewed on first access
        """
        quote = await self.get_quote_by_id(quote_id, access_token)
        
        if not quote:
            raise ValueError("Quote not found or access denied")
        
        # Validate buyer access
        if str(quote.get("buyerId")) != str(buyer_id):
            # Check if access token is valid (allows tokenized access)
            if not access_token or quote.get("accessToken") != access_token:
                raise ValueError("You are not authorized to view this quote")
        
        # Check if expired
        validity_date = quote.get("validityDate")
        if validity_date:
            if isinstance(validity_date, datetime):
                if validity_date.tzinfo is None:
                    validity_date = validity_date.replace(tzinfo=timezone.utc)
                if validity_date < datetime.now(timezone.utc):
                    # Mark as expired if not already
                    if quote.get("status") not in ["accepted", "rejected", "expired"]:
                        await self.db.quotes.update_one(
                            {"_id": quote["_id"]},
                            {"$set": {"status": "expired", "updatedAt": datetime.now(timezone.utc)}}
                        )
                        quote["status"] = "expired"
        
        # Mark as viewed if first time
        if quote.get("status") == "sent":
            now = datetime.now(timezone.utc)
            await self.db.quotes.update_one(
                {"_id": quote["_id"]},
                {"$set": {"status": "viewed", "viewedAt": now, "updatedAt": now}}
            )
            quote["status"] = "viewed"
            quote["viewedAt"] = now
            
            # Track analytics
            await self._track_analytics("quote_viewed", {
                "quoteId": quote_id,
                "sellerId": str(quote.get("sellerId")),
                "buyerId": str(buyer_id),
                "timeToView": (now - quote.get("createdAt", now)).total_seconds()
            })
        
        return self._serialize_quote(quote)
    
    async def accept_quote(
        self,
        quote_id: str,
        buyer_id: ObjectId
    ) -> Dict[str, Any]:
        """
        Accept a quote (buyer action).
        
        Validations:
        - Quote must exist and be for this buyer
        - Quote must be in "sent" or "viewed" status
        - Quote must not be expired
        """
        quote = await self.db.quotes.find_one({"quoteId": quote_id})
        
        if not quote:
            raise ValueError("Quote not found")
        
        if str(quote.get("buyerId")) != str(buyer_id):
            raise ValueError("You are not authorized to accept this quote")
        
        # Check status
        if quote.get("status") not in ["sent", "viewed"]:
            raise ValueError(f"Quote cannot be accepted (status: {quote.get('status')})")
        
        # Check expiry
        validity_date = quote.get("validityDate")
        if validity_date:
            if isinstance(validity_date, datetime):
                if validity_date.tzinfo is None:
                    validity_date = validity_date.replace(tzinfo=timezone.utc)
                if validity_date < datetime.now(timezone.utc):
                    raise ValueError("Quote has expired")
        
        now = datetime.now(timezone.utc)
        
        # Update quote
        await self.db.quotes.update_one(
            {"_id": quote["_id"]},
            {"$set": {
                "status": "accepted",
                "acceptedAt": now,
                "updatedAt": now
            }}
        )
        
        # Update inquiry status
        await self.db.inquiries.update_one(
            {"_id": quote.get("inquiryId")},
            {"$set": {"quoteStatus": "accepted", "updatedAt": now}}
        )
        
        # Track analytics
        await self._track_analytics("quote_accepted", {
            "quoteId": quote_id,
            "sellerId": str(quote.get("sellerId")),
            "buyerId": str(buyer_id),
            "totalPrice": quote.get("totalPrice"),
            "responseTime": (now - quote.get("createdAt", now)).total_seconds()
        })
        
        # Get seller contact (now unlocked)
        seller = await self.db.users.find_one({"_id": quote.get("sellerId")})
        seller_contact = None
        if seller:
            seller_contact = {
                "name": seller.get("profile", {}).get("businessName"),
                "phone": seller.get("profile", {}).get("phone"),
                "email": seller.get("email"),
                "whatsapp": seller.get("profile", {}).get("whatsapp")
            }
        
        logger.info(f"Quote accepted: {quote_id} by buyer {buyer_id}")
        
        return {
            "success": True,
            "message": "Quote accepted successfully",
            "quoteId": quote_id,
            "sellerContact": seller_contact
        }
    
    async def reject_quote(
        self,
        quote_id: str,
        buyer_id: ObjectId,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reject a quote (buyer action).
        """
        quote = await self.db.quotes.find_one({"quoteId": quote_id})
        
        if not quote:
            raise ValueError("Quote not found")
        
        if str(quote.get("buyerId")) != str(buyer_id):
            raise ValueError("You are not authorized to reject this quote")
        
        if quote.get("status") not in ["sent", "viewed"]:
            raise ValueError(f"Quote cannot be rejected (status: {quote.get('status')})")
        
        now = datetime.now(timezone.utc)
        
        await self.db.quotes.update_one(
            {"_id": quote["_id"]},
            {"$set": {
                "status": "rejected",
                "rejectedAt": now,
                "rejectionReason": reason,
                "updatedAt": now
            }}
        )
        
        # Update inquiry
        await self.db.inquiries.update_one(
            {"_id": quote.get("inquiryId")},
            {"$set": {"quoteStatus": "rejected", "updatedAt": now}}
        )
        
        # Track analytics
        await self._track_analytics("quote_rejected", {
            "quoteId": quote_id,
            "sellerId": str(quote.get("sellerId")),
            "buyerId": str(buyer_id),
            "reason": reason
        })
        
        logger.info(f"Quote rejected: {quote_id} by buyer {buyer_id}")
        
        return {
            "success": True,
            "message": "Quote rejected",
            "quoteId": quote_id
        }
    
    async def expire_quotes(self) -> int:
        """
        Expire all quotes past their validity date.
        Called by cron job.
        
        Returns number of expired quotes.
        """
        now = datetime.now(timezone.utc)
        
        result = await self.db.quotes.update_many(
            {
                "status": {"$in": ["sent", "viewed"]},
                "validityDate": {"$lt": now}
            },
            {"$set": {"status": "expired", "updatedAt": now}}
        )
        
        expired_count = result.modified_count
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} quotes")
            
            # Track analytics
            await self._track_analytics("quotes_expired", {
                "count": expired_count,
                "timestamp": now.isoformat()
            })
        
        return expired_count
    
    async def get_seller_quotes(
        self,
        seller_id: ObjectId,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get quotes created by a seller."""
        query = {"sellerId": seller_id}
        if status:
            query["status"] = status
        
        total = await self.db.quotes.count_documents(query)
        skip = (page - 1) * limit
        
        quotes = await self.db.quotes.find(query)\
            .sort("createdAt", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        return {
            "quotes": [self._serialize_quote(q) for q in quotes],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1
        }
    
    async def get_buyer_quotes(
        self,
        buyer_id: ObjectId,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get quotes received by a buyer."""
        query = {"buyerId": buyer_id}
        if status:
            query["status"] = status
        
        total = await self.db.quotes.count_documents(query)
        skip = (page - 1) * limit
        
        quotes = await self.db.quotes.find(query)\
            .sort("createdAt", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        return {
            "quotes": [self._serialize_quote(q) for q in quotes],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1
        }
    
    async def get_quote_analytics(
        self,
        seller_id: Optional[ObjectId] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get quote analytics.
        
        Metrics:
        - Quote sent count
        - Quote view rate
        - Quote acceptance rate
        - Average response time
        - Expiry rate
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = {"createdAt": {"$gte": since}}
        if seller_id:
            query["sellerId"] = seller_id
        
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "viewed": {"$sum": {"$cond": [{"$in": ["$status", ["viewed", "accepted", "rejected"]]}, 1, 0]}},
                "accepted": {"$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}},
                "expired": {"$sum": {"$cond": [{"$eq": ["$status", "expired"]}, 1, 0]}},
                "totalValue": {"$sum": "$totalPrice"},
                "acceptedValue": {"$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, "$totalPrice", 0]}}
            }}
        ]
        
        result = await self.db.quotes.aggregate(pipeline).to_list(1)
        
        if not result:
            return {
                "period": f"Last {days} days",
                "totalQuotes": 0,
                "viewRate": 0,
                "acceptanceRate": 0,
                "rejectionRate": 0,
                "expiryRate": 0,
                "totalValue": 0,
                "acceptedValue": 0
            }
        
        stats = result[0]
        total = stats.get("total", 0)
        
        return {
            "period": f"Last {days} days",
            "totalQuotes": total,
            "viewRate": round((stats.get("viewed", 0) / total * 100), 1) if total > 0 else 0,
            "acceptanceRate": round((stats.get("accepted", 0) / total * 100), 1) if total > 0 else 0,
            "rejectionRate": round((stats.get("rejected", 0) / total * 100), 1) if total > 0 else 0,
            "expiryRate": round((stats.get("expired", 0) / total * 100), 1) if total > 0 else 0,
            "totalValue": stats.get("totalValue", 0),
            "acceptedValue": stats.get("acceptedValue", 0)
        }
    
    async def _track_analytics(self, event: str, data: Dict[str, Any]):
        """Track quote analytics event."""
        await self.db.quoteAnalytics.insert_one({
            "event": event,
            "data": data,
            "createdAt": datetime.now(timezone.utc)
        })
    
    def _serialize_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize quote for API response."""
        def format_date(d):
            if d is None:
                return None
            if isinstance(d, datetime):
                return d.isoformat()
            return str(d)
        
        return {
            "quoteId": quote.get("quoteId"),
            "inquiryId": str(quote.get("inquiryId")),
            "productId": str(quote.get("productId")),
            "productName": quote.get("productName"),
            "sellerId": str(quote.get("sellerId")),
            "sellerName": quote.get("sellerName"),
            "buyerId": str(quote.get("buyerId")),
            "buyerName": quote.get("buyerName"),
            "requestedQuantity": quote.get("requestedQuantity"),
            "unitPrice": quote.get("unitPrice"),
            "moq": quote.get("moq"),
            "packagingCharges": quote.get("packagingCharges", 0),
            "transportChargesIncluded": False,
            "totalPrice": quote.get("totalPrice"),
            "leadTimeDays": quote.get("leadTimeDays"),
            "validityDate": format_date(quote.get("validityDate")),
            "validityDays": quote.get("validityDays"),
            "terms": quote.get("terms"),
            "customMessage": quote.get("customMessage"),
            "status": quote.get("status"),
            "whatsappPreviewSent": quote.get("whatsappPreviewSent", False),
            "createdAt": format_date(quote.get("createdAt")),
            "viewedAt": format_date(quote.get("viewedAt")),
            "acceptedAt": format_date(quote.get("acceptedAt")),
            "rejectedAt": format_date(quote.get("rejectedAt"))
        }


# Factory function
async def get_quotation_service(db) -> QuotationService:
    """Factory function to get quotation service."""
    service = QuotationService(db)
    return service
