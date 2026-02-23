"""
SUBSCRIPTION PAYMENT ROUTER
===========================

Payment integration for subscription activation.
Supports multiple payment gateways (Razorpay, Stripe abstracted).

Endpoints:
- POST /subscription/plans - Get available plans
- POST /subscription/create-order - Create payment order
- POST /subscription/webhook - Payment webhook (idempotent)
- POST /subscription/verify - Verify payment status
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
from bson import ObjectId
import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)

# Plan pricing configuration
PLAN_PRICING = {
    "trial": {
        "name": "Trial",
        "price": 0,
        "currency": "INR",
        "duration_days": 14,
        "features": ["14-day free trial", "Unlimited inquiries", "Basic support"]
    },
    "pro": {
        "name": "Pro",
        "price": 999,  # INR
        "currency": "INR",
        "duration_days": 30,
        "features": ["Unlimited inquiries", "Priority ranking", "Priority support", "Verified badge"]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 4999,  # INR
        "currency": "INR",
        "duration_days": 365,
        "features": ["Everything in Pro", "Dedicated support", "Custom integrations", "API access"]
    }
}


class CreateOrderRequest(BaseModel):
    """Request to create payment order."""
    planName: Literal["trial", "pro", "enterprise"]
    durationMonths: int = Field(default=1, ge=1, le=12)


class WebhookPayload(BaseModel):
    """Payment webhook payload."""
    paymentId: str
    orderId: str
    status: Literal["success", "failed", "pending"]
    amount: int
    currency: str = "INR"
    planName: str
    userId: str
    signature: str


class VerifyPaymentRequest(BaseModel):
    """Request to verify payment."""
    paymentId: str
    orderId: str


def create_subscription_payment_router(db, get_current_user):
    """
    Create subscription payment router with database dependency.
    """
    router = APIRouter(prefix="/subscription", tags=["subscription-payments"])
    
    # Import engine
    from services.subscription_engine import SubscriptionEngine
    
    @router.get("/plans")
    async def get_subscription_plans():
        """
        Get available subscription plans and pricing.
        """
        return {
            "plans": PLAN_PRICING,
            "currency": "INR",
            "taxInfo": "Prices inclusive of GST"
        }
    
    @router.post("/create-order")
    async def create_payment_order(
        request: CreateOrderRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Create a payment order for subscription.
        
        Flow:
        1. Validate plan
        2. Calculate total price
        3. Create temporary order record
        4. Return order details for frontend payment
        
        Note: In production, this would integrate with Razorpay/Stripe.
        For MVP, we simulate order creation.
        """
        plan = PLAN_PRICING.get(request.planName)
        if not plan:
            raise HTTPException(status_code=400, detail="Invalid plan")
        
        # Calculate total price
        base_price = plan["price"]
        total_months = request.durationMonths
        total_price = base_price * total_months
        
        # Calculate duration
        duration_days = plan["duration_days"] * total_months
        
        now = datetime.now(timezone.utc)
        order_id = f"order_{ObjectId()}"
        
        # Store order in database
        order_doc = {
            "_id": ObjectId(),
            "orderId": order_id,
            "userId": current_user["_id"],
            "planName": request.planName,
            "amount": total_price,
            "currency": plan["currency"],
            "durationDays": duration_days,
            "durationMonths": total_months,
            "status": "pending",
            "createdAt": now,
            "expiresAt": now + timedelta(minutes=30)  # Order expires in 30 min
        }
        
        await db.subscriptionOrders.insert_one(order_doc)
        
        logger.info(f"Created order {order_id} for user {current_user['_id']} - {request.planName}")
        
        return {
            "orderId": order_id,
            "amount": total_price,
            "currency": plan["currency"],
            "planName": request.planName,
            "durationDays": duration_days,
            "description": f"{plan['name']} Plan - {total_months} month(s)",
            # In production, would include payment gateway specific fields:
            # "razorpayOrderId": "...",
            # "razorpayKey": "...",
        }
    
    @router.post("/webhook")
    async def payment_webhook(request: Request):
        """
        Payment webhook endpoint.
        
        CRITICAL:
        - Verify signature
        - Check payment status
        - Idempotent processing (check if paymentId already processed)
        - Activate/extend subscription
        
        Note: In production, signature verification would use gateway secret.
        """
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")
        
        payment_id = payload.get("paymentId")
        order_id = payload.get("orderId")
        status = payload.get("status")
        user_id = payload.get("userId")
        signature = payload.get("signature")
        
        if not all([payment_id, order_id, status, user_id]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Verify signature (in production, use actual gateway secret)
        # For MVP, we use a simple HMAC verification
        webhook_secret = os.environ.get("WEBHOOK_SECRET", "dev_webhook_secret")
        expected_sig = hmac.new(
            webhook_secret.encode(),
            f"{payment_id}|{order_id}|{status}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature and signature != expected_sig:
            logger.warning(f"Invalid webhook signature for payment {payment_id}")
            # In production, would reject. For dev, log and continue
        
        # Get order
        order = await db.subscriptionOrders.find_one({"orderId": order_id})
        if not order:
            logger.error(f"Order {order_id} not found for payment {payment_id}")
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check if payment already processed (idempotency)
        engine = SubscriptionEngine(db)
        if await engine.check_payment_processed(payment_id):
            logger.info(f"Payment {payment_id} already processed - idempotent return")
            return {"status": "ok", "message": "Payment already processed"}
        
        # Only process successful payments
        if status != "success":
            await db.subscriptionOrders.update_one(
                {"orderId": order_id},
                {"$set": {"status": status, "updatedAt": datetime.now(timezone.utc)}}
            )
            return {"status": "ok", "message": f"Payment {status}"}
        
        # Activate subscription
        result = await engine.activate_or_extend(
            user_id=ObjectId(user_id),
            plan_name=order["planName"],
            duration_days=order["durationDays"],
            source="payment",
            payment_id=payment_id
        )
        
        # Update order status
        await db.subscriptionOrders.update_one(
            {"orderId": order_id},
            {"$set": {
                "status": "completed",
                "paymentId": payment_id,
                "completedAt": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"Payment {payment_id} processed - subscription {result['action']}")
        
        return {
            "status": "ok",
            "message": "Subscription activated",
            "action": result["action"]
        }
    
    @router.post("/verify")
    async def verify_payment(
        request: VerifyPaymentRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Verify payment status and return subscription details.
        Called by frontend after payment completion.
        """
        order = await db.subscriptionOrders.find_one({
            "orderId": request.orderId,
            "userId": current_user["_id"]
        })
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get current subscription
        engine = SubscriptionEngine(db)
        subscription = await engine.get_active_subscription(current_user["_id"])
        
        return {
            "order": {
                "orderId": order["orderId"],
                "status": order.get("status", "pending"),
                "planName": order["planName"],
                "amount": order["amount"]
            },
            "subscription": subscription if subscription else None,
            "verified": order.get("status") == "completed"
        }
    
    @router.post("/simulate-payment")
    async def simulate_payment(
        order_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """
        DEV ONLY: Simulate successful payment for testing.
        Remove in production.
        """
        order = await db.subscriptionOrders.find_one({
            "orderId": order_id,
            "userId": current_user["_id"]
        })
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        payment_id = f"pay_{ObjectId()}"
        
        # Process as if webhook received
        engine = SubscriptionEngine(db)
        result = await engine.activate_or_extend(
            user_id=current_user["_id"],
            plan_name=order["planName"],
            duration_days=order["durationDays"],
            source="payment",
            payment_id=payment_id
        )
        
        # Update order
        await db.subscriptionOrders.update_one(
            {"orderId": order_id},
            {"$set": {
                "status": "completed",
                "paymentId": payment_id,
                "completedAt": datetime.now(timezone.utc)
            }}
        )
        
        return {
            "success": True,
            "paymentId": payment_id,
            "subscription": result["subscription"],
            "action": result["action"]
        }
    
    return router


# Import timedelta for order expiry
from datetime import timedelta
