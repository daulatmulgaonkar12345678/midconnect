"""
QUOTATION API ROUTER
====================

Enterprise quotation endpoints for B2B marketplace.

Endpoints:
- POST /quotes/create - Create quote (seller)
- GET /quotes/{quoteId} - View quote (buyer)
- POST /quotes/{quoteId}/accept - Accept quote (buyer)
- POST /quotes/{quoteId}/reject - Reject quote (buyer)
- GET /quotes/seller - List seller quotes
- GET /quotes/buyer - List buyer quotes
- GET /quotes/analytics - Quote analytics
- POST /quotes/{quoteId}/whatsapp-preview - Get WhatsApp message
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
from bson import ObjectId
import logging
import os

logger = logging.getLogger(__name__)


class CreateQuoteRequest(BaseModel):
    """Request to create a quote."""
    inquiryId: str
    unitPrice: float = Field(..., gt=0)
    moq: int = Field(..., ge=1)
    leadTimeDays: int = Field(..., ge=1, le=365)
    validityDays: int = Field(default=7, ge=1, le=30)
    packagingCharges: float = Field(default=0, ge=0)
    terms: Optional[str] = Field(default=None, max_length=2000)
    customMessage: Optional[str] = Field(default=None, max_length=1000)


class RejectQuoteRequest(BaseModel):
    """Request to reject a quote."""
    reason: Optional[str] = Field(default=None, max_length=500)


def create_quotation_router(db, get_current_user):
    """
    Create quotation router with database dependency.
    """
    router = APIRouter(prefix="/quotes", tags=["quotes"])
    
    from services.quotation_service import QuotationService, QuoteCreateRequest
    
    # ==========================================
    # SELLER ENDPOINTS
    # ==========================================
    
    @router.post("/create")
    async def create_quote(
        request: CreateQuoteRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Create a quote for an accepted inquiry.
        
        Seller must have accepted the inquiry first.
        Only one active quote per inquiry allowed.
        """
        if "seller" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Only sellers can create quotes")
        
        service = QuotationService(db)
        
        try:
            quote_request = QuoteCreateRequest(
                inquiryId=request.inquiryId,
                unitPrice=request.unitPrice,
                moq=request.moq,
                leadTimeDays=request.leadTimeDays,
                validityDays=request.validityDays,
                packagingCharges=request.packagingCharges,
                terms=request.terms,
                customMessage=request.customMessage
            )
            
            result = await service.create_quote(
                seller_id=current_user["_id"],
                request=quote_request
            )
            
            return result
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating quote: {e}")
            raise HTTPException(status_code=500, detail="Failed to create quote")
    
    @router.get("/seller")
    async def get_seller_quotes(
        status: Optional[Literal["sent", "viewed", "accepted", "rejected", "expired"]] = None,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get quotes created by the current seller.
        """
        if "seller" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Only sellers can access this")
        
        service = QuotationService(db)
        return await service.get_seller_quotes(
            seller_id=current_user["_id"],
            status=status,
            page=page,
            limit=limit
        )
    
    @router.post("/{quote_id}/whatsapp-redirect")
    async def get_whatsapp_redirect(
        quote_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Generate WhatsApp redirect link for a quote.
        
        Per spec:
        - Returns structured message with secure quote link
        - Marks quote as whatsappRedirectUsed = true
        - Returns wa.me link with buyer phone if available
        
        Security:
        - Only the seller who created the quote can access
        - No contact details leaked in message
        """
        if "seller" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Only sellers can access this")
        
        service = QuotationService(db)
        
        quote = await service.get_quote_by_id(quote_id)
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")
        
        if str(quote.get("sellerId")) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Get buyer phone for WhatsApp link
        buyer_phone = quote.get("buyerPhone")
        
        # If not in quote, try to fetch from inquiry/user
        if not buyer_phone:
            inquiry = await db.inquiries.find_one({"_id": quote.get("inquiryId")})
            if inquiry and inquiry.get("status") == "accepted":
                buyer = await db.users.find_one({"_id": quote.get("buyerId")})
                if buyer:
                    buyer_phone = buyer.get("profile", {}).get("phone") or buyer.get("phone")
        
        # Generate base URL
        base_url = os.environ.get("FRONTEND_URL", "https://midconnect-fix.preview.emergentagent.com")
        
        preview = service.generate_whatsapp_preview(quote, base_url)
        
        # Mark as WhatsApp redirect used
        await service.mark_whatsapp_redirect_used(quote_id)
        
        # Generate WhatsApp link if phone available
        whatsapp_link = None
        if buyer_phone:
            # Clean phone number
            phone_clean = buyer_phone.replace(" ", "").replace("-", "").replace("+", "")
            if not phone_clean.startswith("91"):
                phone_clean = "91" + phone_clean
            
            # URL encode message
            from urllib.parse import quote as url_quote
            encoded_message = url_quote(preview["message"])
            whatsapp_link = f"https://wa.me/{phone_clean}?text={encoded_message}"
        
        return {
            "message": preview["message"],
            "secureUrl": preview["secureUrl"],
            "quoteId": quote_id,
            "whatsappLink": whatsapp_link,
            "buyerPhoneAvailable": buyer_phone is not None
        }
    
    @router.get("/analytics")
    async def get_quote_analytics(
        days: int = Query(30, ge=1, le=365),
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get quote analytics for the current seller.
        """
        if "seller" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Only sellers can access this")
        
        service = QuotationService(db)
        return await service.get_quote_analytics(
            seller_id=current_user["_id"],
            days=days
        )
    
    # ==========================================
    # BUYER ENDPOINTS
    # ==========================================
    
    @router.get("/buyer")
    async def get_buyer_quotes(
        status: Optional[Literal["sent", "viewed", "accepted", "rejected", "expired"]] = None,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get quotes received by the current buyer.
        """
        service = QuotationService(db)
        return await service.get_buyer_quotes(
            buyer_id=current_user["_id"],
            status=status,
            page=page,
            limit=limit
        )
    
    @router.get("/{quote_id}")
    async def view_quote(
        quote_id: str,
        token: Optional[str] = Query(None, description="Secure access token"),
        current_user: dict = Depends(get_current_user)
    ):
        """
        View a quote.
        
        Validates buyer access.
        Marks as viewed on first access.
        Returns full quote details.
        """
        service = QuotationService(db)
        
        try:
            quote = await service.view_quote(
                quote_id=quote_id,
                buyer_id=current_user["_id"],
                access_token=token
            )
            
            return {
                "quote": quote,
                "canAccept": quote.get("status") in ["sent", "viewed"],
                "isExpired": quote.get("status") == "expired",
                "paymentComingSoon": True  # Banner flag
            }
            
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            logger.error(f"Error viewing quote: {e}")
            raise HTTPException(status_code=500, detail="Failed to view quote")
    
    @router.post("/{quote_id}/accept")
    async def accept_quote(
        quote_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Accept a quote.
        
        Only the buyer who received the quote can accept.
        Quote must not be expired.
        Unlocks seller contact information.
        """
        service = QuotationService(db)
        
        try:
            result = await service.accept_quote(
                quote_id=quote_id,
                buyer_id=current_user["_id"]
            )
            
            return result
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error accepting quote: {e}")
            raise HTTPException(status_code=500, detail="Failed to accept quote")
    
    @router.post("/{quote_id}/reject")
    async def reject_quote(
        quote_id: str,
        request: RejectQuoteRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Reject a quote.
        
        Optionally provide a reason.
        """
        service = QuotationService(db)
        
        try:
            result = await service.reject_quote(
                quote_id=quote_id,
                buyer_id=current_user["_id"],
                reason=request.reason
            )
            
            return result
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error rejecting quote: {e}")
            raise HTTPException(status_code=500, detail="Failed to reject quote")
    
    # ==========================================
    # PUBLIC ENDPOINTS (with token)
    # ==========================================
    
    @router.get("/public/{quote_id}")
    async def view_quote_public(
        quote_id: str,
        token: str = Query(..., description="Secure access token")
    ):
        """
        View a quote via secure public link (from WhatsApp).
        
        Requires valid access token.
        Does not require authentication.
        Redirects to login if accepting.
        """
        service = QuotationService(db)
        
        quote = await service.get_quote_by_id(quote_id, access_token=token)
        
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found or invalid token")
        
        # Check expiry
        validity_date = quote.get("validityDate")
        is_expired = False
        if validity_date:
            if isinstance(validity_date, datetime):
                if validity_date.tzinfo is None:
                    validity_date = validity_date.replace(tzinfo=timezone.utc)
                is_expired = validity_date < datetime.now(timezone.utc)
        
        # Return limited public view
        # Format createdAt for public view
        created_at = quote.get("createdAt")
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = str(created_at) if created_at else None
        
        return {
            "quote": {
                "quoteId": quote.get("quoteId"),
                "productName": quote.get("productName"),
                "sellerName": quote.get("sellerName"),
                "requestedQuantity": quote.get("requestedQuantity"),
                "unitPrice": quote.get("unitPrice"),
                "moq": quote.get("moq"),
                "packagingCharges": quote.get("packagingCharges", 0),
                "transportChargesIncluded": False,
                "totalPrice": quote.get("totalPrice"),
                "leadTimeDays": quote.get("leadTimeDays"),
                "validityDate": quote.get("validityDate").isoformat() if isinstance(quote.get("validityDate"), datetime) else quote.get("validityDate"),
                "terms": quote.get("terms"),
                "customMessage": quote.get("customMessage"),
                "status": quote.get("status"),
                "createdAt": created_at_str
            },
            "isExpired": is_expired,
            "requiresLogin": True,  # Flag to show login prompt for accepting
            "paymentComingSoon": True
        }
    
    # ==========================================
    # ADMIN/CRON ENDPOINTS
    # ==========================================
    
    @router.post("/admin/expire-quotes")
    async def run_expiry_job():
        """
        Run quote expiry job.
        Called by cron or admin.
        """
        # In production, add admin auth
        service = QuotationService(db)
        
        expired_count = await service.expire_quotes()
        
        return {
            "success": True,
            "expiredCount": expired_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @router.get("/admin/analytics")
    async def get_platform_analytics(
        days: int = Query(30, ge=1, le=365)
    ):
        """
        Get platform-wide quote analytics.
        """
        # In production, add admin auth
        service = QuotationService(db)
        return await service.get_quote_analytics(seller_id=None, days=days)
    
    return router
