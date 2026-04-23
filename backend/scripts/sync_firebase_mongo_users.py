"""
Firebase <-> MongoDB User Sync Script
======================================

Idempotent migration that reconciles MongoDB users with Firebase Auth and
normalises role / seller / verification fields.

Safe to run multiple times. Reports a summary of changes.

Usage:
    # Dry-run (no writes)
    python -m backend.scripts.sync_firebase_mongo_users --dry-run

    # Live run
    python -m backend.scripts.sync_firebase_mongo_users

Specification:
1. Fetch all users from MongoDB.
2. For each user:
   * Get Firebase Auth user using firebaseUid.
   * Sync: email, isEmailVerified, name (if DB missing).
3. Fix roles:
   * If user has businessName OR has created listings -> add role "seller"
   * Else keep existing roles (default "buyer").
4. Fix seller fields:
   * If role includes "seller": isSeller=true, sellerSlug=slugify(businessName).
   * Else: isSeller=false.
5. Verified badge ONLY depends on gst.verified === true. Do NOT use emailVerified.
6. Normalize status: single "status": "active". Remove duplicate flags where safe.
7. Save updated user back to MongoDB.
8. No null sellerSlug for sellers (fallback to slugify(name) if businessName missing).

Safety:
- Does NOT overwrite valid GST data.
- Does NOT remove existing roles, only adds missing ones.
- Idempotent - second run results in zero changes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the /app/backend package is importable when run via `python path/to/script.py`
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import firebase_admin  # type: ignore
from firebase_admin import credentials, auth as firebase_auth  # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("sync_users")


def slugify(text: Optional[str]) -> str:
    """URL-safe slug matching frontend convention (lowercase kebab-case)."""
    if not text:
        return ""
    s = str(text).lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def _get_business_name(user: Dict[str, Any]) -> Optional[str]:
    """Read the business / company name from any of the known locations."""
    profile = user.get("profile") or {}
    for candidate in (
        user.get("businessName"),
        user.get("companyName"),
        profile.get("businessName"),
        profile.get("companyName"),
    ):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return None


def _init_firebase() -> None:
    """Initialise Firebase Admin SDK once using GOOGLE_APPLICATION_CREDENTIALS or inline creds."""
    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get(
        "FIREBASE_CREDENTIALS_PATH"
    )
    if cred_path and Path(cred_path).exists():
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase initialised via credentials file: %s", cred_path)
        return

    # Fallback: ADC / no-op when running against emulator
    try:
        firebase_admin.initialize_app()
        logger.info("Firebase initialised via Application Default Credentials")
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "Firebase could not be initialised (%s). Firebase fields will not be synced.",
            exc,
        )


async def sync_users(dry_run: bool = False) -> Dict[str, Any]:
    """Run the sync. Returns a summary dict."""
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    _init_firebase()
    firebase_available = bool(firebase_admin._apps)

    summary: Dict[str, Any] = {
        "totalUsers": 0,
        "usersUpdated": 0,
        "firebaseSynced": 0,
        "firebaseMissing": 0,
        "sellerRoleAdded": 0,
        "sellerSlugBackfilled": 0,
        "statusNormalised": 0,
        "verificationNormalised": 0,
        "errors": [],
        "dryRun": dry_run,
    }

    # Cache of sellerIds that have at least one sellerListing (to decide seller role).
    sellers_with_listings: set = set()
    async for listing in db.sellerListings.find({}, {"sellerId": 1}):
        sid = listing.get("sellerId")
        if sid:
            sellers_with_listings.add(str(sid))

    logger.info("Found %d distinct sellerIds with listings", len(sellers_with_listings))

    cursor = db.users.find({})
    async for user in cursor:
        summary["totalUsers"] += 1
        user_id = user["_id"]
        updates: Dict[str, Any] = {}
        unsets: Dict[str, str] = {}

        # ---- 2. Sync from Firebase ----
        firebase_uid = user.get("firebaseUid")
        if firebase_available and firebase_uid:
            try:
                fb_user = firebase_auth.get_user(firebase_uid)
                summary["firebaseSynced"] += 1

                if fb_user.email and user.get("email") != fb_user.email:
                    updates["email"] = fb_user.email
                if user.get("isEmailVerified") != bool(fb_user.email_verified):
                    updates["isEmailVerified"] = bool(fb_user.email_verified)
                if fb_user.display_name and not user.get("name"):
                    updates["name"] = fb_user.display_name
            except firebase_auth.UserNotFoundError:
                summary["firebaseMissing"] += 1
            except Exception as exc:  # noqa: BLE001
                summary["errors"].append(
                    {"userId": str(user_id), "stage": "firebase", "error": str(exc)}
                )

        # ---- 3. Roles ----
        existing_roles: List[str] = list(user.get("roles") or [])
        # Accept string role for legacy docs
        if isinstance(user.get("roles"), str):
            existing_roles = [user["roles"]]

        business_name = _get_business_name(user)
        has_listings = str(user_id) in sellers_with_listings

        roles_changed = False
        if (business_name or has_listings) and "seller" not in existing_roles:
            existing_roles.append("seller")
            roles_changed = True
            summary["sellerRoleAdded"] += 1

        if not existing_roles:
            existing_roles = ["buyer"]
            roles_changed = True

        if roles_changed:
            updates["roles"] = existing_roles

        is_seller = "seller" in existing_roles

        # ---- 4. Seller fields ----
        current_is_seller = bool(user.get("isSeller"))
        if current_is_seller != is_seller:
            updates["isSeller"] = is_seller

        if is_seller:
            current_slug = (user.get("sellerSlug") or "").strip()
            if not current_slug:
                # Derive slug: businessName first, fall back to name/email prefix.
                source = (
                    business_name
                    or user.get("name")
                    or (user.get("email") or "").split("@")[0]
                )
                new_slug = slugify(source)
                if new_slug:
                    updates["sellerSlug"] = new_slug
                    summary["sellerSlugBackfilled"] += 1

        # ---- 5. Verified badge — gst.verified only ----
        gst = user.get("gst") or {}
        gst_verified = bool(gst.get("verified") is True)
        if user.get("isVerified") != gst_verified:
            updates["isVerified"] = gst_verified
            summary["verificationNormalised"] += 1

        # ---- 6. Normalise status ----
        legacy_account_status = user.get("accountStatus")
        legacy_is_active = user.get("isActive")
        current_status = user.get("status")

        # Determine target status (active unless explicitly suspended/deleted).
        if current_status:
            target_status = current_status
        elif legacy_account_status in ("suspended", "deleted", "pending"):
            target_status = legacy_account_status
        elif legacy_is_active is False:
            target_status = "inactive"
        else:
            target_status = "active"

        if current_status != target_status:
            updates["status"] = target_status
            summary["statusNormalised"] += 1

        # Clean up redundant flags only if they exactly mirror status.
        if legacy_account_status and legacy_account_status == target_status:
            unsets["accountStatus"] = ""
        if legacy_is_active is not None and bool(legacy_is_active) == (target_status == "active"):
            unsets["isActive"] = ""

        # ---- 7. Persist ----
        if updates or unsets:
            summary["usersUpdated"] += 1
            mongo_update: Dict[str, Any] = {}
            if updates:
                updates["updatedAt"] = datetime.now(timezone.utc)
                mongo_update["$set"] = updates
            if unsets:
                mongo_update["$unset"] = unsets

            if dry_run:
                logger.info("[dry-run] %s -> %s", user_id, mongo_update)
            else:
                try:
                    await db.users.update_one({"_id": user_id}, mongo_update)
                except Exception as exc:  # noqa: BLE001
                    summary["errors"].append(
                        {"userId": str(user_id), "stage": "update", "error": str(exc)}
                    )

    client.close()
    return summary


def _print_summary(summary: Dict[str, Any]) -> None:
    logger.info("---- Sync summary ----")
    for key, value in summary.items():
        if key == "errors":
            continue
        logger.info("%s: %s", key, value)
    if summary["errors"]:
        logger.warning("Errors (%d):", len(summary["errors"]))
        for err in summary["errors"][:20]:
            logger.warning("  %s", err)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync users between Firebase and MongoDB")
    parser.add_argument(
        "--dry-run", action="store_true", help="Compute changes without writing to MongoDB"
    )
    args = parser.parse_args()

    # Load .env from /app/backend so MONGO_URL is available when running locally.
    env_file = _ROOT / "backend" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    if "MONGO_URL" not in os.environ or "DB_NAME" not in os.environ:
        logger.error("MONGO_URL and DB_NAME env vars are required")
        sys.exit(1)

    summary = asyncio.run(sync_users(dry_run=args.dry_run))
    _print_summary(summary)


if __name__ == "__main__":
    main()
