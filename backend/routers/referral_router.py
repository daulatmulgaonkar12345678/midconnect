"""
REFERRAL SYSTEM ROUTER
======================
Dual system:
1. Referral rewards → for engagement (existing tiers, activation-based)
2. Sales tracking → for monetization (commission on admin-activated paid subscriptions)

Endpoints:
- GET  /referral/my-link           → Get/generate referral code & link
- GET  /referral/stats             → Get referral stats for dashboard
- GET  /referral/sales-stats       → Get sales tracking metrics (paid customers, earnings)
- POST /referral/track-signup      → Link a new user to their referrer
- POST /referral/check-activation  → Check if referred user completed activation criteria
- GET  /referral/admin/sales-overview → Admin: full revenue, commission, user details
- GET  /referral/admin/plan-config → Admin: get plan pricing config
- PUT  /referral/admin/plan-config → Admin: update plan pricing config
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import random
import string
import logging

logger = logging.getLogger(__name__)

REFERRAL_TIERS = [
    {"min_referrals": 10, "reward_days": 180, "label": "6 months free"},
    {"min_referrals": 5,  "reward_days": 90,  "label": "3 months free"},
    {"min_referrals": 1,  "reward_days": 30,  "label": "1 month free"},
]

ACTIVATION_WINDOW_DAYS = 7
ACTIVATION_CRITERIA_NEEDED = 2  # Must meet 2 of 3
DEFAULT_COMMISSION_RATE = 0.20  # 20%

# Paid plan names — only these trigger order creation
PAID_PLANS = {"starter", "standard", "pro"}

# Default plan pricing & commission (seeded to plan_config collection)
DEFAULT_PLAN_CONFIG = {
    "starter": {"price": 5000, "commissionPercent": 20},
    "standard": {"price": 10000, "commissionPercent": 20},
    "pro": {"price": 15000, "commissionPercent": 20},
}


class TrackSignupRequest(BaseModel):
    referralCode: str = Field(..., min_length=3, max_length=20)


class PlanConfigUpdate(BaseModel):
    price: int = Field(..., ge=0)
    commissionPercent: float = Field(..., ge=0, le=100)


def init_referral_router(db, verify_token_func):
    router = APIRouter()

    async def get_current_user(authorization: str):
        from utils.permissions import authenticate_user
        return await authenticate_user(db, verify_token_func, authorization)

    def serialize_doc(doc):
        if doc is None:
            return None
        if isinstance(doc, list):
            return [serialize_doc(d) for d in doc]
        if isinstance(doc, dict):
            result = {}
            for key, value in doc.items():
                if key == "_id":
                    result["id"] = str(value)
                elif isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, dict):
                    result[key] = serialize_doc(value)
                elif isinstance(value, list):
                    result[key] = serialize_doc(value)
                else:
                    result[key] = value
            return result
        return doc

    # ── Helpers ──

    async def _generate_unique_code(user) -> str:
        """FIRSTNAME + 4 random digits, uppercase, unique."""
        profile = user.get("profile", {})
        name = profile.get("businessName", "") or user.get("email", "user")
        prefix = "".join(c for c in name.upper() if c.isalpha())[:3]
        if len(prefix) < 3:
            prefix = prefix.ljust(3, "X")

        for _ in range(20):
            digits = "".join(random.choices(string.digits, k=4))
            code = f"{prefix}{digits}"
            existing = await db.users.find_one({"referralCode": code})
            if not existing:
                return code
        # Fallback: fully random
        return "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

    def _get_tier(count: int):
        """Return the highest tier the user qualifies for."""
        for tier in REFERRAL_TIERS:
            if count >= tier["min_referrals"]:
                return tier
        return None

    def _get_next_tier(count: int):
        """Return the next tier to unlock."""
        for tier in reversed(REFERRAL_TIERS):
            if count < tier["min_referrals"]:
                return tier
        return None

    async def _check_activation_criteria(user_id: str) -> dict:
        """Check if a referred user meets 2 of 3 activation criteria."""
        uid = ObjectId(user_id)
        seller_listing_count = await db.sellerListings.count_documents({"sellerId": uid})
        invoice_count = await db.invoices.count_documents({
            "sellerId": uid,
            "total": {"$gt": 0}  # Anti-abuse: no ₹0 invoices
        })
        buyer_count = await db.seller_buyers.count_documents({"sellerId": uid})
        supplier_count = await db.suppliers.count_documents({"sellerId": uid})

        criteria_met = 0
        criteria_details = []

        # Criterion 1: ≥ 5 products
        if seller_listing_count >= 5:
            criteria_met += 1
            criteria_details.append({"name": "products", "met": True, "current": seller_listing_count, "required": 5})
        else:
            criteria_details.append({"name": "products", "met": False, "current": seller_listing_count, "required": 5})

        # Criterion 2: ≥ 3 invoices (non-zero amount)
        if invoice_count >= 3:
            criteria_met += 1
            criteria_details.append({"name": "invoices", "met": True, "current": invoice_count, "required": 3})
        else:
            criteria_details.append({"name": "invoices", "met": False, "current": invoice_count, "required": 3})

        # Criterion 3: ≥ 1 buyer AND ≥ 1 supplier
        has_buyer_supplier = buyer_count >= 1 and supplier_count >= 1
        if has_buyer_supplier:
            criteria_met += 1
            criteria_details.append({"name": "buyer_supplier", "met": True, "current": {"buyers": buyer_count, "suppliers": supplier_count}, "required": "1 buyer + 1 supplier"})
        else:
            criteria_details.append({"name": "buyer_supplier", "met": False, "current": {"buyers": buyer_count, "suppliers": supplier_count}, "required": "1 buyer + 1 supplier"})

        return {
            "criteriaMet": criteria_met,
            "criteriaNeeded": ACTIVATION_CRITERIA_NEEDED,
            "activated": criteria_met >= ACTIVATION_CRITERIA_NEEDED,
            "details": criteria_details
        }

    async def _apply_referral_reward(referrer_id):
        """Apply tier-based reward to referrer's subscription."""
        referrer = await db.users.find_one({"_id": referrer_id})
        if not referrer:
            return

        referral_count = referrer.get("referralSuccessCount", 0)
        tier = _get_tier(referral_count)
        if not tier:
            return

        now = datetime.now(timezone.utc)
        sub = referrer.get("subscription", {})

        # Calculate the new end date based on tier (NOT cumulative per referral)
        reward_days = tier["reward_days"]

        # Start from current subscription end or trial end or now
        current_end = sub.get("endDate") or sub.get("trialEndsAt") or now
        if isinstance(current_end, str):
            current_end = datetime.fromisoformat(current_end.replace("Z", "+00:00"))

        # The reward grants X days total from signup, not stacking
        # If referrer already has reward applied, update to highest tier
        referral_reward_start = referrer.get("referralRewardStart", now)
        new_end = referral_reward_start + timedelta(days=reward_days)

        # Never reduce existing subscription
        if new_end < current_end:
            new_end = current_end

        plan = sub.get("plan", "free")
        if plan in ("free", "trial"):
            plan = "referral_premium"

        await db.users.update_one(
            {"_id": referrer_id},
            {"$set": {
                "subscription.endDate": new_end,
                "subscription.plan": plan,
                "subscription.status": "active",
                "referralRewardStart": referral_reward_start if referrer.get("referralRewardStart") else now,
                "referralRewardTier": tier["label"],
                "updatedAt": now,
            }}
        )
        logger.info(f"Referral reward applied: {referrer.get('email')} → {tier['label']} (end: {new_end})")

    # ── Endpoints ──

    @router.get("/referral/my-link")
    async def get_referral_link(authorization: str = Header(...)):
        """Get or generate referral link for the current user."""
        user = await get_current_user(authorization)
        user_id = str(user["_id"])

        # Check if user already has a referral code
        code = user.get("referralCode")
        if not code:
            code = await _generate_unique_code(user)
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"referralCode": code, "updatedAt": datetime.now(timezone.utc)}}
            )

        # Build the link using the app domain
        base_url = "https://www.udyogconnect.in"
        link = f"{base_url}/register?ref={code}"

        return {
            "referralCode": code,
            "referralLink": link,
            "userId": user_id,
        }

    @router.get("/referral/stats")
    async def get_referral_stats(authorization: str = Header(...)):
        """Get referral statistics for dashboard display."""
        user = await get_current_user(authorization)

        total_referred = user.get("referralCount", 0)
        successful = user.get("referralSuccessCount", 0)
        pending = total_referred - successful

        current_tier = _get_tier(successful)
        next_tier = _get_next_tier(successful)

        # Get list of referred users with live activation progress
        referred_users = []
        ref_code = user.get("referralCode")
        if ref_code:
            cursor = db.users.find(
                {"referredBy": ref_code},
                {"_id": 1, "profile.businessName": 1, "createdAt": 1, "referralActivated": 1, "referralRewarded": 1, "referralActivationDeadline": 1}
            ).sort("createdAt", -1).limit(15)
            async for u in cursor:
                uid = u["_id"]
                # Fetch live progress for each referred user
                products = await db.sellerListings.count_documents({"sellerId": uid})
                invoices = await db.invoices.count_documents({"sellerId": uid, "total": {"$gt": 0}})
                buyers_count = await db.seller_buyers.count_documents({"sellerId": uid})
                suppliers_count = await db.suppliers.count_documents({"sellerId": uid})
                has_buyer_supplier = buyers_count >= 1 and suppliers_count >= 1

                # Determine status
                activated = u.get("referralActivated", False)
                if activated:
                    status = "completed"
                elif products > 0 or invoices > 0 or buyers_count > 0 or suppliers_count > 0:
                    status = "partial"
                else:
                    status = "pending"

                name = u.get("profile", {}).get("businessName", "")
                if not name:
                    name = u.get("profile", {}).get("fullName", "New User")

                joined = u.get("createdAt")
                joined_str = joined.isoformat() if hasattr(joined, "isoformat") else str(joined or "")

                referred_users.append({
                    "name": name or "New User",
                    "joinedAt": joined_str,
                    "status": status,
                    "activated": activated,
                    "rewarded": u.get("referralRewarded", False),
                    "progress": {
                        "products": min(products, 5),
                        "productsRequired": 5,
                        "invoices": min(invoices, 3),
                        "invoicesRequired": 3,
                        "buyerSupplier": has_buyer_supplier,
                    }
                })

        # Sort: completed first, then partial, then pending
        status_order = {"completed": 0, "partial": 1, "pending": 2}
        referred_users.sort(key=lambda x: status_order.get(x["status"], 3))

        return {
            "referralCode": user.get("referralCode", ""),
            "totalReferred": total_referred,
            "successfulReferrals": successful,
            "pendingReferrals": pending,
            "currentTier": current_tier,
            "nextTier": next_tier,
            "referralsToNextTier": (next_tier["min_referrals"] - successful) if next_tier else 0,
            "referredUsers": referred_users,
            "rewardTier": user.get("referralRewardTier"),
            "tiers": REFERRAL_TIERS,
        }

    @router.post("/referral/track-signup")
    async def track_referral_signup(data: TrackSignupRequest, authorization: str = Header(...)):
        """Called after signup to link the new user to their referrer."""
        user = await get_current_user(authorization)

        # Don't allow self-referral
        if user.get("referralCode") == data.referralCode:
            raise HTTPException(status_code=400, detail="Cannot refer yourself")

        # Check if already referred
        if user.get("referredBy"):
            return {"message": "Already referred", "referredBy": user.get("referredBy")}

        # Find the referrer
        referrer = await db.users.find_one({"referralCode": data.referralCode})
        if not referrer:
            raise HTTPException(status_code=404, detail="Invalid referral code")

        # Anti-abuse: same phone check
        user_phone = user.get("profile", {}).get("phone", "")
        referrer_phone = referrer.get("profile", {}).get("phone", "")
        if user_phone and referrer_phone and user_phone == referrer_phone:
            raise HTTPException(status_code=400, detail="Cannot use same phone number")

        # Anti-abuse: same email check
        user_email = (user.get("email") or "").lower().strip()
        referrer_email = (referrer.get("email") or "").lower().strip()
        if user_email and referrer_email and user_email == referrer_email:
            raise HTTPException(status_code=400, detail="Cannot use same email address")

        now = datetime.now(timezone.utc)

        # Link the user to the referrer
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "referredBy": data.referralCode,
                "referredAt": now,
                "referralActivated": False,
                "referralRewarded": False,
                "referralActivationDeadline": now + timedelta(days=ACTIVATION_WINDOW_DAYS),
                "updatedAt": now,
            }}
        )

        # Increment referrer's count
        await db.users.update_one(
            {"_id": referrer["_id"]},
            {
                "$inc": {"referralCount": 1},
                "$set": {"updatedAt": now},
            }
        )

        logger.info(f"Referral tracked: {user.get('email')} referred by {referrer.get('email')} (code: {data.referralCode})")
        return {"message": "Referral tracked successfully", "referredBy": data.referralCode}

    @router.post("/referral/check-activation")
    async def check_and_reward_activation(authorization: str = Header(...)):
        """
        Check if the current user (referred user) has completed activation criteria.
        If yes and within time window, reward the referrer.
        Called periodically by the frontend (e.g., on dashboard load).
        """
        user = await get_current_user(authorization)

        # Only check if user was referred
        referral_code = user.get("referredBy")
        if not referral_code:
            return {"message": "Not a referred user", "activated": False}

        # Skip if already activated and rewarded
        if user.get("referralRewarded"):
            return {"message": "Already rewarded", "activated": True, "rewarded": True}

        # Check time window
        deadline = user.get("referralActivationDeadline")
        now = datetime.now(timezone.utc)
        if deadline and isinstance(deadline, datetime) and now > deadline:
            return {"message": "Activation window expired", "activated": False, "expired": True}

        # Check activation criteria
        user_id = str(user["_id"])
        result = await _check_activation_criteria(user_id)

        if not result["activated"]:
            return {"message": "Activation criteria not yet met", **result}

        # Mark user as activated
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "referralActivated": True,
                "referralActivatedAt": now,
                "referralRewarded": True,
                "updatedAt": now,
            }}
        )

        # Find and reward the referrer
        referrer = await db.users.find_one({"referralCode": referral_code})
        if referrer:
            # Increment successful count
            await db.users.update_one(
                {"_id": referrer["_id"]},
                {
                    "$inc": {"referralSuccessCount": 1},
                    "$set": {"updatedAt": now},
                }
            )
            # Refresh referrer data after increment
            referrer = await db.users.find_one({"_id": referrer["_id"]})
            await _apply_referral_reward(referrer["_id"])
            logger.info(f"Referral activation complete: {user.get('email')} → rewarded {referrer.get('email')}")

        return {
            "message": "Activation complete! Referrer has been rewarded.",
            "activated": True,
            "rewarded": True,
            **result
        }

    # ══════════════════════════════════════════════════════
    # SALES TRACKING SYSTEM (Dual: orders + legacy referral_commissions)
    # ══════════════════════════════════════════════════════

    # ── Plan Config Management ──

    async def _seed_plan_config():
        """Seed default plan_config if collection is empty."""
        count = await db.plan_config.count_documents({})
        if count == 0:
            now = datetime.now(timezone.utc)
            for plan_name, config in DEFAULT_PLAN_CONFIG.items():
                await db.plan_config.insert_one({
                    "plan": plan_name,
                    "price": config["price"],
                    "commissionPercent": config["commissionPercent"],
                    "createdAt": now,
                    "updatedAt": now,
                })
            logger.info("Seeded default plan_config collection")

    async def _get_plan_config(plan_name: str) -> dict:
        """Fetch plan pricing from plan_config collection."""
        config = await db.plan_config.find_one({"plan": plan_name}, {"_id": 0})
        if not config:
            fallback = DEFAULT_PLAN_CONFIG.get(plan_name)
            if fallback:
                return fallback
            return None
        return config

    # Seed on router init
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_seed_plan_config())
        else:
            loop.run_until_complete(_seed_plan_config())
    except RuntimeError:
        pass

    # ── Legacy: Invoice-based commission (kept for backward compat) ──

    async def record_referral_commission(invoice_doc: dict, seller_id: str):
        """Called when an invoice becomes fully paid. Records commission if seller was referred.
        LEGACY system — kept for backward compatibility. New orders use orders collection."""
        try:
            seller = await db.users.find_one({"_id": ObjectId(seller_id)}, {"referredBy": 1})
            if not seller or not seller.get("referredBy"):
                return

            ref_code = seller["referredBy"]
            invoice_id = invoice_doc.get("_id")
            total = invoice_doc.get("total", 0)
            if total <= 0:
                return

            existing = await db.referral_commissions.find_one({"invoiceId": invoice_id})
            if existing:
                return

            commission = round(total * DEFAULT_COMMISSION_RATE, 2)

            await db.referral_commissions.insert_one({
                "invoiceId": invoice_id,
                "sellerId": ObjectId(seller_id),
                "referredBy": ref_code,
                "orderAmount": round(total, 2),
                "commissionRate": DEFAULT_COMMISSION_RATE,
                "commission": commission,
                "status": "pending",
                "createdAt": datetime.now(timezone.utc),
            })
            logger.info(f"[LEGACY] Referral commission recorded: invoice={invoice_id}")
        except Exception as e:
            logger.warning(f"Failed to record referral commission: {e}")

    router.record_referral_commission = record_referral_commission

    # ── NEW: Order creation on admin subscription activation ──

    async def create_order_on_activation(user_id: str, plan_name: str):
        """Called after admin activates a PAID subscription.
        Creates an order record if all conditions are met:
        1. Plan is paid (starter/standard/pro)
        2. User has referredBy
        3. No existing order for this user (first activation only)
        """
        try:
            if plan_name not in PAID_PLANS:
                return None

            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return None

            ref_code = user.get("referredBy")
            if not ref_code:
                return None

            # Duplicate prevention: one order per user
            existing_order = await db.orders.find_one({"userId": ObjectId(user_id)})
            if existing_order:
                logger.info(f"[ORDERS] Skipped duplicate order for user {user_id}")
                return None

            # Fetch dynamic pricing from plan_config
            config = await _get_plan_config(plan_name)
            if not config:
                logger.warning(f"[ORDERS] No plan_config for plan: {plan_name}")
                return None

            amount = config["price"]
            commission_pct = config["commissionPercent"]
            commission = round(amount * commission_pct / 100, 2)

            now = datetime.now(timezone.utc)

            order_doc = {
                "userId": ObjectId(user_id),
                "referredBy": ref_code,
                "plan": plan_name,
                "amount": amount,
                "commission": commission,
                "commissionPercent": commission_pct,
                "status": "paid",
                "createdAt": now,
            }

            result = await db.orders.insert_one(order_doc)

            # Update user subscription fields
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "subscriptionStatus": "active",
                    "subscriptionType": "paid",
                    "plan": plan_name,
                    "updatedAt": now,
                }}
            )

            logger.info(f"[ORDERS] Created order: user={user_id}, plan={plan_name}, amount={amount}, commission={commission}, referredBy={ref_code}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"[ORDERS] Failed to create order: {e}")
            return None

    # Expose for server.py to call
    router.create_order_on_activation = create_order_on_activation

    # ── Sales Stats (User view — reads from orders, fallback to referral_commissions) ──

    @router.get("/referral/sales-stats")
    async def get_sales_stats(authorization: str = Header(...)):
        """Get sales tracking metrics for the referral agent (user view).
        Shows: paid customers count, total earnings, pending earnings.
        Does NOT show total revenue or commission % (admin only)."""
        user = await get_current_user(authorization)
        ref_code = user.get("referralCode")
        if not ref_code:
            return {
                "paidCustomers": 0,
                "totalEarnings": 0,
                "pendingEarnings": 0,
                "paidOutEarnings": 0,
            }

        # Primary: orders collection
        orders = await db.orders.find({"referredBy": ref_code}).to_list(10000)
        orders_total = sum(o.get("commission", 0) for o in orders)
        orders_pending = sum(o.get("commission", 0) for o in orders if o.get("status") == "paid")
        orders_paid_out = sum(o.get("commission", 0) for o in orders if o.get("status") == "paid_out")
        orders_customer_count = len(orders)

        # Fallback: legacy referral_commissions
        legacy = await db.referral_commissions.find({"referredBy": ref_code}).to_list(10000)
        legacy_total = sum(c.get("commission", 0) for c in legacy)
        legacy_pending = sum(c.get("commission", 0) for c in legacy if c.get("status") == "pending")
        legacy_paid_out = sum(c.get("commission", 0) for c in legacy if c.get("status") == "paid_out")

        # Unique paid customers from legacy (unique sellerIds)
        legacy_seller_ids = set()
        for c in legacy:
            sid = c.get("sellerId")
            if sid:
                legacy_seller_ids.add(str(sid))
        # Subtract any overlap (users who have both an order and legacy commission)
        order_user_ids = {str(o.get("userId")) for o in orders}
        legacy_only_customers = len(legacy_seller_ids - order_user_ids)

        total_paid_customers = orders_customer_count + legacy_only_customers
        total_earnings = round(orders_total + legacy_total, 2)
        pending_earnings = round(orders_pending + legacy_pending, 2)
        paid_out_earnings = round(orders_paid_out + legacy_paid_out, 2)

        return {
            "paidCustomers": total_paid_customers,
            "totalEarnings": total_earnings,
            "pendingEarnings": pending_earnings,
            "paidOutEarnings": paid_out_earnings,
        }

    # ── Admin Sales Overview ──

    @router.get("/referral/admin/sales-overview")
    async def admin_sales_overview(authorization: str = Header(...)):
        """Admin-only: Full overview of referral sales system.
        Shows revenue, commission, user details — everything."""
        user = await get_current_user(authorization)
        if not user.get("isAdmin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Primary: orders collection
        all_orders = await db.orders.find({}).to_list(50000)
        orders_revenue = sum(o.get("amount", 0) for o in all_orders)
        orders_commission = sum(o.get("commission", 0) for o in all_orders)
        orders_pending_commission = sum(o.get("commission", 0) for o in all_orders if o.get("status") == "paid")
        orders_paid_out = sum(o.get("commission", 0) for o in all_orders if o.get("status") == "paid_out")

        # Legacy: referral_commissions
        all_legacy = await db.referral_commissions.find({}).to_list(50000)
        legacy_revenue = sum(c.get("orderAmount", 0) for c in all_legacy)
        legacy_commission = sum(c.get("commission", 0) for c in all_legacy)

        total_revenue = round(orders_revenue + legacy_revenue, 2)
        total_commission = round(orders_commission + legacy_commission, 2)

        # Per-partner breakdown (from orders)
        partner_map: dict = {}
        for o in all_orders:
            code = o.get("referredBy", "")
            if code not in partner_map:
                partner_map[code] = {"code": code, "revenue": 0, "commission": 0, "sales": 0}
            partner_map[code]["revenue"] += o.get("amount", 0)
            partner_map[code]["commission"] += o.get("commission", 0)
            partner_map[code]["sales"] += 1

        # Merge legacy data into partner_map
        for c in all_legacy:
            code = c.get("referredBy", "")
            if code not in partner_map:
                partner_map[code] = {"code": code, "revenue": 0, "commission": 0, "sales": 0}
            partner_map[code]["revenue"] += c.get("orderAmount", 0)
            partner_map[code]["commission"] += c.get("commission", 0)
            partner_map[code]["sales"] += 1

        # Enrich with partner names
        partners = []
        for code, pdata in partner_map.items():
            partner_user = await db.users.find_one(
                {"referralCode": code},
                {"profile": 1, "email": 1, "referralCount": 1, "referralSuccessCount": 1}
            )
            name = ""
            if partner_user:
                name = partner_user.get("profile", {}).get("businessName", "") or partner_user.get("email", "")
            partners.append({
                **pdata,
                "name": name,
                "totalReferred": partner_user.get("referralCount", 0) if partner_user else 0,
                "successfulReferred": partner_user.get("referralSuccessCount", 0) if partner_user else 0,
                "revenue": round(pdata["revenue"], 2),
                "commission": round(pdata["commission"], 2),
            })
        partners.sort(key=lambda x: x["revenue"], reverse=True)

        # Global totals
        total_referral_users = await db.users.count_documents({"referredBy": {"$exists": True, "$ne": ""}})
        total_paid_users_orders = await db.orders.count_documents({})

        return {
            "totalReferredUsers": total_referral_users,
            "paidUsers": total_paid_users_orders,
            "totalRevenue": total_revenue,
            "totalCommission": total_commission,
            "pendingCommission": round(orders_pending_commission, 2),
            "paidOutCommission": round(orders_paid_out, 2),
            "partners": partners,
        }

    # ── Admin Plan Config CRUD ──

    @router.get("/referral/admin/plan-config")
    async def get_plan_config(authorization: str = Header(...)):
        """Admin: get all plan pricing configs."""
        user = await get_current_user(authorization)
        if not user.get("isAdmin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        configs = await db.plan_config.find({}, {"_id": 0}).to_list(20)
        if not configs:
            # Return defaults if nothing seeded yet
            return {"plans": [
                {"plan": k, **v} for k, v in DEFAULT_PLAN_CONFIG.items()
            ]}
        return {"plans": configs}

    @router.put("/referral/admin/plan-config/{plan_name}")
    async def update_plan_config(plan_name: str, data: PlanConfigUpdate, authorization: str = Header(...)):
        """Admin: update price and commission for a plan."""
        user = await get_current_user(authorization)
        if not user.get("isAdmin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        if plan_name not in PAID_PLANS:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {plan_name}. Must be one of: {', '.join(PAID_PLANS)}")

        now = datetime.now(timezone.utc)
        await db.plan_config.update_one(
            {"plan": plan_name},
            {"$set": {
                "price": data.price,
                "commissionPercent": data.commissionPercent,
                "updatedAt": now,
            }},
            upsert=True,
        )

        logger.info(f"[PLAN_CONFIG] Admin updated {plan_name}: price={data.price}, commission={data.commissionPercent}%")
        return {
            "message": f"Plan config for '{plan_name}' updated",
            "plan": plan_name,
            "price": data.price,
            "commissionPercent": data.commissionPercent,
        }

    return router
