"""
REFERRAL SYSTEM ROUTER
======================
Dual system:
1. Referral rewards → for engagement (existing tiers, activation-based)
2. Sales tracking → for monetization (commission on paid invoices)

Endpoints:
- GET  /referral/my-link           → Get/generate referral code & link
- GET  /referral/stats             → Get referral stats for dashboard
- GET  /referral/sales-stats       → Get sales tracking metrics (paid customers, earnings)
- POST /referral/track-signup      → Link a new user to their referrer
- POST /referral/check-activation  → Check if referred user completed activation criteria
- GET  /referral/admin/sales-overview → Admin: full revenue, commission, user details
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
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


class TrackSignupRequest(BaseModel):
    referralCode: str = Field(..., min_length=3, max_length=20)


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
    # SALES TRACKING SYSTEM (New — runs parallel to referral rewards)
    # ══════════════════════════════════════════════════════

    async def record_referral_commission(invoice_doc: dict, seller_id: str):
        """Called when an invoice becomes fully paid. Records commission if seller was referred.
        This is the ONLY place commission is calculated and stored — never dynamically."""
        try:
            seller = await db.users.find_one({"_id": ObjectId(seller_id)}, {"referredBy": 1})
            if not seller or not seller.get("referredBy"):
                return  # Not a referred user

            ref_code = seller["referredBy"]
            invoice_id = invoice_doc.get("_id")
            total = invoice_doc.get("total", 0)
            if total <= 0:
                return  # Skip zero-amount invoices

            # Check duplicate — don't record commission twice for same invoice
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
                "status": "pending",  # pending | paid_out
                "createdAt": datetime.now(timezone.utc),
            })
            logger.info(f"Referral commission recorded: invoice={invoice_id}, seller={seller_id}, refCode={ref_code}, amount={total}, commission={commission}")
        except Exception as e:
            logger.warning(f"Failed to record referral commission: {e}")

    # Expose for invoice_router to call
    router.record_referral_commission = record_referral_commission

    @router.get("/referral/sales-stats")
    async def get_sales_stats(authorization: str = Header(...)):
        """Get sales tracking metrics for the referral agent (user view).
        Shows: paid customers count, total earnings, pending earnings.
        Does NOT show total revenue (admin only)."""
        user = await get_current_user(authorization)
        ref_code = user.get("referralCode")
        if not ref_code:
            return {
                "paidCustomers": 0,
                "totalEarnings": 0,
                "pendingEarnings": 0,
                "paidOutEarnings": 0,
                "commissionRate": DEFAULT_COMMISSION_RATE,
            }

        # Paid customers: referred users who have at least 1 paid invoice
        referred_users = await db.users.find(
            {"referredBy": ref_code},
            {"_id": 1}
        ).to_list(1000)
        referred_ids = [u["_id"] for u in referred_users]

        paid_customer_count = 0
        if referred_ids:
            # Count sellers with at least 1 fully paid invoice
            pipeline = [
                {"$match": {"sellerId": {"$in": referred_ids}, "status": "paid", "total": {"$gt": 0}}},
                {"$group": {"_id": "$sellerId"}},
                {"$count": "total"}
            ]
            result = await db.invoices.aggregate(pipeline).to_list(1)
            paid_customer_count = result[0]["total"] if result else 0

        # Earnings from referral_commissions
        commissions = await db.referral_commissions.find(
            {"referredBy": ref_code}
        ).to_list(10000)

        total_earnings = sum(c.get("commission", 0) for c in commissions)
        pending_earnings = sum(c.get("commission", 0) for c in commissions if c.get("status") == "pending")
        paid_out_earnings = sum(c.get("commission", 0) for c in commissions if c.get("status") == "paid_out")

        return {
            "paidCustomers": paid_customer_count,
            "totalEarnings": round(total_earnings, 2),
            "pendingEarnings": round(pending_earnings, 2),
            "paidOutEarnings": round(paid_out_earnings, 2),
            "commissionRate": DEFAULT_COMMISSION_RATE,
        }

    @router.get("/referral/admin/sales-overview")
    async def admin_sales_overview(authorization: str = Header(...)):
        """Admin-only: Full overview of referral sales system.
        Shows revenue, commission, user details — everything."""
        user = await get_current_user(authorization)
        if not user.get("isAdmin"):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Total referral commissions
        all_commissions = await db.referral_commissions.find({}).to_list(50000)
        total_revenue = sum(c.get("orderAmount", 0) for c in all_commissions)
        total_commission = sum(c.get("commission", 0) for c in all_commissions)
        pending_commission = sum(c.get("commission", 0) for c in all_commissions if c.get("status") == "pending")

        # Per-partner breakdown
        partner_map: dict = {}
        for c in all_commissions:
            code = c.get("referredBy", "")
            if code not in partner_map:
                partner_map[code] = {"code": code, "revenue": 0, "commission": 0, "sales": 0}
            partner_map[code]["revenue"] += c.get("orderAmount", 0)
            partner_map[code]["commission"] += c.get("commission", 0)
            partner_map[code]["sales"] += 1

        # Enrich with partner names
        partners = []
        for code, data in partner_map.items():
            partner_user = await db.users.find_one({"referralCode": code}, {"profile": 1, "email": 1, "referralCount": 1, "referralSuccessCount": 1})
            name = ""
            if partner_user:
                name = partner_user.get("profile", {}).get("businessName", "") or partner_user.get("email", "")
            partners.append({
                **data,
                "name": name,
                "totalReferred": partner_user.get("referralCount", 0) if partner_user else 0,
                "successfulReferred": partner_user.get("referralSuccessCount", 0) if partner_user else 0,
                "revenue": round(data["revenue"], 2),
                "commission": round(data["commission"], 2),
            })
        partners.sort(key=lambda x: x["revenue"], reverse=True)

        # Global totals
        total_referral_users = await db.users.count_documents({"referredBy": {"$exists": True, "$ne": ""}})
        # Paid users among referred
        pipeline = [
            {"$match": {"referredBy": {"$exists": True, "$ne": ""}}},
            {"$lookup": {"from": "invoices", "localField": "_id", "foreignField": "sellerId", "as": "invoices"}},
            {"$match": {"invoices": {"$elemMatch": {"status": "paid", "total": {"$gt": 0}}}}},
            {"$count": "total"}
        ]
        paid_result = await db.users.aggregate(pipeline).to_list(1)
        paid_users = paid_result[0]["total"] if paid_result else 0

        return {
            "totalReferredUsers": total_referral_users,
            "paidUsers": paid_users,
            "totalRevenue": round(total_revenue, 2),
            "totalCommission": round(total_commission, 2),
            "pendingCommission": round(pending_commission, 2),
            "commissionRate": DEFAULT_COMMISSION_RATE,
            "partners": partners,
        }

    return router
