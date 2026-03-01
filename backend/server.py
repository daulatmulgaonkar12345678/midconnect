# =============================================================================
# SSOT: All database fields use camelCase. NEVER use snake_case in Mongo keys.
# Database Schema: firebaseUid, accountStatus, isAdmin, isActive, profile.*, gst.*
# =============================================================================

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Body, File, UploadFile, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator, model_validator, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import math
import base64
import re
import asyncio
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import time
import json
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from PIL import Image
from bson import ObjectId
from fastapi import HTTPException, Query, Depends
from datetime import datetime, timezone
import io

# Load environment variables from .env file
load_dotenv()

# Import services for clean architecture
from services.listing_service import ListingService
from services.product_identity_service import ProductIdentityService

# ================== IMAGE UPLOAD CONFIGURATION ==================

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': 'JPEG',
    'image/png': 'PNG', 
    'image/webp': 'WEBP'
}

# File size limits in bytes
IMAGE_SIZE_LIMITS = {
    'category': 1 * 1024 * 1024,  # 1 MB
    'product': 3 * 1024 * 1024,   # 3 MB input (will be compressed)
}

MAX_IMAGES_PER_PRODUCT = 5
MAX_IMAGES_PER_CATEGORY = 2

# Max dimensions for resize
MAX_IMAGE_DIMENSION = 1600  # Updated to spec
MIN_IMAGE_DIMENSION = 600   # Minimum requirement

# Compression targets
TARGET_IMAGE_SIZE_MIN = 100 * 1024   # 100 KB
TARGET_IMAGE_SIZE_MAX = 300 * 1024   # 300 KB


def validate_and_process_image(
    file_content: bytes,
    file_type: str,
    max_size: int,
    context: str = "image"
) -> tuple[bytes, str]:
    """
    Validate and sanitize an uploaded image.
    
    Security measures:
    1. Check MIME type against whitelist
    2. Verify file size
    3. Actually decode image with PIL (detects fake/malicious files)
    4. Resize if needed
    5. Re-encode to sanitized format
    
    Returns: (processed_image_bytes, format)
    Raises: HTTPException on validation failure
    """
    # 1. Check MIME type
    if file_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: {file_type}. Allowed: JPEG, PNG, WEBP"
        )
    
    # 2. Check file size
    if len(file_content) > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size: {max_mb:.1f} MB"
        )
    
    # 3. Try to open with PIL - this validates it's a real image
    try:
        img = Image.open(io.BytesIO(file_content))
        img.verify()  # Verify it's not corrupted
        
        # Re-open after verify (verify closes the file)
        img = Image.open(io.BytesIO(file_content))
    except Exception as e:
        logger.warning(f"Image validation failed for {context}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file"
        )
    
    # 4. Convert RGBA to RGB if needed (for JPEG output)
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 5. Resize if too large
    width, height = img.size
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        ratio = min(MAX_IMAGE_DIMENSION / width, MAX_IMAGE_DIMENSION / height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # 6. Re-encode as JPEG (sanitized output)
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    output.seek(0)
    
    return output.getvalue(), 'image/jpeg'


def image_to_data_url(image_bytes: bytes, mime_type: str = 'image/jpeg') -> str:
    """Convert image bytes to base64 data URL for storage"""
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{b64}"


def compress_image_to_target(
    img: Image.Image,
    target_min: int = TARGET_IMAGE_SIZE_MIN,
    target_max: int = TARGET_IMAGE_SIZE_MAX,
    output_format: str = 'WEBP'
) -> tuple[bytes, str]:
    """
    Compress image to target size range with optimal quality.
    
    Strategy:
    1. Start at high quality (90)
    2. Gradually reduce quality until target size reached
    3. Never over-compress (min quality = 40)
    4. Reject if cannot reach target without severe degradation
    
    Returns: (compressed_bytes, mime_type)
    Raises: HTTPException if compression impossible
    """
    # Strip EXIF metadata for security (GPS, device info)
    # Create new image without EXIF
    data = list(img.getdata())
    img_no_exif = Image.new(img.mode, img.size)
    img_no_exif.putdata(data)
    img = img_no_exif
    
    # Try compression at decreasing quality levels
    quality_levels = [90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40]
    
    for quality in quality_levels:
        output = io.BytesIO()
        
        if output_format == 'WEBP':
            img.save(output, format='WEBP', quality=quality, method=4)
            mime = 'image/webp'
        else:
            img.save(output, format='JPEG', quality=quality, optimize=True)
            mime = 'image/jpeg'
        
        size = output.tell()
        
        # Check if within target range
        if size <= target_max:
            output.seek(0)
            logger.info(f"Image compressed: quality={quality}, size={size/1024:.1f}KB")
            return output.getvalue(), mime
    
    # If we get here, even lowest quality is too large
    # This shouldn't happen with proper resizing, but handle it
    raise HTTPException(
        status_code=400,
        detail="Image cannot be compressed to acceptable quality. Please use a smaller image."
    )


def validate_and_process_product_image(
    file_content: bytes,
    file_type: str
) -> tuple[bytes, str]:
    """
    Full pipeline for product image upload:
    1. Validate MIME type & file header
    2. Verify image integrity
    3. Check minimum dimensions
    4. Resize to max dimensions
    5. Strip EXIF metadata
    6. Compress to target size (WEBP)
    
    Returns: (processed_bytes, mime_type)
    Raises: HTTPException on validation failure
    """
    max_size = IMAGE_SIZE_LIMITS['product']
    
    # 1. Check MIME type
    if file_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: {file_type}. Allowed: JPEG, PNG, WEBP"
        )
    
    # 2. Check file size (input limit)
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum upload size: {max_size / (1024*1024):.0f} MB"
        )
    
    # 3. Validate image integrity with PIL
    try:
        img = Image.open(io.BytesIO(file_content))
        img.verify()
        img = Image.open(io.BytesIO(file_content))  # Re-open after verify
    except Exception as e:
        logger.warning(f"Product image validation failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file"
        )
    
    # 4. Check minimum dimensions
    width, height = img.size
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise HTTPException(
            status_code=400,
            detail=f"Image too small. Minimum dimensions: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION} pixels"
        )
    
    # 5. Convert to RGB if needed
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 6. Resize if too large (maintain aspect ratio)
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        ratio = min(MAX_IMAGE_DIMENSION / width, MAX_IMAGE_DIMENSION / height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.info(f"Image resized from {width}x{height} to {new_size[0]}x{new_size[1]}")
    
    # 7. Compress to target size
    compressed_bytes, mime_type = compress_image_to_target(img)
    
    return compressed_bytes, mime_type

# ================== STRUCTURED LOGGING ==================

class StructuredLogger:
    """JSON-structured logging for observability"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Add console handler with JSON format
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
    
    def _log(self, level: str, event: str, **kwargs):
        """Log structured JSON message"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **kwargs
        }
        
        # Add request context if available
        try:
            ctx = request_context.get()
            if ctx:
                log_entry["request_id"] = ctx.request_id
                if ctx.user_id:
                    log_entry["user_id"] = ctx.user_id
        except LookupError:
            pass
        
        if level == "ERROR":
            self.logger.error(json.dumps(log_entry))
        elif level == "WARNING":
            self.logger.warning(json.dumps(log_entry))
        elif level == "DEBUG":
            self.logger.debug(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))
    
    def info(self, event: str, **kwargs):
        self._log("INFO", event, **kwargs)
    
    def error(self, event: str, **kwargs):
        self._log("ERROR", event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        self._log("WARNING", event, **kwargs)
    
    def debug(self, event: str, **kwargs):
        self._log("DEBUG", event, **kwargs)

# Basic logging for startup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("server")
structured_logger = StructuredLogger("api")

# ================== ENV & LOGGING ==================


# port = os.getenv("PORT", "10000")
# logger.info(f"🚀 Starting server on port {port}")
# ================== REQUEST CONTEXT ==================

@dataclass
class RequestContext:
    """Context for the current request"""
    request_id: str
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    start_time: float = field(default_factory=time.time)

# Context variable for request-scoped data
request_context: ContextVar[Optional[RequestContext]] = ContextVar('request_context', default=None)

def get_request_id() -> Optional[str]:
    """Get current request ID from context"""
    ctx = request_context.get()
    return ctx.request_id if ctx else None

def set_user_id(user_id: str):
    """Set user ID in current request context"""
    ctx = request_context.get()
    if ctx:
        ctx.user_id = user_id

# ================== METRICS TRACKING ==================

@dataclass
class MetricsCollector:
    """Simple metrics collector for observability"""
    
    # Request counts by endpoint and status
    request_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_sums: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    
    # Auth metrics
    auth_failures: int = 0
    auth_successes: int = 0
    
    # Rate limit metrics
    rate_limit_hits: int = 0
    
    # Database metrics
    db_errors: int = 0
    
    def record_request(self, endpoint: str, status_code: int, latency_ms: float):
        """Record a completed request"""
        key = f"{endpoint}:{status_code // 100}xx"
        self.request_counts[key] += 1
        self.latency_sums[endpoint] = self.latency_sums.get(endpoint, 0) + latency_ms
        
        if status_code >= 400:
            error_key = f"{status_code}"
            self.error_counts[error_key] += 1
    
    def record_auth_failure(self, reason: str):
        """Record an authentication failure"""
        self.auth_failures += 1
        structured_logger.warning("auth_failure", reason=reason)
    
    def record_auth_success(self, user_id: str):
        """Record a successful authentication"""
        self.auth_successes += 1
    
    def record_rate_limit(self, endpoint: str, ip: str):
        """Record a rate limit hit"""
        self.rate_limit_hits += 1
        structured_logger.warning("rate_limit_exceeded", endpoint=endpoint, ip=ip)
    
    def record_db_error(self, operation: str, error: str):
        """Record a database error"""
        self.db_errors += 1
        structured_logger.error("db_error", operation=operation, error=error)
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        return {
            "requests": dict(self.request_counts),
            "errors_by_status": dict(self.error_counts),
            "auth": {
                "successes": self.auth_successes,
                "failures": self.auth_failures
            },
            "rate_limit_hits": self.rate_limit_hits,
            "db_errors": self.db_errors
        }

# Global metrics collector
metrics = MetricsCollector()

# ================== FIREBASE INIT (ENV SAFE) ==================

firebase_initialized = False
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if firebase_json:
    try:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        logger.info("✅ Firebase Admin initialized via env")
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {e}")
else:
    logger.warning("⚠️ Firebase not configured — auth disabled")
_raw_mongo_url = os.getenv("MONGO_URL")
MONGO_URL = _raw_mongo_url.strip() if _raw_mongo_url else None


# Also sanitize DB_NAME just in case
_raw_db_name = os.getenv("DB_NAME", "b2b_marketplace")  # Default to b2b_marketplace
DB_NAME = _raw_db_name.strip()

db = None
mongo_connected = False

if not MONGO_URL:
    logger.error("❌ MONGO_URL environment variable is missing")
else:
    # Log sanitization for debugging (without exposing the actual URL)
    if _raw_mongo_url != MONGO_URL:
        logger.warning("⚠️ MONGO_URL had trailing/leading whitespace - sanitized")
    
    # Log the database name being used
    logger.info(f"📊 Connecting to database: {DB_NAME}")
    
    try:
        client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000
        )
        db = client[DB_NAME]
        mongo_connected = True
        logger.info(f"✅ MongoDB client initialized - Database: {DB_NAME}")
    except Exception as e:
        logger.error(f"❌ MongoDB init failed: {e}")

# ================== RATE LIMITER ==================

limiter = Limiter(key_func=get_remote_address)

# ==================== ENUMS & VALIDATORS ==================

class AccountStatus(str, Enum):
    """Valid account statuses"""
    ACTIVE = "active"
    DELETED = "deleted"
    ARCHIVED = "archived"

class SubscriptionPlan(str, Enum):
    """Valid subscription plans - Single Source of Truth"""
    FREE = "free"
    TRIAL = "trial"
    PRO = "pro"

# ================== SUBSCRIPTION SYSTEM UTILITIES ==================
# 
# SINGLE SOURCE OF TRUTH: 
# - Subscription status is stored in users.subscription object
# - inquiries_used is NEVER stored - always calculated from inquiries collection
# - This prevents data corruption and ensures accurate counts
#

# Subscription plan configurations
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "inquiryLimit": 5,  # per month
        "canExpire": False,
    },
    "trial": {
        "name": "Trial",
        "inquiryLimit": -1,  # unlimited
        "durationDays": 90,
        "canExpire": True,
    },
    "pro": {
        "name": "Pro",
        "inquiryLimit": -1,  # unlimited
        "priceQuarterly": 999,  # INR
        "canExpire": True,
    }
}

def make_timezone_aware(dt) -> datetime:
    """
    Convert offset-naive datetime to timezone-aware (UTC).
    MongoDB stores datetimes without timezone info, so we need this for comparisons.
    
    Args:
        dt: datetime object (naive or aware) or ISO string
        
    Returns:
        Timezone-aware datetime in UTC, or None if conversion fails
    """
    if dt is None:
        return None
    
    # Handle string dates
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return None
    
    # If already timezone-aware, return as-is
    if dt.tzinfo is not None:
        return dt
    
    # Make timezone-aware by assuming UTC
    return dt.replace(tzinfo=timezone.utc)

def get_subscription_status(subscription: dict) -> str:
    """
    Calculate subscription status from user's subscription object.
    
    Logic:
    - If plan is 'trial' or 'pro' AND today <= end_date: return 'unlimited'
    - If plan is 'free': return 'limited'
    - Otherwise: return 'expired'
    
    NEVER store or retrieve inquiries_used - calculate dynamically.
    """
    if not subscription:
        return "limited"  # Default to free tier
    
    plan = subscription.get("plan", "free")
    end_date = subscription.get("endDate")
    active = subscription.get("active", False)
    
    # Free plan - always limited
    if plan == "free":
        return "limited"
    
    # Trial or Pro - check if still valid
    if plan in ["trial", "pro"]:
        if not end_date:
            return "expired"
        
        # Use helper to convert to timezone-aware datetime
        end_date = make_timezone_aware(end_date)
        if end_date is None:
            return "expired"
        
        if end_date > datetime.now(timezone.utc):
            return "unlimited"
        else:
            return "expired"
    
    return "limited"

async def count_accepted_inquiries_this_month(db, seller_id: str) -> int:
    """
    Count accepted inquiries for a seller in the current month.
    
    This is the SINGLE SOURCE OF TRUTH for inquiry usage.
    NEVER store this count - always calculate it.
    
    SSOT POLICY: seller_id in inquiries is ObjectId.
    """
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1)
    
    # SSOT: Convert seller_id to ObjectId for query
    seller_oid = ObjectId(seller_id) if isinstance(seller_id, str) else seller_id
    
    count = await db.inquiries.count_documents({
        "sellerId": seller_oid,
        "status": "accepted",
        "acceptedAt": {"$gte": month_start}
    })
    
    return count

def check_can_accept_inquiry(subscription: dict, accepted_count: int) -> dict:
    """
    Check if seller can accept an inquiry based on subscription.
    
    Returns:
        {
            "canAccept": bool,
            "reason": str (if cannot accept),
            "limit": int (-1 for unlimited),
            "used": int
        }
    """
    status = get_subscription_status(subscription)
    plan = subscription.get("plan", "free") if subscription else "free"
    limit = SUBSCRIPTION_PLANS.get(plan, {}).get("inquiryLimit", 5)
    
    if status == "unlimited":
        return {
            "canAccept": True,
            "reason": None,
            "limit": -1,
            "used": accepted_count
        }
    
    if status == "expired":
        return {
            "canAccept": False,
            "reason": "subscriptionExpired",
            "limit": 0,
            "used": accepted_count,
            "message": "Your subscription has expired. Please renew to accept inquiries."
        }
    
    # Limited (free tier)
    if accepted_count >= limit:
        return {
            "canAccept": False,
            "reason": "limitReached",
            "limit": limit,
            "used": accepted_count,
            "message": f"You've reached your monthly limit of {limit} inquiry acceptances. Upgrade to Pro for unlimited access."
        }
    
    return {
        "canAccept": True,
        "reason": None,
        "limit": limit,
        "used": accepted_count
    }

class SellerRole(str, Enum):
    """Valid seller roles"""
    MANUFACTURER = "Manufacturer"
    DEALER = "Dealer"
    DISTRIBUTOR = "Distributor"
    TRADER = "Trader"

class GSTStatus(str, Enum):
    """Valid GST verification statuses"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class CapacityTimeBasis(str, Enum):
    """Valid time basis for capacity"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

class SpecFieldType(str, Enum):
    """Valid specification field types"""
    DROPDOWN = "dropdown"
    NUMBER = "number"
    TEXT = "text"
    RANGE = "range"

# Pagination limits
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

# ================== REQUEST SANITIZATION HELPERS ==================

# Fields that must NEVER be accepted from frontend
SYSTEM_FIELDS = frozenset([
    '_id', 'id',
    'createdAt', 'created_at',
    'updatedAt', 'updated_at', 
    'createdBy', 'created_by',
    'userId', 'user_id',  # Must come from auth token
    'sellerId', 'seller_id',  # Must come from auth token for seller actions
    'adminId', 'admin_id',  # Must come from auth token
    'buyerId', 'buyer_id',  # Must come from auth token
])

# Fields that only admins can modify
ADMIN_ONLY_FIELDS = frozenset([
    'roles', 'isAdmin', 'is_admin',
    'subscription', 'canLogin', 'can_login',
    'accountStatus', 'accountStatus',
    'isActive', 'isActive'  # For users collection
])

def sanitize_request_body(data: dict, allowed_fields: set = None, is_admin: bool = False) -> dict:
    """
    Remove system-generated fields from request body.
    
    Args:
        data: Request body dictionary
        allowed_fields: Optional set of explicitly allowed fields
        is_admin: If True, allow admin-only fields
    
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    
    for key, value in data.items():
        # Always remove system fields
        if key in SYSTEM_FIELDS:
            continue
        
        # Remove admin-only fields for non-admins
        if not is_admin and key in ADMIN_ONLY_FIELDS:
            continue
        
        # If allowed_fields specified, only include those
        if allowed_fields and key not in allowed_fields:
            continue
        
        # Recursively sanitize nested dicts
        if isinstance(value, dict):
            sanitized[key] = sanitize_request_body(value, is_admin=is_admin)
        else:
            sanitized[key] = value
    
    return sanitized

def generate_system_fields(user_id: ObjectId = None) -> dict:
    """
    Generate system fields for document creation.
    
    Args:
        user_id: ObjectId of the user creating the document
    
    Returns:
        Dictionary with system fields
    """
    now = datetime.now(timezone.utc)
    fields = {
        'createdAt': now,
        'updatedAt': now
    }
    if user_id:
        fields['createdBy'] = user_id
    return fields

def generate_update_fields() -> dict:
    """
    Generate fields for document updates.
    
    Returns:
        Dictionary with updatedAt timestamp
    """
    return {
        'updatedAt': datetime.now(timezone.utc)
    }

def safe_object_id(value: str, field_name: str = "id") -> ObjectId:
    """
    Safely convert string to ObjectId with proper error handling.
    
    Args:
        value: String value to convert
        field_name: Name of the field (for error messages)
    
    Returns:
        ObjectId
    
    Raises:
        HTTPException with 400 status if invalid
    """
    if isinstance(value, ObjectId):
        return value
    
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format: must be a valid ObjectId"
        )

def safe_int(value, field_name: str = "value", default: int = None) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        field_name: Name of the field (for error messages)
        default: Default value if conversion fails (None raises error)
    
    Returns:
        Integer value
    
    Raises:
        HTTPException with 400 status if invalid and no default
    """
    if value is None:
        if default is not None:
            return default
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required"
        )
    
    try:
        return int(value)
    except (ValueError, TypeError):
        if default is not None:
            return default
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: must be an integer"
        )

def safe_bool(value, default: bool = False) -> bool:
    """
    Safely convert value to boolean.
    
    Args:
        value: Value to convert
        default: Default value if None
    
    Returns:
        Boolean value
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes')
    return bool(value)

# ================== STANDARDIZED ERROR RESPONSES ==================

class APIError:
    """Standardized API error factory"""
    
    @staticmethod
    def validation_error(field: str, message: str, code: str = "VALIDATION_ERROR"):
        """Return consistent validation error"""
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": code,
                "field": field,
                "message": message
            }
        )
    
    @staticmethod
    def not_found(resource: str, resource_id: str = None):
        """Return consistent not found error"""
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with ID '{resource_id}' not found"
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "NOT_FOUND",
                "resource": resource,
                "message": detail
            }
        )
    
    @staticmethod
    def conflict(message: str, field: str = None):
        """Return consistent conflict error (duplicate, etc.)"""
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "CONFLICT",
                "field": field,
                "message": message
            }
        )
    
    @staticmethod
    def transaction_failed(operation: str, details: str = None):
        """Return consistent transaction failure error"""
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "TRANSACTION_FAILED",
                "operation": operation,
                "message": f"Transaction failed during {operation}. Changes have been rolled back.",
                "details": details
            }
        )

# ================== MONGODB SERIALIZATION UTILITIES ==================

from bson import ObjectId
from datetime import datetime


def serialize_mongo_doc(data):
    """
    Fully safe MongoDB serializer.
    Handles:
    - dict
    - list
    - nested dict
    - nested list
    - ObjectId
    - datetime
    """

    if data is None:
        return None

    if isinstance(data, ObjectId):
        return str(data)

    if isinstance(data, datetime):
        return data.isoformat()

    if isinstance(data, list):
        return [serialize_mongo_doc(item) for item in data]

    if isinstance(data, dict):
        return {key: serialize_mongo_doc(value) for key, value in data.items()}

    return data


def success_response(data: dict) -> dict:
    """
    ENTERPRISE STANDARD: Wrap all responses with serialization.
    Use this for EVERY endpoint return to prevent ObjectId serialization crashes.
    
    Example:
        return success_response({"listing": listing, "product": product})
    """
    return serialize_mongo_doc(data)


# ================== QUERY VALIDATION HELPERS ==================

def validate_object_id(id_str: str, field_name: str = "id") -> ObjectId:
    """Validate and convert string to ObjectId"""
    if not id_str:
        APIError.validation_error(field_name, f"{field_name} is required")
    try:
        return ObjectId(id_str)
    except Exception:
        APIError.validation_error(field_name, f"Invalid {field_name} format. Expected 24-character hex string.")

def validate_pagination(skip: int, limit: int) -> tuple:
    """Validate and sanitize pagination parameters"""
    if skip < 0:
        skip = 0
    if limit < 1:
        limit = DEFAULT_PAGE_SIZE
    if limit > MAX_PAGE_SIZE:
        limit = MAX_PAGE_SIZE
    return skip, limit

def sanitize_sort_field(field: str, allowed_fields: List[str]) -> str:
    """Validate sort field against allowed list to prevent injection"""
    if not field:
        return allowed_fields[0] if allowed_fields else "_id"
    if field.lstrip("-") not in allowed_fields:
        return allowed_fields[0] if allowed_fields else "_id"
    return field

def sanitize_search_query(query: str, max_length: int = 200) -> str:
    """Sanitize search query to prevent regex injection"""
    if not query:
        return ""
    # Remove regex special characters that could cause ReDoS
    sanitized = re.sub(r'[.*+?^${}()|[\]\\]', '', query)
    return sanitized[:max_length].strip()

# ================== TRANSACTION HELPERS ==================

async def execute_with_transaction(operations: list, operation_name: str):
    """
    Execute multiple database operations in a transaction.
    Rolls back all changes if any operation fails.
    
    Note: MongoDB transactions require a replica set.
    For standalone MongoDB, we use best-effort ordering with manual rollback.
    """
    # Check if we're using a replica set (transactions require replica set)
    try:
        # Try to start a session (works with replica set)
        async with await client.start_session() as session:
            async with session.start_transaction():
                results = []
                for op_func in operations:
                    result = await op_func(session)
                    results.append(result)
                return results
    except Exception as e:
        # Fallback for standalone MongoDB - execute sequentially
        # Log warning that transactions aren't available
        logger.warning(f"Transaction not available (standalone MongoDB): {e}. Using sequential execution.")
        
        completed_ops = []
        try:
            for i, op_func in enumerate(operations):
                result = await op_func(None)
                completed_ops.append((i, result))
            return [r for _, r in completed_ops]
        except Exception as inner_e:
            # Log the failure
            logger.error(f"Operation {operation_name} failed at step {len(completed_ops)}: {inner_e}")
            # For critical operations, we should have compensating transactions
            # This is logged for manual intervention if needed
            raise HTTPException(
                status_code=500,
                detail={
                    "error_code": "OPERATION_FAILED",
                    "operation": operation_name,
                    "completedSteps": len(completed_ops),
                    "message": f"Operation failed. {len(completed_ops)} steps completed before failure.",
                    "requiresReview": len(completed_ops) > 0
                }
            )

# ================== FASTAPI APP ==================

app = FastAPI(
    title="B2B Marketplace API",
    version="1.0.0"
)

# ================== CORS CONFIGURATION ==================
#
# CORS EXPLANATION FOR THIS APPLICATION:
# =====================================
#
# 1. WHY `allow_credentials=False`:
#    - This app uses Firebase ID tokens via the `Authorization` header
#    - NO cookies are used for authentication
#    - `allow_credentials=True` is ONLY needed when:
#      a) Browser sends cookies/HTTP auth automatically
#      b) You need `withCredentials: true` in fetch/XMLHttpRequest
#    - Setting `allow_credentials=True` with `allow_origins=["*"]` is 
#      actually INVALID per CORS spec (browser ignores it)
#    - Keeping it `True` is misleading and suggests cookie-based auth
#
# 2. WHY `allow_origins=["*"]` is SAFE for mobile:
#    - Expo/React Native apps make direct HTTP calls (not browser XHR)
#    - Mobile apps don't have an "origin" - CORS is browser-only
#    - Security is enforced by Firebase token validation, not CORS
#    - CORS is ONLY a browser security feature, not API security
#
# 3. ENVIRONMENT-AWARE STRATEGY:
#    - Development: Allow all origins for testing flexibility
#    - Production: Can restrict to known web domains if web clients added
#    - Mobile apps are unaffected by origin restrictions
#

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
IS_PRODUCTION = ENVIRONMENT == "production" and not DEBUG

# Define allowed origins for web clients (when needed)
PRODUCTION_WEB_ORIGINS = [
    "https://midconnect-ten.vercel.app",
    "https://midconnect.vercel.app",
    "https://udyogconnect.in",
    "https://www.udyogconnect.in"
    # Add other production web domains here
]

# Development origins for local testing
DEVELOPMENT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]


def get_cors_origins():
    """
    Returns CORS origins based on environment.
    
    CRITICAL FIX: 
    - When allow_credentials=True, browsers REJECT wildcard origins ["*"]
    - Must always return explicit list of allowed origins
    
    Mobile apps (Expo/React Native):
    - Always work regardless of this setting
    - They bypass CORS entirely (direct HTTP, not browser XHR)
    
    Web clients:
    - Need explicit origin list for credentials to work
    """
    # Check for environment variable first (for production flexibility)
    env_origins = os.environ.get("CORS_ORIGINS", "")
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    
    # FIXED: Always return explicit origins (wildcard + credentials = browser reject)
    ALLOWED_ORIGINS = [
        # Production domains - UdyogConnect
        "https://www.udyogconnect.in",
        "https://udyogconnect.in",
        # Production domains - MidConnect legacy
        "https://midconnect-ten.vercel.app",
        "https://midconnect.vercel.app",
        "https://midconnect.onrender.com",
        # Vercel preview deployments pattern
        "https://midconnect-git-main.vercel.app",
        "https://midconnect-git-main-daulatmulgaonkargmailcoms-projects.vercel.app",
        "https://midconnect-e2kzxlgcq-daulatmulgaonkargmailcoms-projects.vercel.app",
        # Development
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        # Emergent preview URLs
        "https://app.emergent.sh",
        "https://search-typos.preview.emergentagent.com",
    ]
    
    # In both dev and prod, return explicit list (credentials require it)
    return ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    # Origins: MUST be explicit list when credentials=True
    allow_origins=get_cors_origins(),
    
    # CRITICAL: Set to True for web clients with credentials/tokens
    # We need this for proper preflight handling with Authorization headers
    allow_credentials=True,
    
    # Allow all HTTP methods (GET, POST, PUT, DELETE, PATCH, OPTIONS)
    allow_methods=["*"],
    
    # Allow all headers (including Authorization for Firebase tokens)
    allow_headers=["*"],
    
    # Expose custom headers to JavaScript clients
    expose_headers=["X-Request-ID"],
)


# ================== REQUEST LOGGING MIDDLEWARE ==================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging"""
    
    async def dispatch(self, request: StarletteRequest, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Create request context
        ctx = RequestContext(
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method
        )
        token = request_context.set(ctx)
        
        # Add request ID to response headers
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "client_ip": request.client.host if request.client else "unknown"
            }
            
            # Add user_id if available
            if ctx.user_id:
                log_data["user_id"] = ctx.user_id
            
            # Log based on status code
            if response.status_code >= 500:
                structured_logger.error("request_completed", **log_data)
            elif response.status_code >= 400:
                structured_logger.warning("request_completed", **log_data)
            else:
                structured_logger.info("request_completed", **log_data)
            
            # Record metrics
            metrics.record_request(request.url.path, response.status_code, latency_ms)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            structured_logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                latency_ms=round(latency_ms, 2)
            )
            raise
        finally:
            request_context.reset(token)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Add rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)


# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
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

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km using Haversine formula"""
    R = 6371  # Earth's radius in km
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

# ============== PYDANTIC MODELS ==============

class UserCreate(BaseModel):
    """SSOT: All fields use camelCase - LEGACY: For backward compatibility only"""
    email: EmailStr
    firebaseUid: str
    businessName: str
    phone: str
    city: str
    state: str
    pincode: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gstNumber: Optional[str] = None
    
    @field_validator('firebaseUid')
    @classmethod
    def validate_firebaseUid(cls, v):
        if not v or len(v) < 10:
            raise ValueError('Invalid Firebase UID')
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        # Remove non-digits and validate
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError('Phone must be 10-15 digits')
        return digits
    
    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Pincode must be 6 digits')
        return v
    
    @field_validator('gstNumber')
    @classmethod
    def validate_gst(cls, v):
        if v:
            pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.match(pattern, v.upper()):
                raise ValueError('Invalid GST number format')
            return v.upper()
        return v


class ProfileCompleteCreate(BaseModel):
    """
    PHASE 1 REGISTRATION: Profile completion after email verification
    
    Flow:
    1. Firebase user created, email verification sent
    2. User verifies email
    3. User selects role (buyer/seller) and completes profile
    4. This endpoint creates MongoDB user
    
    SSOT: All fields use camelCase
    """
    # Role selection - determines if GST is required
    role: Literal["buyer", "seller"]
    
    # Profile fields (required for both)
    businessName: str = Field(..., min_length=2, max_length=200)
    phone: str
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str
    
    # GST - ONLY for sellers
    gstNumber: Optional[str] = None
    
    model_config = {"extra": "forbid"}  # Reject unknown fields
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError('Phone must be 10-15 digits')
        return digits
    
    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Pincode must be 6 digits')
        return v
    
    @field_validator('gstNumber')
    @classmethod
    def validate_gst(cls, v):
        if v:
            pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.match(pattern, v.upper()):
                raise ValueError('Invalid GST number format')
            return v.upper()
        return v
    
    @model_validator(mode='after')
    def validate_seller_gst(self):
        """Seller MUST provide GST number"""
        if self.role == "seller" and not self.gstNumber:
            raise ValueError('GST number is required for seller registration')
        return self

class InitialRegisterCreate(BaseModel):
    """
    NEW ARCHITECTURE: Create MongoDB user immediately after Firebase signup
    
    Flow:
    1. Firebase user created (frontend)
    2. Frontend calls this endpoint immediately
    3. MongoDB user created with isEmailVerified: false, status: pending
    4. User verifies email
    5. On next login, isEmailVerified syncs to true
    6. User completes profile to access protected features
    
    SSOT: All fields use camelCase
    """
    # These are all we need - the rest comes from Firebase token
    pass  # No additional fields needed - all from token


class UserUpdate(BaseModel):
    """SSOT: All fields use camelCase"""
    businessName: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gstNumber: Optional[str] = None
    ownerName: Optional[str] = None
    gstDocument: Optional[str] = None  # Base64 encoded image
    gstStatus: Optional[Literal["pending", "verified", "rejected"]] = None

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Category name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Category name must be less than 100 characters')
        return v.strip()

# Technical Specification Schema - Admin defined, vendor cannot edit
class TechnicalSpec(BaseModel):
    name: str  # e.g., "Phase", "Voltage Range"
    key: str  # e.g., "phase", "voltageRange"
    type: Literal["dropdown", "number", "text", "range"]
    options: Optional[List[str]] = None  # For dropdown type
    unit: Optional[str] = None  # e.g., "V", "HP", "kW"
    required: bool = True
    
    @model_validator(mode='after')
    def validate_dropdown_options(self):
        if self.type == "dropdown" and not self.options:
            raise ValueError('Dropdown type requires options list')
        return self

# Extended Product Model with hierarchy
class ProductCreate(BaseModel):
    """SSOT: All fields use camelCase"""
    categoryId: str = Field(..., description="Category ID (ObjectId string)")
    family: str = Field(..., min_length=2, description="Product Family - e.g., 'Electric Motor'")
    variant: str = Field(..., min_length=2, description="Product Variant - e.g., 'AC Motor'")
    name: str = Field(..., min_length=2, description="Full product name - e.g., 'Three Phase AC Motor'")
    description: Optional[str] = None
    unit: str = "pcs"  # Normalized unit
    standardParameters: List[str] = []  # Legacy - for backward compatibility
    specSchema: List[TechnicalSpec] = []  # Locked technical specifications
    
    @field_validator('categoryId')
    @classmethod
    def validate_category_id(cls, v):
        try:
            ObjectId(v)
        except:
            raise ValueError('Invalid categoryId format')
        return v
    
    @field_validator('name', 'family', 'variant')
    @classmethod
    def validate_required_strings(cls, v, info):
        if not v or len(v.strip()) < 2:
            raise ValueError(f'{info.field_name} must be at least 2 characters')
        return v.strip()

# Product Request - When vendor can't find a product
class ProductRequestCreate(BaseModel):
    """SSOT: All fields use camelCase"""
    categoryId: str = Field(..., description="Category ID")
    family: str = Field(..., min_length=2)
    variant: str = Field(..., min_length=2)
    productName: str = Field(..., min_length=2)
    technicalDetails: str = Field(..., min_length=10)
    supportingDocument: Optional[str] = None  # Base64 image/PDF


# Seller Product Creation - Secure model that EXCLUDES sellerId
# sellerId is NEVER accepted from request body - always from authenticated user
class SellerProductCreate(BaseModel):
    """
    ⚠️ DEPRECATED: Use ListingCreate instead.
    
    Model for sellers to create products.
    
    ARCHITECTURAL NOTE:
    - This model is DEPRECATED. Products should be created by ADMIN only.
    - Sellers should use ListingCreate to create listings for existing products.
    - Sellers provide: productId, images (mandatory), pricingTiers (mandatory), description
    - Price belongs to SELLER listing, NOT to product template.
    
    SECURITY: This model explicitly EXCLUDES sellerId field.
    The sellerId is ALWAYS taken from the authenticated user's token.
    
    SSOT: All fields use camelCase.
    """
    categoryId: str = Field(..., description="Category ID (ObjectId string)")
    family: str = Field(..., min_length=2, max_length=100, description="Product family")
    variant: str = Field(..., min_length=2, max_length=100, description="Product variant")
    name: str = Field(..., min_length=2, max_length=200, description="Product name")
    description: Optional[str] = Field(None, max_length=2000, description="Product description")
    unit: str = Field("pieces", description="Unit of measurement")
    price: float = Field(..., gt=0, description="DEPRECATED: Price belongs to listing, not product")
    stock: int = Field(0, ge=0, description="Available stock quantity")
    moq: int = Field(1, ge=1, description="Minimum order quantity")
    images: List[str] = Field(default_factory=list, max_length=10, description="Product image URLs")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Product specifications")
    
    model_config = {"extra": "forbid"}  # STRICT: Reject any extra fields like sellerId
    
    @field_validator('categoryId')
    @classmethod
    def validate_category_id(cls, v):
        try:
            ObjectId(v)
        except:
            raise ValueError('Invalid categoryId format - must be valid ObjectId')
        return v
    
    @field_validator('name', 'family', 'variant')
    @classmethod
    def validate_required_strings(cls, v, info):
        if not v or len(v.strip()) < 2:
            raise ValueError(f'{info.field_name} must be at least 2 characters')
        return v.strip()
    
    @field_validator('price')
    @classmethod
    def validate_price_positive(cls, v):
        if v <= 0:
            raise ValueError('price must be greater than 0')
        return round(v, 2)
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 images allowed')
        return v[:10]


class PricingSlab(BaseModel):
    """SSOT: All fields use camelCase"""
    minQuantity: int
    maxQuantity: Optional[int] = None
    pricePerUnit: float
    timeBasis: Literal["day", "week", "month"] = "day"
    
    @field_validator('minQuantity')
    @classmethod
    def validate_min_quantity(cls, v):
        if v < 1:
            raise ValueError('minQuantity must be at least 1')
        return v
    
    @field_validator('pricePerUnit')
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('pricePerUnit cannot be negative')
        return round(v, 2)
    
    @model_validator(mode='after')
    def validate_quantity_range(self):
        if self.maxQuantity is not None and self.maxQuantity < self.minQuantity:
            raise ValueError('maxQuantity must be >= minQuantity')
        return self

class ListingCreate(BaseModel):
    """
    Model for sellers to create listings for existing products.
    
    ARCHITECTURAL RULE:
    - Sellers create LISTINGS, NOT products
    - productId references admin-created product template
    - Seller provides: images, description, price (pricingTiers)
    - Price belongs to SELLER (in listing), NOT to PRODUCT
    
    SSOT: All fields use camelCase.
    """
    productId: str = Field(..., description="Product ID (references admin-created product)")
    sellerRole: Literal["Manufacturer", "Dealer", "Distributor", "Trader"]
    specifications: Dict[str, str] = {}  # Vendor's spec values - must match product's specSchema keys
    description: Optional[str] = Field(None, max_length=2000, description="Seller's product description")
    images: List[str] = Field(..., min_length=1, description="Mandatory: At least 1 image required from seller")
    quantity: int = Field(..., ge=1, description="Available stock quantity")
    moq: int = Field(..., ge=1, description="Minimum Order Quantity")
    maxCapacity: int = Field(..., ge=1, description="Maximum production/delivery capacity")
    capacityTimeBasis: Literal["day", "week", "month"] = "day"
    pricingSlabs: List[PricingSlab] = Field(..., min_length=1, description="Mandatory: At least 1 pricing tier required")
    leadTime: Optional[str] = None  # e.g., "2-3 days"
    packagingSize: Optional[str] = None  # e.g., "10 pieces/box"
    deliveryLocations: List[str] = []  # Cities/states vendor delivers to
    sellerNotes: Optional[str] = None  # Non-technical notes
    isDraft: bool = True
    
    @field_validator('productId')
    @classmethod
    def validate_product_id(cls, v):
        try:
            ObjectId(v)
        except:
            raise ValueError('Invalid productId format')
        return v
    
    @field_validator('quantity', 'moq', 'maxCapacity')
    @classmethod
    def validate_positive_int(cls, v, info):
        if v < 1:
            raise ValueError(f'{info.field_name} must be at least 1')
        return v
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 images allowed')
        # Validate Cloudinary URL format
        CLOUDINARY_CLOUD_NAME = 'dco24qmoq'
        valid_prefix = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/'
        for i, url in enumerate(v):
            if not url.startswith(valid_prefix):
                raise ValueError(f'Image {i+1}: Invalid image URL. Must be from Cloudinary')
        return v
    
    @model_validator(mode='after')
    def validate_moq_capacity(self):
        if self.moq > self.maxCapacity:
            raise ValueError('MOQ cannot exceed maxCapacity')
        return self

class ListingUpdate(BaseModel):
    """SSOT: All fields use camelCase"""
    specifications: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    quantity: Optional[int] = None
    moq: Optional[int] = None
    maxCapacity: Optional[int] = None
    capacityTimeBasis: Optional[Literal["day", "week", "month"]] = None
    pricingSlabs: Optional[List[PricingSlab]] = None
    sellerRole: Optional[Literal["Manufacturer", "Dealer", "Distributor", "Trader"]] = None
    leadTime: Optional[str] = None
    packagingSize: Optional[str] = None
    deliveryLocations: Optional[List[str]] = None
    sellerNotes: Optional[str] = None
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError('Maximum 10 images allowed')
        # Validate Cloudinary URL format
        CLOUDINARY_CLOUD_NAME = 'dco24qmoq'
        valid_prefix = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/'
        for i, url in enumerate(v):
            if not url.startswith(valid_prefix):
                raise ValueError(f'Image {i+1}: Invalid image URL. Must be from Cloudinary')
        return v

class EnquiryCreate(BaseModel):
    """SSOT: All fields use camelCase"""
    listingId: str
    quantity: int
    message: Optional[str] = None
    
    @field_validator('listingId')
    @classmethod
    def validate_listing_id(cls, v):
        try:
            ObjectId(v)
        except:
            raise ValueError('Invalid listingId format')
        return v
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('quantity must be at least 1')
        return v

class SearchQuery(BaseModel):
    query: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    expand_to_all_india: bool = False
    category_id: Optional[str] = None
    min_quantity: Optional[int] = None
    max_price: Optional[float] = None
    skip: int = 0
    limit: int = DEFAULT_PAGE_SIZE
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        return sanitize_search_query(v, max_length=200)
    
    @field_validator('skip')
    @classmethod
    def validate_skip(cls, v):
        return max(0, v)
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        return min(max(1, v), MAX_PAGE_SIZE)
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('latitude must be between -90 and 90')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('longitude must be between -180 and 180')
        return v

# ============== AUTH DEPENDENCY ==============

async def verify_firebase_token(token: str) -> dict:
    """Verify Firebase ID token and return decoded token data"""
    # DEV MODE: When Firebase is not initialized, allow test token for development
    if not firebase_initialized:
        # Allow special dev token for testing
        if token == "dev-test-token":
            logger.warning("DEV MODE: Using test token for development testing")
            return {
                "uid": "dev-test-uid-12345",
                "email": "admin@test.com",
                "emailVerified": True,
                "admin": True
            }
        raise HTTPException(
            status_code=503,
            detail="Authentication service not configured"
        )

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase token verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify Firebase token and get user from MongoDB.
    
    NEW ARCHITECTURE:
    - If user doesn't exist in MongoDB, create with pending status
    - Sync email verification status from Firebase to MongoDB
    - Return user regardless of email verification status
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    try:
        token = credentials.credentials
        
        # Verify Firebase ID token
        decoded_token = await verify_firebase_token(token)
        firebaseUid = decoded_token['uid']
        email = decoded_token.get('email', '')
        # NOTE: We DO NOT use Firebase email_verified for business logic
        # MongoDB isEmailVerified is the SINGLE SOURCE OF TRUTH
        
        # Log firebaseUid for debugging (masked for privacy)
        masked_uid = f"{firebaseUid[:8]}...{firebaseUid[-4:]}" if len(firebaseUid) > 12 else firebaseUid
        logger.info(f"🔐 Auth: firebaseUid={masked_uid}")
        
        # Store decoded token for admin claim check
        firebase_admin_claim = decoded_token.get('admin', False)
        
        # Get user from MongoDB - SSOT: Use camelCase field name
        user = await db.users.find_one({"firebaseUid": firebaseUid})
        
        # NEW ARCHITECTURE: Create user immediately if not exists
        if not user:
            logger.info(f"🔐 Auth: Creating new user for firebaseUid={masked_uid}")
            now = datetime.now(timezone.utc)
            verification_deadline = now + timedelta(hours=24)
            
            user = {
                "_id": ObjectId(),
                "firebaseUid": firebaseUid,
                "email": email,
                "roles": ["buyer"],  # Default role
                "isAdmin": False,
                "profile": None,  # Profile completion required
                "profileComplete": False,
                "gst": {
                    "number": None,
                    "status": None,
                    "verified": False
                },
                "isEmailVerified": False,  # SSOT: Always start as false, verify via our system
                "status": "pending",
                "verificationDeadline": verification_deadline,
                "accountStatus": "active",
                "canLogin": True,
                "isActive": True,
                "deletedAt": None,
                "deletionReason": None,
                "subscription": {
                    "plan": "free",
                    "status": "free",
                    "startDate": now,
                    "endDate": None,
                    "trialEndsAt": None,
                    "inquiryLimit": 5,
                    "enquiriesThisMonth": 0,
                    "enquiriesResetAt": now + timedelta(days=30)
                },
                "favourites": [],
                "recentSearches": [],
                "createdAt": now,
                "updatedAt": now
            }
            await db.users.insert_one(user)
            logger.info(f"🔐 Auth: Created pending user: {email}")
        else:
            logger.info(f"🔐 Auth: User found in DB for firebaseUid={masked_uid}")
        
        # DEV MODE: If dev token, ensure admin role
        if firebaseUid == "dev-test-uid-12345" and not firebase_initialized:
            if "admin" not in user.get("roles", []):
                await db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"roles": ["admin", "seller", "buyer"], "isAdmin": True}}
                )
                user["roles"] = ["admin", "seller", "buyer"]
                user["isAdmin"] = True
        
        # Attach Firebase admin claim to user object for require_admin check
        user["_firebase_admin_claim"] = firebase_admin_claim
        
        return serialize_doc(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return None

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require authenticated user"""
    if credentials is None:
        metrics.record_auth_failure("no_credentials")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = await get_current_user(credentials)
    if not user:
        metrics.record_auth_failure("user_not_found")
        raise HTTPException(status_code=401, detail="User not found. Please register first.")
    
    # Set user in request context for logging
    user_id = str(user.get("_id", ""))
    set_user_id(user_id)
    
    # Check if account is deleted
    if user.get("accountStatus") == "deleted":
        deleted_at = user.get("deletedAt")
        if deleted_at:
            # Handle datetime if it was serialized to string
            if isinstance(deleted_at, str):
                try:
                    deleted_at = datetime.fromisoformat(deleted_at.replace('Z', '+00:00'))
                except ValueError:
                    deleted_at = datetime.strptime(deleted_at, "%Y-%m-%dT%H:%M:%S.%f")
            # Check if within 30-day grace period
            grace_period_end = deleted_at + timedelta(days=30)
            if datetime.now(timezone.utc) < grace_period_end:
                # Allow login to restore account
                metrics.record_auth_failure("account_deleted_restorable")
                raise HTTPException(
                    status_code=403, 
                    detail="ACCOUNT_DELETED_RESTORABLE",
                    headers={"X-Account-Deleted": "true", "X-Can-Restore": "true"}
                )
            else:
                # Account is archived (past grace period)
                metrics.record_auth_failure("account_permanently_deleted")
                raise HTTPException(status_code=403, detail="Account has been permanently deactivated. Contact support for assistance.")
        metrics.record_auth_failure("account_deactivated")
        raise HTTPException(status_code=403, detail="Account has been deactivated.")
    
    if not user.get("canLogin", True):
        metrics.record_auth_failure("login_restricted")
        raise HTTPException(status_code=403, detail="Account access has been restricted. Contact support.")
    
    # Record successful auth
    metrics.record_auth_success(user_id)
    
    return user

async def require_verified_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Require email-verified user (for enquiries and publishing).
    
    NEW ARCHITECTURE: Check both isEmailVerified and emailVerified for compatibility
    """
    user = await require_auth(credentials)
    
    # Check both new and legacy verification fields
    is_verified = user.get("isEmailVerified", False) or user.get("emailVerified", False)
    
    if not is_verified:
        metrics.record_auth_failure("email_not_verified")
        raise HTTPException(
            status_code=403, 
            detail="Email verification required. Please verify your email first."
        )
    return user


async def require_profile_complete(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Require user with completed profile for protected actions.
    
    NEW ARCHITECTURE:
    - Must be email verified
    - Must have profile completed
    """
    user = await require_verified_user(credentials)
    
    # Check if profile is complete
    profile = user.get("profile")
    profile_complete = user.get("profileComplete", False)
    
    if not profile or not profile_complete:
        raise HTTPException(
            status_code=403,
            detail="Profile completion required. Please complete your profile first."
        )
    
    return user

async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Require admin user for admin-only endpoints.
    Uses DUAL-CHECK authorization:
    1. Firebase Custom Claim (admin: true in token)
    2. MongoDB isAdmin flag (camelCase SSOT)
    Both must be true for admin access (defense in depth).
    """
    user = await require_auth(credentials)
    
    # Check Firebase Custom Claim (primary authorization)
    firebase_admin_claim = user.get("_firebase_admin_claim", False)
    
    # Check MongoDB isAdmin flag - SSOT: camelCase
    mongodb_is_admin = user.get("isAdmin", False)
    
    # Log authorization attempt for audit
    structured_logger.info(
        "admin_auth_check",
        user_email=user.get('email'),
        firebase_claim=firebase_admin_claim,
        mongodb_flag=mongodb_is_admin
    )
    
    # DUAL-CHECK: Both Firebase claim AND MongoDB flag must be true
    # However, for initial setup, allow MongoDB-only admin if no Firebase claims exist yet
    if not mongodb_is_admin:
        metrics.record_auth_failure("admin_access_denied")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # If Firebase claims are properly set up, require both
    # For now, MongoDB isAdmin is the primary check (backwards compatible)
    # TODO: Once Firebase custom claims are set for all admins, enable strict dual-check:
    # if not (firebase_admin_claim and mongodb_is_admin):
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

async def require_verified_seller(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Require a verified seller for seller product management.
    
    PHASE 3 - SELLER STATE DERIVED (NO sellerStatus FIELD):
    - is_seller = "seller" in user["roles"]
    - is_verified = user["gst"]["verified"] == True
    - is_pending = user["gst"]["status"] == "pending"
    
    User must:
    1. Be authenticated
    2. Have "seller" in roles array
    3. Have active account
    """
    user = await require_auth(credentials)
    
    # PHASE 3: Derive seller status from roles array
    roles = user.get("roles", [])
    is_seller = "seller" in roles
    
    if not is_seller:
        metrics.record_auth_failure("seller_access_denied")
        raise HTTPException(
            status_code=403, 
            detail="You must register as a seller to access this section."
        )
    
    # Check account is active
    if user.get("accountStatus") == "deleted":
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    return user


async def require_gst_verified_seller(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Require a GST-verified seller for publishing products.
    
    UNIFIED GST SCHEMA - SINGLE SOURCE OF TRUTH:
    gst: {
        number: string,
        status: "pending" | "verified" | "rejected",
        verified: boolean
    }
    
    PERMISSION CONTROL:
    - CASE 1: Not seller -> 403
    - CASE 2: Seller but GST pending -> 403 (for publish)
    - CASE 3: Seller but GST rejected -> 403 (for publish)
    - CASE 4: Seller GST verified -> Allow
    """
    user = await require_verified_seller(credentials)
    
    # Check seller status (banned/suspended)
    seller_status = user.get("sellerStatus", "active")
    if seller_status == "banned":
        raise HTTPException(
            status_code=403,
            detail="Seller account is banned. Contact support for assistance."
        )
    if seller_status == "suspended":
        raise HTTPException(
            status_code=403,
            detail="Seller account is suspended. Contact support for assistance."
        )
    
    # Check GST verification status - SSOT: gst.status must be "verified"
    gst = user.get("gst", {})
    gst_status = gst.get("status", "none")
    
    if gst_status != "verified":
        raise HTTPException(
            status_code=403,
            detail=f"GST verification required. Current status: {gst_status}"
        )
    
    return user

# ============== USER ENDPOINTS ==============

@api_router.post("/users/register")
@limiter.limit("5/minute")
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user after Firebase authentication.
    
    Production-safe: handles duplicate registration gracefully without crash.
    """
    # Check if user already exists by firebaseUid or email
    existing = await db.users.find_one({"$or": [
        {"email": user_data.email},
        {"firebaseUid": user_data.firebaseUid}
    ]})
    
    # If user exists, return their profile (idempotent - no error)
    if existing:
        logger.info(f"User already exists, returning existing profile: {user_data.email}")
        return {"message": "User already registered", "user": serialize_doc(existing)}
    
    # Calculate trial end date (first 50 users get 90 days, rest get 21 days)
    user_count = await db.users.count_documents({})
    trial_days = 90 if user_count < 50 else 21
    
    user_doc = {
        "_id": ObjectId(),
        "email": user_data.email,
        "firebaseUid": user_data.firebaseUid,
        "roles": ["user"],
        "profile": {
            "businessName": user_data.businessName,
            "phone": user_data.phone,
            "city": user_data.city,
            "state": user_data.state,
            "pincode": user_data.pincode,
            "address": user_data.address,
            "latitude": user_data.latitude,
            "longitude": user_data.longitude
        },
        "gst": {
            "number": user_data.gstNumber,
            "status": None,
            "verified": False
        },
        "emailVerified": False,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),

        # Account status fields for soft delete
        "accountStatus": "active",  # active, deleted, archived
        "isActive": True,
        "canLogin": True,
        "deletedAt": None,
        "deletionReason": None,

                                                                         
        "subscription": {
            "plan": "trial",
            "status": "trial",
            "startDate": datetime.now(timezone.utc),
            "trialEndsAt": datetime.now(timezone.utc) + timedelta(days=trial_days),
            "endDate": None,
            "inquiryLimit": 10,
            "enquiriesThisMonth": 0,
            "enquiriesResetAt": datetime.now(timezone.utc) + timedelta(days=30)
        },

        "favourites": [],
        "recentSearches": [],
        "isAdmin": False
    }
    
    try:
        await db.users.insert_one(user_doc)
        logger.info(f"New user registered: {user_data.email}")
        return {"message": "User registered successfully", "user": serialize_doc(user_doc)}
    except Exception as e:
        # Handle race condition: if duplicate key error, return existing user
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            logger.warning(f"Duplicate key during registration, fetching existing user: {user_data.email}")
            existing = await db.users.find_one({"$or": [
                {"email": user_data.email},
                {"firebaseUid": user_data.firebaseUid}
            ]})
            if existing:
                return {"message": "User already registered", "user": serialize_doc(existing)}
        # Re-raise other errors
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

# ============== EMAIL VERIFICATION (Custom Zoho SMTP) ==============

# REMOVED: SendVerificationRequest - no longer needed, we use auth token

@api_router.post("/send-verification")
@limiter.limit("3/minute")
async def send_verification_email(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Send verification email via Resend.
    
    Uses auth token to get user email.
    No request body required - backend knows user from token.
    This is called immediately after Firebase signup.
    
    MIGRATION: Now uses Resend instead of Zoho SMTP.
    """
    from services.email_service import get_email_verification_service
    
    # Get current user from auth token (auto-creates if not exists)
    current_user = await get_current_user(credentials)
    
    # Check if already verified
    if current_user.get("isEmailVerified"):
        return {"success": True, "message": "Email is already verified. Please login."}
    
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email associated with this account")
    
    email_service = get_email_verification_service(db)
    result = await email_service.send_verification_email(email)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send email"))
    
    return result

@api_router.get("/verify-email")
async def verify_email_token(token: str):
    """
    Verify email using token from verification link.
    
    Called when user clicks the verification link in their email.
    Returns redirect URL for frontend.
    
    MIGRATION: Now uses Resend-based token verification.
    """
    from services.email_service import get_email_verification_service
    
    if not token:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    email_service = get_email_verification_service(db)
    result = await email_service.verify_token(token)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Verification failed"))
    
    return result

@api_router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification_email(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Resend verification email via Resend.
    
    Uses auth token to get user email.
    No request body required - backend knows user from token.
    Rate limited to prevent abuse.
    
    MIGRATION: Now uses Resend instead of Zoho SMTP.
    """
    from services.email_service import get_email_verification_service
    
    # Get current user from auth token
    current_user = await get_current_user(credentials)
    
    # Check if already verified - no need to resend
    if current_user.get("isEmailVerified"):
        return {"success": True, "message": "Email is already verified. Please login."}
    
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email associated with this account")
    
    email_service = get_email_verification_service(db)
    result = await email_service.send_verification_email(email)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send email"))
    
    return result


@api_router.post("/auth/complete-profile")
@limiter.limit("5/minute")
async def complete_profile(
    request: Request,
    profile_data: ProfileCompleteCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    NEW ARCHITECTURE - COMPLETE PROFILE (UPDATE EXISTING USER)
    
    Flow:
    1. User already exists in MongoDB (created on signup via get_current_user)
    2. User verifies email (Firebase)
    3. On login, isEmailVerified syncs to true
    4. User fills profile form
    5. This endpoint UPDATES the existing user with profile data
    
    PHASE 2 - DATABASE UPDATE STRUCTURE (STRICTLY ALIGNED):
    - roles: ["buyer"] or ["buyer", "seller"]
    - gst.number: seller only
    - gst.status: "pending" for seller, null for buyer
    
    PHASE 6 - PINCODE GEO LOGIC:
    - Validate pincode exists in pincodes collection
    - Fetch latitude & longitude
    - Save to profile.latitude, profile.longitude
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization token required")
    
    try:
        # Verify Firebase token
        token = credentials.credentials
        decoded_token = await verify_firebase_token(token)
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        # Get existing user (should exist from get_current_user auto-creation)
        existing = await db.users.find_one({"firebaseUid": firebase_uid})
        
        if not existing:
            # Edge case: user doesn't exist yet - create them
            logger.warning(f"User not found during profile completion, creating: {email}")
        
        # ENTERPRISE FIX: Use MongoDB isEmailVerified as SINGLE SOURCE OF TRUTH
        # Do NOT use Firebase email_verified here
        mongo_verified = existing.get("isEmailVerified", False) if existing else False
        if not mongo_verified:
            raise HTTPException(
                status_code=403,
                detail="Email verification required. Please check your inbox and verify your email first."
            )
        
        # Check if profile is already complete
        if existing and existing.get("profileComplete"):
            logger.info(f"User profile already completed: {email}")
            return {"message": "Profile already completed", "user": serialize_doc(existing)}
        
        # PHASE 6 - PINCODE GEO LOGIC
        latitude = None
        longitude = None
        pincode_doc = await db.pincodes.find_one({"pincode": profile_data.pincode})
        if pincode_doc:
            latitude = pincode_doc.get("latitude")
            longitude = pincode_doc.get("longitude")
            logger.info(f"Pincode {profile_data.pincode} found: lat={latitude}, lng={longitude}")
        else:
            logger.warning(f"Pincode {profile_data.pincode} not found in pincodes collection")
        
        # Calculate trial end date (90 days as per spec)
        now = datetime.now(timezone.utc)
        trial_days = 90
        
        # Calculate next month for enquiriesResetAt
        next_month = now.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)  # First day of next month
        
        # PHASE 2 - BUILD ROLES ARRAY
        if profile_data.role == "seller":
            roles = ["buyer", "seller"]
            gst_number = profile_data.gstNumber
            gst_status = "pending"
        else:
            roles = ["buyer"]
            gst_number = None
            gst_status = None
        
        # Build update document
        update_doc = {
            "roles": roles,
            "profile": {
                "businessName": profile_data.businessName,
                "phone": profile_data.phone,
                "city": profile_data.city,
                "state": profile_data.state,
                "pincode": profile_data.pincode,
                "address": profile_data.address,
                "latitude": latitude,
                "longitude": longitude
            },
            "profileComplete": True,
            "gst": {
                "number": gst_number,
                "status": gst_status,
                "verified": False
            },
            "isEmailVerified": True,
            "emailVerified": True,
            "status": "active",
            "subscription": {
                "plan": "trial",
                "status": "trial",
                "startDate": now,
                "endDate": None,
                "trialEndsAt": now + timedelta(days=trial_days),
                "inquiryLimit": 10,
                "enquiriesThisMonth": 0,
                "enquiriesResetAt": next_month
            },
            "updatedAt": now
        }
        
        if existing:
            # UPDATE existing user
            await db.users.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": update_doc,
                    "$unset": {"verificationDeadline": ""}
                }
            )
            # Get updated user
            updated_user = await db.users.find_one({"_id": existing["_id"]})
            logger.info(f"Profile completed for existing user: {email}, role: {profile_data.role}")
            
            return {
                "message": "Profile completed successfully",
                "user": serialize_doc(updated_user),
                "isSeller": "seller" in roles,
                "gstStatus": gst_status
            }
        else:
            # CREATE new user (edge case)
            user_doc = {
                "_id": ObjectId(),
                "email": email,
                "firebaseUid": firebase_uid,
                "isAdmin": False,
                "accountStatus": "active",
                "canLogin": True,
                "isActive": True,
                "deletedAt": None,
                "deletionReason": None,
                "favourites": [],
                "recentSearches": [],
                "createdAt": now,
                **update_doc
            }
            
            await db.users.insert_one(user_doc)
            logger.info(f"New user registered via profile completion: {email}, role: {profile_data.role}")
            
            return {
                "message": "Profile completed successfully",
                "user": serialize_doc(user_doc),
                "isSeller": "seller" in roles,
                "gstStatus": gst_status
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile completion error: {e}")
        raise HTTPException(status_code=500, detail="Profile completion failed. Please try again.")


@api_router.get("/auth/check-registration")
async def check_registration_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    ENTERPRISE FIX: Check user registration and profile completion status.
    
    MongoDB isEmailVerified is the SINGLE SOURCE OF TRUTH.
    Firebase email_verified is NOT used for business logic.
    
    Returns:
    - profileComplete: true if user has completed profile
    - isEmailVerified: true if email is verified (from MongoDB)
    - needsVerification: true if email needs verification
    - user: MongoDB user profile if exists
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization token required")
    
    try:
        # Get user (auto-created by get_current_user if not exists)
        user = await get_current_user(credentials)
        
        if user:
            profile_complete = user.get("profileComplete", False)
            # SSOT: Use ONLY MongoDB isEmailVerified
            is_email_verified = user.get("isEmailVerified", False)
            
            return {
                "profileComplete": profile_complete,
                "isEmailVerified": is_email_verified,
                "needsVerification": not is_email_verified,
                "needsProfileCompletion": not profile_complete and is_email_verified,
                "user": user
            }
        else:
            # This shouldn't happen as get_current_user auto-creates
            return {
                "profileComplete": False,
                "isEmailVerified": False,
                "needsVerification": True,
                "needsProfileCompletion": False,
                "email": "",
                "firebaseUid": ""
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check registration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check registration status")


@api_router.post("/auth/cleanup-for-reregister")
@limiter.limit("3/minute")
async def cleanup_for_reregister(request: Request, email: str = Body(..., embed=True)):
    """
    STEP 6 - HANDLE RE-REGISTRATION SAFELY
    
    Before creating a new Firebase user on signup, call this endpoint to:
    - Check if unverified user exists
    - Delete from both MongoDB and Firebase
    - Allow clean re-registration
    
    This prevents:
    - "Email already exists in Firebase but not in database" error
    """
    try:
        # Find existing unverified user by email
        mongo_user = await db.users.find_one({"email": email})
        
        if not mongo_user:
            return {"message": "No existing user found", "cleaned": False}
        
        # Only cleanup if NOT email verified
        is_verified = mongo_user.get("isEmailVerified", False) or mongo_user.get("emailVerified", False)
        
        if is_verified:
            raise HTTPException(
                status_code=400,
                detail="Email already registered and verified. Please login instead."
            )
        
        # User exists but not verified - clean up
        firebase_uid = mongo_user.get("firebaseUid")
        
        # Delete from Firebase first
        if firebase_uid and firebase_initialized:
            try:
                firebase_auth.delete_user(firebase_uid)
                logger.info(f"🧹 Re-registration cleanup: Deleted Firebase user for {email}")
            except Exception as fb_err:
                # Firebase user might not exist or already deleted
                logger.warning(f"⚠️ Could not delete Firebase user for {email}: {fb_err}")
        
        # Delete from MongoDB
        await db.users.delete_one({"_id": mongo_user["_id"]})
        logger.info(f"🧹 Re-registration cleanup: Deleted MongoDB user for {email}")
        
        return {
            "message": "Previous unverified registration cleaned up",
            "cleaned": True,
            "email": email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup for re-register error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup for re-registration")


@api_router.get("/users/me")
async def get_current_user_profile(user: dict = Depends(require_auth)):
    """Get current user profile"""
    return serialize_doc(user)

@api_router.put("/users/me")
async def update_user_profile(update_data: UserUpdate, user: dict = Depends(require_auth)):
    """Update current user profile"""
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": update_dict}
    )
    
    updated_user = await db.users.find_one({"_id": ObjectId(user["_id"])})
    return serialize_doc(updated_user)

@api_router.post("/users/verify-email")
async def verify_email(user: dict = Depends(require_auth)):
    """Mark user email as verified (called after Firebase email verification)"""
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {"emailVerified": True, "updatedAt": datetime.now(timezone.utc)}}
    )
    return {"message": "Email verified successfully"}

@api_router.post("/users/favourites/{listing_id}")
async def add_favourite(listing_id: str, user: dict = Depends(require_auth)):
    """Add a listing to favourites"""
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$addToSet": {"favourites": listing_id}}
    )
    return {"message": "Added to favourites"}

@api_router.delete("/users/favourites/{listing_id}")
async def remove_favourite(listing_id: str, user: dict = Depends(require_auth)):
    """Remove a listing from favourites"""
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$pull": {"favourites": listing_id}}
    )
    return {"message": "Removed from favourites"}

@api_router.get("/users/favourites")
async def get_favourites(user: dict = Depends(require_auth)):
    """Get user's favourite listings from seller_listings collection"""
    favourite_ids = user.get("favourites", [])
    if not favourite_ids:
        return []
    
    # SSOT: Use seller_listings with status="active" instead of is_draft=False
    listings = await db.sellerListings.find({
        "_id": {"$in": [ObjectId(fid) for fid in favourite_ids]},
        "status": "active"
    }).to_list(100)
    
    return serialize_doc(listings)

@api_router.post("/users/me/gst")
async def upload_gst_certificate(
    owner_name: str = Form(...),
    gst_number: str = Form(...),
    gst_status: str = Form("pending"),
    gst_document: UploadFile = File(...),
    user: dict = Depends(require_auth)
):
    """Upload GST certificate with owner details"""
    # Log incoming GST payload for verification
    logger.info(f"GST Upload - User: {user.get('email')}")
    logger.info(f"GST Upload - owner_name: {owner_name}")
    logger.info(f"GST Upload - gst_number: {gst_number}")
    logger.info(f"GST Upload - file: {gst_document.filename}, type: {gst_document.content_type}")
    
    # Validate GST number format
    import re
    gst_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(gst_pattern, gst_number.upper()):
        logger.warning(f"GST Upload - Invalid GST format: {gst_number}")
        raise HTTPException(status_code=400, detail="Invalid GST number format")
    
    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
    if gst_document.content_type not in allowed_types:
        logger.warning(f"GST Upload - Invalid file type: {gst_document.content_type}")
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only PDF, JPG, PNG allowed."
        )
    
    # Read file and convert to base64 for storage
    file_content = await gst_document.read()
    
    # Check file size (max 5MB)
    if len(file_content) > 5 * 1024 * 1024:
        logger.warning(f"GST Upload - File too large: {len(file_content)} bytes")
        raise HTTPException(status_code=400, detail="File too large. Max 5MB allowed.")
    
    logger.info(f"GST Upload - File size: {len(file_content)} bytes")
    
    # Encode as base64 for storage in MongoDB
    file_base64 = base64.b64encode(file_content).decode('utf-8')
    document_data = f"data:{gst_document.content_type};base64,{file_base64}"
    
    # Update user profile with GST details
    update_data = {
        "ownerName": owner_name.strip(),
        "gstNumber": gst_number.upper().strip(),
        "gstDocument": document_data,
        "gst_document_filename": gst_document.filename,
        "gstStatus": gst_status,
        "updatedAt": datetime.now(timezone.utc)
    }
    
    result = await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": update_data}
    )
    
    logger.info(f"GST Upload - MongoDB update result: matched={result.matched_count}, modified={result.modified_count}")
    
    # Verify the update by fetching the user
    updated_user = await db.users.find_one({"_id": ObjectId(user["_id"])})
    if updated_user:
        logger.info("GST Upload - Verified saved data:")
        logger.info(f"  - owner_name: {updated_user.get('owner_name')}")
        logger.info(f"  - gst_number: {updated_user.get('gst_number')}")
        logger.info(f"  - gst_status: {updated_user.get('gst_status')}")
        logger.info(f"  - gst_document present: {bool(updated_user.get('gst_document'))}")
    
    return {
        "message": "GST details uploaded successfully", 
        "gstStatus": gst_status,
        "ownerName": owner_name.strip(),
        "gstNumber": gst_number.upper().strip()
    }


# ============== BECOME SELLER ENDPOINT ==============

class BecomeSellerRequest(BaseModel):
    """Request model for becoming a seller - SSOT: camelCase fields
    
    NOTE: No seller_type field - badge comes from each product's sellerRoleForProduct
    A single seller can have different roles for different products:
    - Manufacturer of Product A
    - Dealer of Product B
    - Distributor of Product C
    """
    businessName: str
    businessLocation: str
    gstNumber: str  # MANDATORY for sellers
    
    model_config = {"populate_by_name": True}
    
    @field_validator('businessName')
    @classmethod
    def validate_business_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Business name must be at least 2 characters')
        return v.strip()
    
    @field_validator('businessLocation')
    @classmethod
    def validate_business_location(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Business location is required')
        return v.strip()
    
    @field_validator('gstNumber')
    @classmethod
    def validate_gst_number(cls, v):
        if not v:
            raise ValueError('GST number is mandatory for sellers')
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if not re.match(pattern, v.upper()):
            raise ValueError('Invalid GST number format')
        return v.upper()

@api_router.post("/users/become-seller")
@limiter.limit("3/minute")
async def become_seller(
    request: Request,
    seller_data: BecomeSellerRequest,
    user: dict = Depends(require_auth)
):
    """
    Upgrade user from buyer to seller role.
    
    Requirements:
    - User must not already be a seller
    - GST number is MANDATORY
    - Business details are required
    
    After becoming seller:
    - Products created will be in 'draft' status until GST is verified
    - User can list products immediately (but they stay private)
    - Products become public once GST is verified by admin
    
    NOTE: seller_type is NOT stored on user - badge comes from each product's sellerRoleForProduct
    """
    # Check if already a seller
    if user.get("isSeller"):
        raise HTTPException(
            status_code=400,
            detail="You are already registered as a seller"
        )
    
    # Check if GST already used by another seller
    existing_gst = await db.users.find_one({
        "gst.number": seller_data.gstNumber,
        "_id": {"$ne": ObjectId(user["_id"])}
    })
    if existing_gst:
        raise HTTPException(
            status_code=409,
            detail="This GST number is already registered with another account"
        )
    
    # Update user to seller (NO seller_type - badge comes from product)
    update_data = {
        "isSeller": True,
        "profile.businessName": seller_data.businessName,
        "profile.city": seller_data.businessLocation,
        "gst.number": seller_data.gstNumber,
        "gst.status": "pending",
        "gst.verified": False,
        "updatedAt": datetime.now(timezone.utc)
    }
    
    result = await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=500,
            detail="We couldn't save your business details right now. This is a temporary issue. Please try again in a moment."
        )
    
    # Fetch updated user
    updated_user = await db.users.find_one({"_id": ObjectId(user["_id"])})
    
    logger.info(f"User {user.get('email')} upgraded to seller with GST: {seller_data.gstNumber}")
    
    return {
        "message": "Seller account activated successfully",
        "user": serialize_doc(updated_user),
        "notice": "Your products will be published only after GST verification. You can start creating product listings now."
    }


# ============== ADMIN GST PENDING REVIEWS ENDPOINT ==============

@api_router.get("/admin/gst/pending")
async def admin_get_pending_gst(
    admin: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get sellers with pending GST verification.
    
    UNIFIED GST SCHEMA - SINGLE SOURCE OF TRUTH:
    gst: {
        number: string,
        status: "pending" | "verified" | "rejected",
        verified: boolean
    }
    
    Query:
    - roles includes "seller"
    - gst.number exists and is not empty
    - gst.status = "pending"
    - gst.verified = false
    """
    # SSOT: Use unified gst schema only
    query = {
        "roles": "seller",
        "gst.number": {"$exists": True, "$ne": None, "$ne": ""},
        "gst.status": "pending",
        "gst.verified": False
    }
    
    skip = (page - 1) * limit
    total = await db.users.count_documents(query)
    
    users = await db.users.find(query).sort("updatedAt", -1).skip(skip).limit(limit).to_list(length=limit)
    
    results = []
    for user in users:
        gst = user.get("gst", {})
        profile = user.get("profile", {}) or {}
        
        results.append({
            "_id": str(user["_id"]),
            "email": user.get("email", ""),
            "businessName": profile.get("businessName", ""),
            "gstNumber": gst.get("number", ""),
            "gstStatus": gst.get("status", "pending"),
            "gstVerified": gst.get("verified", False),
            "phone": profile.get("phone", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "createdAt": user.get("createdAt", ""),
            "updatedAt": user.get("updatedAt", "")
        })
    
    # Response format matching frontend: setRequests(data.pending_reviews || [])
    response_data = {
        "pending_reviews": results,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }
    logger.info(f"[GST PENDING] total={total}, page={page}, pages={response_data['pages']}, result_count={len(results)}")
    
    return response_data


# ============== ADMIN GST VERIFICATION ENDPOINT ==============

@api_router.patch("/admin/users/{user_id}/verify-gst")
async def admin_verify_gst(
    user_id: str,
    verified: bool = True,
    admin: dict = Depends(require_admin)
):
    """
    Admin endpoint to verify/reject a seller's GST.
    
    UNIFIED GST SCHEMA - SINGLE SOURCE OF TRUTH:
    gst: {
        number: string,
        status: "pending" | "verified" | "rejected",
        verified: boolean
    }
    
    When GST is verified:
    - gst.status = "verified"
    - gst.verified = true
    - All seller's draft listings become active
    
    When GST is rejected:
    - gst.status = "rejected"
    - gst.verified = false
    - Seller can re-submit GST
    """
    try:
        target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is a seller
    roles = target_user.get("roles", [])
    if "seller" not in roles:
        raise HTTPException(status_code=400, detail="User is not a seller")
    
    # Check GST number exists
    gst = target_user.get("gst", {})
    gst_number = gst.get("number")
    if not gst_number:
        raise HTTPException(status_code=400, detail="User has no GST number to verify")
    
    # SSOT: Update only the unified gst schema
    new_status = "verified" if verified else "rejected"
    
    update_data = {
        "gst.status": new_status,
        "gst.verified": verified,
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    listings_published = 0
    
    # If verified, make all seller's draft listings active
    if verified:
        listings_result = await db.sellerListings.update_many(
            {
                "sellerId": ObjectId(user_id),
                "status": {"$in": ["inactive", "draft"]}
            },
            {"$set": {
                "status": "active",
                "publishedAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        listings_published = listings_result.modified_count
        logger.info(f"Admin {admin['email']} verified GST for user {user_id}. Published {listings_published} listings.")
    else:
        logger.info(f"Admin {admin['email']} rejected GST for user {user_id}")
    
    return {
        "message": f"GST {'verified' if verified else 'rejected'} successfully",
        "gst": {
            "number": gst_number,
            "status": new_status,
            "verified": verified
        },
        "listingsPublished": listings_published
    }


# ============== PROFILE UPDATE ENDPOINT ==============

class ProfileUpdateRequest(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

@api_router.patch("/users/me/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    user: dict = Depends(require_auth)
):
    """
    Update user profile - limited to contact details only.
    Business name, email, phone, GST are NOT editable here.
    """
    update_data = {"updatedAt": datetime.now(timezone.utc)}
    
    # Only update provided fields
    if request.address is not None:
        update_data["address"] = request.address
    if request.city is not None:
        if not request.city.strip():
            raise HTTPException(status_code=400, detail="City cannot be empty")
        update_data["city"] = request.city.strip()
    if request.state is not None:
        if not request.state.strip():
            raise HTTPException(status_code=400, detail="State cannot be empty")
        update_data["state"] = request.state.strip()
    if request.pincode is not None:
        update_data["pincode"] = request.pincode.strip()
    
    if len(update_data) == 1:  # Only updated_at
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Profile update failed")
    
    # Return updated user (serialize to handle any ObjectId fields)
    updated_user = await db.users.find_one({"_id": ObjectId(user["_id"])})
    
    return {"message": "Profile updated successfully", "user": serialize_doc(updated_user)}


# ============== EMAIL OTP SYSTEM ==============

import secrets
import hashlib

# OTP Configuration from environment
OTP_LENGTH = int(os.environ.get("OTP_LENGTH", "6"))
OTP_VALIDITY_MINUTES = int(os.environ.get("OTP_VALIDITY_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "3"))

def generate_otp() -> str:
    """Generate a random OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])

def hash_otp(otp: str) -> str:
    """Hash OTP for secure storage"""
    return hashlib.sha256(otp.encode()).hexdigest()

async def send_email_otp(to_email: str, otp: str, purpose: str) -> bool:
    """
    Send OTP via email using Resend.
    
    MIGRATION: Now uses Resend instead of Zoho SMTP.
    Uses asyncio.to_thread() to run blocking SDK in thread pool.
    
    Returns True if sent successfully, False otherwise.
    In MOCK mode (no credentials), returns True and logs OTP.
    """
    from services.email_service import send_email, _get_email_wrapper, _get_button_html
    
    # Define subject and body based on purpose
    subject_map = {
        "verify_current_email": "Verify Your Current Email - Udyog Connect",
        "verify_new_email": "Verify Your New Email - Udyog Connect",
        "verify_mobile_change": "Verify Mobile Number Change - Udyog Connect"
    }
    
    body_html_map = {
        "verify_current_email": f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Verify Your Current Email</h2>
        
        <p>You have requested to change your email address on Udyog Connect.</p>
        
        <p>To verify your current email, please use this OTP:</p>
        
        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #0B3C5D; font-family: monospace;">{otp}</div>
        </div>
        
        <p style="color: #666; font-size: 14px;">This OTP is valid for {OTP_VALIDITY_MINUTES} minutes.</p>
        
        <p style="color: #999; font-size: 12px;">If you did not request this change, please ignore this email or contact support.</p>
        """,
        "verify_new_email": f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Verify Your New Email</h2>
        
        <p>You are updating your email address on Udyog Connect.</p>
        
        <p>To verify your new email address, please use this OTP:</p>
        
        <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #28a745; font-family: monospace;">{otp}</div>
        </div>
        
        <p style="color: #666; font-size: 14px;">This OTP is valid for {OTP_VALIDITY_MINUTES} minutes.</p>
        
        <p style="color: #999; font-size: 12px;">If you did not request this change, please ignore this email.</p>
        """,
        "verify_mobile_change": f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Verify Mobile Number Change</h2>
        
        <p>You have requested to change your mobile number on Udyog Connect.</p>
        
        <p>To verify this change, please use this OTP:</p>
        
        <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #f59e0b; font-family: monospace;">{otp}</div>
        </div>
        
        <p style="color: #666; font-size: 14px;">This OTP is valid for {OTP_VALIDITY_MINUTES} minutes.</p>
        
        <p style="color: #ef4444; font-size: 12px;">If you did not request this change, please secure your account immediately.</p>
        """
    }
    
    subject = subject_map.get(purpose, f"Your OTP - Udyog Connect")
    body_html = body_html_map.get(purpose, f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Your OTP Code</h2>
        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #0B3C5D; font-family: monospace;">{otp}</div>
        </div>
        <p style="color: #666; font-size: 14px;">Valid for {OTP_VALIDITY_MINUTES} minutes.</p>
    """)
    
    html_content = _get_email_wrapper(body_html, subject)
    
    result = await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content
    )
    
    if result.get("success"):
        logger.info(f"OTP email sent to {to_email} for {purpose}")
        return True
    else:
        logger.error(f"Failed to send OTP email to {to_email}: {result.get('error')}")
        return False

# OTP Request Models
class RequestEmailChangeStep1(BaseModel):
    """Step 1: Request OTP for current email verification"""
    model_config = {"populate_by_name": True}

class VerifyEmailChangeStep1(BaseModel):
    """Step 1: Verify current email OTP"""
    otp: str
    model_config = {"populate_by_name": True}

class RequestEmailChangeStep2(BaseModel):
    """Step 2: Request OTP for new email verification"""
    newEmail: str
    model_config = {"populate_by_name": True}

class VerifyEmailChangeStep2(BaseModel):
    """Step 2: Verify new email OTP and complete change"""
    newEmail: str
    otp: str
    model_config = {"populate_by_name": True}

class RequestMobileChange(BaseModel):
    """Request OTP for mobile change"""
    newMobile: str
    model_config = {"populate_by_name": True}

class VerifyMobileChange(BaseModel):
    """Verify OTP and complete mobile change"""
    newMobile: str
    otp: str
    model_config = {"populate_by_name": True}

# ============== EMAIL CHANGE ENDPOINTS (Two-Step) ==============

@api_router.post("/users/me/email-change/request-step1")
@limiter.limit("3/minute")
async def request_email_change_step1(request: Request, user: dict = Depends(require_auth)):
    """
    Step 1: Send OTP to current registered email
    """
    current_email = user.get("email")
    if not current_email:
        raise HTTPException(status_code=400, detail="No email associated with this account")
    
    # Check for existing pending request
    existing = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "email_change_step1",
        "verified": False,
        "expiresAt": {"$gt": datetime.now(timezone.utc)}
    })
    
    if existing:
        # Check if we can resend (rate limiting)
        if existing.get("last_sent_at"):
            time_since_last = datetime.now(timezone.utc) - existing["last_sent_at"]
            if time_since_last.total_seconds() < 60:
                raise HTTPException(
                    status_code=429, 
                    detail="Please wait 60 seconds before requesting another OTP"
                )
    
    # Generate OTP
    otp = generate_otp()
    otp_hash = hash_otp(otp)
    
    # Send OTP
    sent = await send_email_otp(current_email, otp, "verify_current_email")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP. Please try again.")
    
    # Store OTP request
    await db.otp_requests.update_one(
        {"user_id": ObjectId(user["_id"]), "purpose": "email_change_step1"},
        {"$set": {
            "user_id": ObjectId(user["_id"]),
            "purpose": "email_change_step1",
            "otpHash": otp_hash,
            "attempts": 0,
            "verified": False,
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES),
            "last_sent_at": datetime.now(timezone.utc),
            "createdAt": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Mask email for display
    masked_email = current_email[:3] + "***" + current_email[current_email.index("@"):]
    
    return {
        "message": f"OTP sent to your registered email ({masked_email})",
        "expires_in_minutes": OTP_VALIDITY_MINUTES
    }

@api_router.post("/users/me/email-change/verify-step1")
async def verify_email_change_step1(
    request: VerifyEmailChangeStep1,
    user: dict = Depends(require_auth)
):
    """
    Step 1: Verify OTP sent to current email
    """
    otp_request = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "email_change_step1",
        "verified": False
    })
    
    if not otp_request:
        raise HTTPException(status_code=400, detail="No pending verification. Please request OTP first.")
    
    # Check expiry - use make_timezone_aware for MongoDB dates
    expires_at = make_timezone_aware(otp_request["expiresAt"])
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Check attempts
    if otp_request["attempts"] >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Maximum attempts exceeded. Please request a new OTP.")
    
    # Verify OTP
    if hash_otp(request.otp) != otp_request["otpHash"]:
        await db.otp_requests.update_one(
            {"_id": otp_request["_id"]},
            {"$inc": {"attempts": 1}}
        )
        remaining = OTP_MAX_ATTEMPTS - otp_request["attempts"] - 1
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )
    
    # Mark as verified
    await db.otp_requests.update_one(
        {"_id": otp_request["_id"]},
        {"$set": {
            "verified": True,
            "verifiedAt": datetime.now(timezone.utc)
        }}
    )
    
    return {"message": "Current email verified successfully. You can now proceed to enter your new email."}

@api_router.post("/users/me/email-change/request-step2")
async def request_email_change_step2(
    request: RequestEmailChangeStep2,
    user: dict = Depends(require_auth)
):
    """
    Step 2: Send OTP to new email (requires Step 1 completion)
    """
    # Verify Step 1 was completed
    step1 = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "email_change_step1",
        "verified": True,
        "verifiedAt": {"$gt": datetime.now(timezone.utc) - timedelta(minutes=30)}  # Step 1 valid for 30 min
    })
    
    if not step1:
        raise HTTPException(
            status_code=400, 
            detail="Please complete Step 1 (verify current email) first."
        )
    
    new_email = request.newEmail.lower().strip()
    
    # Validate email format
    if "@" not in new_email or "." not in new_email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": new_email})
    if existing_user:
        raise HTTPException(status_code=400, detail="This email is already registered")
    
    # Check if same as current
    if new_email == user.get("email", "").lower():
        raise HTTPException(status_code=400, detail="New email must be different from current email")
    
    # Rate limiting
    existing = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "email_change_step2",
        "newEmail": new_email,
        "verified": False
    })
    
    if existing and existing.get("last_sent_at"):
        time_since_last = datetime.now(timezone.utc) - existing["last_sent_at"]
        if time_since_last.total_seconds() < 60:
            raise HTTPException(
                status_code=429, 
                detail="Please wait 60 seconds before requesting another OTP"
            )
    
    # Generate OTP
    otp = generate_otp()
    otp_hash = hash_otp(otp)
    
    # Send OTP to NEW email
    sent = await send_email_otp(new_email, otp, "verify_new_email")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP. Please try again.")
    
    # Store OTP request
    await db.otp_requests.update_one(
        {"user_id": ObjectId(user["_id"]), "purpose": "email_change_step2"},
        {"$set": {
            "user_id": ObjectId(user["_id"]),
            "purpose": "email_change_step2",
            "newEmail": new_email,
            "otpHash": otp_hash,
            "attempts": 0,
            "verified": False,
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES),
            "last_sent_at": datetime.now(timezone.utc),
            "createdAt": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Mask email for display
    masked_email = new_email[:3] + "***" + new_email[new_email.index("@"):]
    
    return {
        "message": f"OTP sent to your new email ({masked_email})",
        "expires_in_minutes": OTP_VALIDITY_MINUTES
    }

@api_router.post("/users/me/email-change/verify-step2")
async def verify_email_change_step2(
    request: VerifyEmailChangeStep2,
    user: dict = Depends(require_auth)
):
    """
    Step 2: Verify OTP and complete email change
    """
    new_email = request.newEmail.lower().strip()
    
    otp_request = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "email_change_step2",
        "newEmail": new_email,
        "verified": False
    })
    
    if not otp_request:
        raise HTTPException(status_code=400, detail="No pending verification for this email.")
    
    # Check expiry - use make_timezone_aware for MongoDB dates
    expires_at = make_timezone_aware(otp_request["expiresAt"])
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Check attempts
    if otp_request["attempts"] >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Maximum attempts exceeded. Please request a new OTP.")
    
    # Verify OTP
    if hash_otp(request.otp) != otp_request["otpHash"]:
        await db.otp_requests.update_one(
            {"_id": otp_request["_id"]},
            {"$inc": {"attempts": 1}}
        )
        remaining = OTP_MAX_ATTEMPTS - otp_request["attempts"] - 1
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )
    
    # Double-check email not taken
    existing_user = await db.users.find_one({"email": new_email})
    if existing_user:
        raise HTTPException(status_code=400, detail="This email is already registered")
    
    # Update user email
    old_email = user.get("email")
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {
            "email": new_email,
            "emailVerified": True,  # New email is now verified
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    # Clean up OTP requests
    await db.otp_requests.delete_many({
        "user_id": ObjectId(user["_id"]),
        "purpose": {"$in": ["email_change_step1", "email_change_step2"]}
    })
    
    logger.info(f"Email changed for user {user['_id']}: {old_email} -> {new_email}")
    
    return {
        "message": "Email updated successfully",
        "newEmail": new_email,
        "requiresRelogin": True
    }

# ============== MOBILE CHANGE ENDPOINTS (Single-Step) ==============

@api_router.post("/users/me/mobile-change/request")
async def request_mobile_change(
    request: RequestMobileChange,
    user: dict = Depends(require_auth)
):
    """
    Request OTP for mobile number change (sent to registered email)
    """
    current_email = user.get("email")
    if not current_email:
        raise HTTPException(status_code=400, detail="No email associated with this account")
    
    new_mobile = request.newMobile.strip()
    
    # Basic validation
    if len(new_mobile) < 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number format")
    
    # Check if same as current
    if new_mobile == user.get("phone", ""):
        raise HTTPException(status_code=400, detail="New mobile must be different from current mobile")
    
    # Check for existing pending request with rate limiting
    existing = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "mobile_change",
        "verified": False
    })
    
    if existing and existing.get("last_sent_at"):
        time_since_last = datetime.now(timezone.utc) - existing["last_sent_at"]
        if time_since_last.total_seconds() < 60:
            raise HTTPException(
                status_code=429, 
                detail="Please wait 60 seconds before requesting another OTP"
            )
    
    # Generate OTP
    otp = generate_otp()
    otp_hash = hash_otp(otp)
    
    # Send OTP to REGISTERED EMAIL (not mobile)
    sent = await send_email_otp(current_email, otp, "verify_mobile_change")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP. Please try again.")
    
    # Store OTP request
    await db.otp_requests.update_one(
        {"user_id": ObjectId(user["_id"]), "purpose": "mobile_change"},
        {"$set": {
            "user_id": ObjectId(user["_id"]),
            "purpose": "mobile_change",
            "newMobile": new_mobile,
            "otpHash": otp_hash,
            "attempts": 0,
            "verified": False,
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES),
            "last_sent_at": datetime.now(timezone.utc),
            "createdAt": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Mask email for display
    masked_email = current_email[:3] + "***" + current_email[current_email.index("@"):]
    
    return {
        "message": f"OTP sent to your registered email ({masked_email})",
        "expires_in_minutes": OTP_VALIDITY_MINUTES
    }

@api_router.post("/users/me/mobile-change/verify")
async def verify_mobile_change(
    request: VerifyMobileChange,
    user: dict = Depends(require_auth)
):
    """
    Verify OTP and complete mobile number change
    """
    new_mobile = request.newMobile.strip()
    
    otp_request = await db.otp_requests.find_one({
        "user_id": ObjectId(user["_id"]),
        "purpose": "mobile_change",
        "newMobile": new_mobile,
        "verified": False
    })
    
    if not otp_request:
        raise HTTPException(status_code=400, detail="No pending verification for this mobile number.")
    
    # Check expiry - use make_timezone_aware for MongoDB dates
    expires_at = make_timezone_aware(otp_request["expiresAt"])
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Check attempts
    if otp_request["attempts"] >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Maximum attempts exceeded. Please request a new OTP.")
    
    # Verify OTP
    if hash_otp(request.otp) != otp_request["otpHash"]:
        await db.otp_requests.update_one(
            {"_id": otp_request["_id"]},
            {"$inc": {"attempts": 1}}
        )
        remaining = OTP_MAX_ATTEMPTS - otp_request["attempts"] - 1
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )
    
    # Update user mobile
    old_mobile = user.get("phone")
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {
            "phone": new_mobile,
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    # Clean up OTP request
    await db.otp_requests.delete_one({"_id": otp_request["_id"]})
    
    logger.info(f"Mobile changed for user {user['_id']}: {old_mobile} -> {new_mobile}")
    
    return {
        "message": "Mobile number updated successfully",
        "newMobile": new_mobile
    }



# ============== ACCOUNT DELETION ENDPOINTS ==============

class DeleteAccountRequest(BaseModel):
    reason: Optional[str] = None
    confirmation: bool = False

@api_router.post("/users/me/delete")
async def delete_account(
    request: DeleteAccountRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Soft delete user account (Safe Delete)
    - Account is disabled but data is preserved
    - User cannot login
    - Listings are unpublished
    - Reversible for 30 days
    """
    # Check if credentials are provided
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get user directly without deleted check
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        firebaseUid = decoded_token['uid']
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    user = await db.users.find_one({"firebaseUid": firebaseUid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not request.confirmation:
        raise HTTPException(status_code=400, detail="Please confirm account deletion")
    
    # Check if already deleted
    if user.get("accountStatus") == "deleted":
        raise HTTPException(status_code=400, detail="Account is already deactivated")
    
    # Check if seller has active confirmed deals
    if user.get("isSeller"):
        active_deals = await db.inquiries.count_documents({
            "sellerId": ObjectId(user["_id"]),
            "status": "confirmed",
            "createdAt": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
        })
        if active_deals > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete account: You have {active_deals} active confirmed deal(s). Please resolve them first."
            )
    
    # Soft delete the account
    deletion_data = {
        "accountStatus": "deleted",
        "isActive": False,
        "canLogin": False,
        "deletedAt": datetime.now(timezone.utc),
        "deletionReason": request.reason,
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": deletion_data}
    )
    
    # If seller, unpublish all listings
    # SSOT: Use seller_listings with sellerId (ObjectId) and status field
    if user.get("isSeller"):
        await db.sellerListings.update_many(
            {"sellerId": ObjectId(user["_id"]), "status": "active"},
            {"$set": {
                "status": "inactive",
                "unpublishedReason": "account_deleted",
                "unpublishedAt": datetime.now(timezone.utc)
            }}
        )
    
    logger.info(f"Account soft-deleted: user_id={user['_id']}, email={user.get('email')}")
    
    return {
        "message": "Account deactivated successfully",
        "can_restore_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "note": "Your account will be fully deactivated after 30 days. You can restore it by logging in within this period."
    }

@api_router.post("/users/me/restore")
async def restore_account(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Restore a soft-deleted account within 30-day grace period
    """
    # Check if credentials are provided
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        firebaseUid = decoded_token['uid']
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    user = await db.users.find_one({"firebaseUid": firebaseUid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if user.get("accountStatus") != "deleted":
        raise HTTPException(status_code=400, detail="Account is not deactivated")
    
    deleted_at = user.get("deletedAt")
    if not deleted_at:
        raise HTTPException(status_code=400, detail="Cannot restore account - invalid state")
    
    # Check grace period
    grace_period_end = deleted_at + timedelta(days=30)
    if datetime.now(timezone.utc) > grace_period_end:
        raise HTTPException(
            status_code=400, 
            detail="Grace period has expired. Account cannot be restored."
        )
    
    # Restore the account
    restore_data = {
        "accountStatus": "active",
        "isActive": True,
        "canLogin": True,
        "deletedAt": None,
        "deletionReason": None,
        "restoredAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": restore_data}
    )
    
    # Republish listings that were unpublished due to deletion
    # SSOT: Use seller_listings with sellerId (ObjectId)
    if user.get("isSeller"):
        await db.sellerListings.update_many(
            {
                "sellerId": ObjectId(user["_id"]),
                "unpublishedReason": "account_deleted"
            },
            {"$set": {
                "status": "active",
                "unpublishedReason": None,
                "unpublishedAt": None,
                "republishedAt": datetime.now(timezone.utc)
            }}
        )
    
    logger.info(f"Account restored: user_id={user['_id']}, email={user.get('email')}")
    
    return {
        "message": "Account restored successfully",
        "status": "active"
    }

# ============== ADMIN - DELETED ACCOUNTS MANAGEMENT ==============

@api_router.get("/admin/deleted-accounts")
async def get_deleted_accounts(admin: dict = Depends(require_admin)):
    """Get list of deleted accounts (admin only)"""
    pipeline = [
        {"$match": {"accountStatus": {"$in": ["deleted", "archived"]}}},
        {"$project": {
            "_id": 1,
            "email": 1,
            "businessName": 1,
            "phone": 1,
            "city": 1,
            "state": 1,
            "isSeller": 1,
            "gstNumber": 1,
            "gstStatus": 1,
            "accountStatus": 1,
            "deletedAt": 1,
            "deletionReason": 1,
            "createdAt": 1,
            "grace_period_remaining": {
                "$cond": {
                    "if": {"$and": [
                        {"$eq": ["$accountStatus", "deleted"]},
                        {"$ne": ["$deletedAt", None]}
                    ]},
                    "then": {
                        "$subtract": [
                            {"$add": ["$deletedAt", 30 * 24 * 60 * 60 * 1000]},  # 30 days in ms
                            "$$NOW"
                        ]
                    },
                    "else": 0
                }
            }
        }},
        {"$sort": {"deletedAt": -1}}
    ]
    
    accounts = await db.users.aggregate(pipeline).to_list(100)
    
    # Process and add computed fields
    for account in accounts:
        deleted_at = account.get("deletedAt")
        if deleted_at and account.get("accountStatus") == "deleted":
            grace_end = deleted_at + timedelta(days=30)
            account["can_restore"] = datetime.now(timezone.utc) < grace_end
            account["grace_expires_at"] = grace_end.isoformat()
        else:
            account["can_restore"] = False
            account["grace_expires_at"] = None
    
    return serialize_doc(accounts)

@api_router.post("/admin/deleted-accounts/{user_id}/restore")
async def admin_restore_deleted_account(user_id: str, admin: dict = Depends(require_admin)):
    """Admin restores a deleted account"""
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("accountStatus") not in ["deleted", "archived"]:
        raise HTTPException(status_code=400, detail="Account is not deactivated")
    
    # Restore the account
    restore_data = {
        "accountStatus": "active",
        "isActive": True,
        "canLogin": True,
        "deletedAt": None,
        "deletionReason": None,
        "restoredAt": datetime.now(timezone.utc),
        "restoredBy": str(admin["_id"]),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": restore_data}
    )
    
    # Republish listings - SSOT: sellerId is ObjectId in seller_listings
    await db.sellerListings.update_many(
        {"sellerId": ObjectId(user_id), "unpublishedReason": "account_deleted"},
        {"$set": {
            "status": "active",
            "unpublishedReason": None,
            "unpublishedAt": None,
            "republishedAt": datetime.now(timezone.utc)
        }}
    )
    
    logger.info(f"Admin {admin['email']} restored account: user_id={user_id}")
    
    return {"message": "Account restored by admin", "status": "active"}

@api_router.post("/admin/deleted-accounts/{user_id}/archive")
async def admin_archive_deleted_account(user_id: str, admin: dict = Depends(require_admin)):
    """Admin permanently archives an account (manual only, no auto-delete)"""
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("accountStatus") != "deleted":
        raise HTTPException(status_code=400, detail="Only deleted accounts can be archived")
    
    # Archive the account (still soft, never hard delete)
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "accountStatus": "archived",
            "archivedAt": datetime.now(timezone.utc),
            "archivedBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    logger.info(f"Admin {admin['email']} archived account: user_id={user_id}")
    
    return {"message": "Account archived permanently", "status": "archived"}

# ============== CATEGORY ENDPOINTS ==============

@api_router.get("/categories")
async def get_categories():
    """Get all categories with at least 1 active listing"""
    # Get categories that have at least one published listing
    # SSOT: Use isActive (camelCase)
    pipeline = [
        {"$match": {"isActive": True}},
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "categoryId",
            "as": "products"
        }},
        {"$lookup": {
            "from": "sellerListings",
            "let": {"product_ids": "$products._id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$in": ["$productId", "$$product_ids"]},
                    "status": "active"
                }}
            ],
            "as": "listings"
        }},
        {"$match": {"$expr": {"$gt": [{"$size": "$listings"}, 0]}}},
        {"$project": {
            "_id": 1,
            "name": 1,
            "description": 1,
            "icon": 1,
            "image": 1,  # Include category image
            "listingCount": {"$size": "$listings"}
        }}
    ]
    
    categories = await db.categories.aggregate(pipeline).to_list(100)
    return serialize_doc(categories)

@api_router.get("/categories/all")
async def get_all_categories():
    """Get all categories (for admin/vendor listing creation)"""
    # Categories must be active AND not soft-deleted
    # SSOT: Use isActive (camelCase) - exclude if False
    categories = await db.categories.find({
        "isActive": {"$ne": False}
    }).sort("name", 1).to_list(100)  # Sort by name ascending
    
    # Normalize field names for frontend compatibility
    result = []
    for cat in categories:
        serialized = serialize_mongo_doc(cat)
        serialized['isActive'] = True  # Only active categories reach here
        result.append(serialized)
    return result


@api_router.get("/categories/public")
async def get_public_categories():
    """
    Get categories that have at least 1 ACTIVE seller listing.
    Seller-listing-driven visibility - empty categories are hidden from public.
    
    FLEXIBLE: Supports both:
    1. Canonical flow (listing -> product -> category)
    2. Direct flow (listing -> category, when product catalog not used)
    """
    # Debug logging
    total_listings = await db.sellerListings.count_documents({})
    active_listings = await db.sellerListings.count_documents({
        "$or": [
            {"status": "active"},
            {"status": "Active"},
            {"status": {"$regex": "^active$", "$options": "i"}}
        ],
        "$or": [
            {"isActive": True},
            {"isActive": {"$exists": False}}
        ]
    })
    logger.info(f"[Public Categories] Total listings: {total_listings}, Active: {active_listings}")
    
    # Get categories with active seller listings
    # FLEXIBLE: Support both product-linked and direct-category listings
    pipeline = [
        # Stage 1: Only active listings - case-insensitive
        {"$match": {
            "$and": [
                {"$or": [
                    {"status": "active"},
                    {"status": "Active"},
                    {"status": {"$regex": "^active$", "$options": "i"}}
                ]},
                {"$or": [
                    {"isActive": True},
                    {"isActive": {"$exists": False}}
                ]},
                {"$or": [
                    {"isDeleted": False},
                    {"isDeleted": {"$exists": False}}
                ]}
            ]
        }},
        # Stage 2: Group by productId to count listings per product
        {"$group": {
            "_id": "$productId",
            "listingCount": {"$sum": 1},
            "listingCategoryId": {"$first": "$categoryId"},      # Capture listing's direct categoryId
            "listingCategoryName": {"$first": "$categoryName"}   # Capture listing's categoryName
        }},
        # Stage 3: Lookup product to get canonical categoryId - ONLY ACTIVE PRODUCTS
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "_id",
            "as": "product",
            "pipeline": [
                {"$match": {
                    "$and": [
                        {"$or": [
                            {"isActive": True},
                            {"isActive": {"$exists": False}}
                        ]},
                        {"$or": [
                            {"isDeleted": {"$ne": True}},
                            {"isDeleted": {"$exists": False}}
                        ]}
                    ]
                }}
            ]
        }},
        # FILTER OUT products that are deleted/inactive
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": False}},
        # Stage 4: Determine categoryId - prefer product.categoryId, fallback to listing's
        {"$addFields": {
            "resolvedCategoryId": {
                "$ifNull": ["$product.categoryId", "$listingCategoryId"]
            }
        }},
        # Stage 5: Group by resolved categoryId
        {"$group": {
            "_id": "$resolvedCategoryId",
            "productCount": {"$sum": 1},
            "totalListings": {"$sum": "$listingCount"},
            "fallbackCategoryName": {"$first": "$listingCategoryName"}
        }},
        # Stage 6: Filter out null categories
        {"$match": {"_id": {"$ne": None}}},
        # Stage 7: Lookup category details
        {"$lookup": {
            "from": "categories",
            "localField": "_id",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        {"$match": {"productCount": {"$gt": 0}}},
        {"$sort": {"category.name": 1, "fallbackCategoryName": 1}}
    ]
    
    categories_raw = await db.sellerListings.aggregate(pipeline).to_list(100)
    
    # Transform results - ensure category_id is string
    categories = []
    for c in categories_raw:
        cat_id = c["_id"]
        if isinstance(cat_id, ObjectId):
            cat_id = str(cat_id)
        
        category = c.get("category", {})
        cat_name = category.get("name") if category else c.get("fallbackCategoryName")
        
        categories.append({
            "_id": cat_id,
            "name": cat_name,
            "image": category.get("image") if category else None,
            "icon": category.get("icon") if category else None,
            "productCount": c.get("productCount", 0),
            "listingCount": c.get("totalListings", 0)
        })
    
    # Debug logging
    logger.info(f"[Public Categories] Found {len(categories)} categories with active sellers")
    for c in categories[:5]:
        logger.info(f"  - {c.get('name')}: {c.get('productCount')} products, {c.get('listingCount')} listings")
    
    return categories

# ============== PRODUCT ENDPOINTS ==============

@api_router.post("/admin/products/legacy")
async def create_product_legacy(product: ProductCreate):
    """
    DEPRECATED: Legacy product creation endpoint.
    Use POST /admin/products with AdminProductCreate model instead.
    This endpoint is kept for backward compatibility only.
    """
    # Initialize identity service
    identity_service = ProductIdentityService(db)
    
    # Verify category exists
    category = await db.categories.find_one({"_id": ObjectId(product.category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Build specs from spec_schema for identity hash
    spec_fields = {}
    if product.spec_schema:
        for spec in product.spec_schema:
            key = spec.key if spec.key else spec.name
            spec_fields[key] = ""  # Empty placeholder
    
    # Check for duplicate using identity signature
    spec_hash = identity_service.generate_spec_hash(spec_fields)
    normalized_specs = identity_service.normalize_specifications(spec_fields)
    
    existing_product = await identity_service.find_existing_product(
        name=product.name,
        category_id=product.category_id,
        spec_template_id=None,
        specifications=spec_fields
    )
    
    if existing_product:
        logger.info(f"[Legacy] Product identity match found: {existing_product['_id']} for {product.name}")
        return {
            "message": "Product with this identity already exists",
            "product": existing_product,
            "isExisting": True,
            **existing_product  # Include product fields at root for backward compatibility
        }
    
    # Convert spec_schema to dict format for storage
    spec_schema_dicts = [spec.dict() for spec in product.spec_schema] if product.spec_schema else []
    
    from datetime import timezone as tz
    now = datetime.now(tz.utc)
    
    prod_doc = {
        "_id": ObjectId(),
        "categoryId": ObjectId(product.category_id),
        "family": product.family,
        "variant": product.variant,
        "name": product.name,
        "description": product.description,
        "unit": product.unit,
        "standardParameters": product.standard_parameters,  # Legacy
        "specSchema": spec_schema_dicts,  # New locked technical specs
        # Product Identity Governance fields
        "normalized_spec_hash": spec_hash,
        "normalizedSpecs": normalized_specs,
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
        "active": True
    }
    
    try:
        await db.products.insert_one(prod_doc)
        logger.info(f"[Legacy] Created product: {product.name} (hash: {spec_hash[:8]}...)")
        return serialize_doc(prod_doc)
    except Exception as e:
        if "duplicate key error" in str(e).lower() or "E11000" in str(e):
            existing = await identity_service.find_existing_product(
                name=product.name,
                category_id=product.category_id,
                spec_template_id=None,
                specifications=spec_fields
            )
            if existing:
                return existing
        raise

@api_router.get("/products")
async def get_products(
    category_id: Optional[str] = Query(None, alias="categoryId"),  # Support both snake_case and camelCase
):
    """
    Get products that have at least 1 ACTIVE/PUBLISHED seller listing.
    Seller-listing-driven visibility - catalog products without listings are hidden.
    
    PRODUCT IDENTITY GOVERNANCE:
    - Groups by productId (canonical product reference)
    - Shows single card per product with:
      - Seller count (number of unique sellers)
      - Lowest starting price (from all pricingTiers)
    - Joins with products collection for canonical product info
    """
    # Debug: Log total listings before filter
    total_listings = await db.sellerListings.count_documents({})
    active_listings = await db.sellerListings.count_documents({"status": "active", "isActive": True})
    logger.info(f"[Products API] Total listings: {total_listings}, Active: {active_listings}")
    
    # FALLBACK: If no products found via canonical pipeline, try direct listing display
    # This handles cases where seller created listings without proper product catalog entries
    
    # Build aggregation pipeline - CANONICAL SSOT: ObjectId-only joins
    # Start from seller_listings, group by productId, join with products
    pipeline = [
        # Stage 1: Only ACTIVE listings - case-insensitive status check
        {"$match": {
            "$and": [
                # Status check - handle both lowercase and potential variations
                {"$or": [
                    {"status": "active"},
                    {"status": "Active"},
                    {"status": {"$regex": "^active$", "$options": "i"}}
                ]},
                # isActive must be true OR not exist (default to active)
                {"$or": [
                    {"isActive": True},
                    {"isActive": {"$exists": False}}
                ]},
                # isDeleted must be false OR not exist
                {"$or": [
                    {"isDeleted": False},
                    {"isDeleted": {"$exists": False}}
                ]}
            ]
        }},
        # Stage 2: Group by productId (MUST be ObjectId - no fallbacks)
        {"$group": {
            "_id": "$productId",  # CANONICAL: No fallback to legacy fields
            "seller_ids": {"$addToSet": "$sellerId"},
            "allPrices": {"$push": "$pricingTiers"},
            "firstDescription": {"$first": "$description"},
            "firstImages": {"$first": "$images"},
            "firstProductName": {"$first": "$productName"},  # Capture listing's productName
            "firstCategoryId": {"$first": "$categoryId"},    # Capture listing's categoryId
            "firstCategoryName": {"$first": "$categoryName"} # Capture listing's categoryName
        }},
        # Stage 3: Lookup product info from products collection
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "_id",
            "as": "product_info"
        }},
        # Stage 4: Unwind product info - ALLOW MISSING to support listing-first workflow
        {"$unwind": {
            "path": "$product_info",
            "preserveNullAndEmptyArrays": True  # FLEXIBLE: Show listings even without catalog entry
        }},
        # Stage 5: Lookup category from categories collection
        {"$lookup": {
            "from": "categories",
            "localField": "product_info.categoryId",
            "foreignField": "_id",
            "as": "category_info"
        }},
        # Stage 5b: Also try to lookup category from listing's categoryId
        {"$lookup": {
            "from": "categories",
            "localField": "firstCategoryId",
            "foreignField": "_id",
            "as": "listing_category_info"
        }},
        # Stage 6: Unwind category info
        {"$unwind": {
            "path": "$category_info",
            "preserveNullAndEmptyArrays": True
        }},
        {"$unwind": {
            "path": "$listing_category_info",
            "preserveNullAndEmptyArrays": True
        }},
    ]
    
    # Stage 7: Filter by category if requested
    if category_id:
        pipeline.append({
            "$match": {"product_info.categoryId": ObjectId(category_id)}
        })
    
    # Stage 8: Project final shape - USE LISTING DATA AS FALLBACK
    pipeline.append({
        "$project": {
            "_id": {"$toString": "$_id"},
            # Name: prefer product catalog, fallback to listing's productName
            "name": {"$ifNull": ["$product_info.name", "$firstProductName"]},
            "slug": "$product_info.slug",
            "description": {"$ifNull": ["$product_info.description", "$firstDescription"]},
            # CategoryId: prefer product catalog, fallback to listing's categoryId
            "categoryId": {
                "$toString": {
                    "$ifNull": ["$product_info.categoryId", "$firstCategoryId"]
                }
            },
            # CategoryName: prefer product's category, fallback to listing's category
            "categoryName": {"$ifNull": ["$category_info.name", "$listing_category_info.name", "$firstCategoryName"]},
            "images": {"$ifNull": ["$product_info.images", "$firstImages"]},
            "sellerCount": {"$size": "$seller_ids"},
            "minPrice": {
                "$min": {
                    "$reduce": {
                        "input": "$allPrices",  # FIXED: was all_prices
                        "initialValue": [],
                        "in": {
                            "$concatArrays": [
                                "$$value",
                                {"$map": {
                                    "input": {"$ifNull": ["$$this", []]},
                                    "as": "tier",
                                    "in": {"$ifNull": ["$$tier.pricePerUnit", "$$tier.price_per_unit"]}
                                }}
                            ]
                        }
                    }
                }
            },
            "normalizedSpecHash": "$product_info.normalizedSpecHash"
        }
    })
    
    # Filter out products with null names
    pipeline.append({
        "$match": {
            "name": {"$ne": None, "$ne": ""}
        }
    })
    
    # Stage 7: Sort by seller count (most popular first)
    pipeline.append({"$sort": {"sellerCount": -1, "name": 1}})
    
    # Stage 8: Limit results
    pipeline.append({"$limit": 500})
    
    try:
        # Debug: Count listings after filter (STRICT: status = "active" only)
        filter_stage = {
            "$and": [
                {"status": "active"},  # STRICT: Only "active" status is public
                {"$or": [
                    {"isActive": True},
                    {"isActive": {"$exists": False}}
                ]},
                {"$or": [
                    {"isDeleted": False},
                    {"isDeleted": {"$exists": False}}
                ]}
            ]
        }
        filtered_count = await db.sellerListings.count_documents(filter_stage)
        logger.info(f"[Products API] Listings after filter: {filtered_count}")
        
        products_raw = await db.sellerListings.aggregate(pipeline).to_list(500)
        logger.info(f"[Products API] Raw aggregation results: {len(products_raw)}")
    except Exception as e:
        logger.error(f"[Products API] Aggregation error: {e}", exc_info=True)
        products_raw = []
    
    # Transform results for frontend compatibility
    products = []
    for p in products_raw:
        product_id = p.get("_id")
        if not product_id:
            continue
        
        products.append({
            "_id": product_id,
            "name": p.get("name"),
            "slug": p.get("slug"),  # SEO-friendly URL identifier
            "description": p.get("description"),
            "categoryId": p.get("categoryId"),
            "categoryName": p.get("categoryName"),
            "images": p.get("images", []),
            "sellerCount": p.get("sellerCount", 0),
            "minPrice": p.get("minPrice")
        })
    
    # Debug logging
    logger.info(f"[Products API] Final products count: {len(products)}")
    
    # ENTERPRISE STANDARD: Return flat array (not wrapped)
    return products


# ============== SELLER PRODUCT CREATION (PROTECTED) ==============
# DEPRECATED: This endpoint allows sellers to create products directly.
# The correct architecture is:
# 1. Admin creates product TEMPLATE via POST /api/admin/products
# 2. Seller creates LISTING via POST /api/listings (with productId, images, pricingTiers)
# This endpoint is kept for backwards compatibility but should NOT be used for new features.

@api_router.post("/products")
async def create_product(
    product: SellerProductCreate,
    current_user: dict = Depends(require_verified_seller)
):
    """
    ⚠️ DEPRECATED: Use POST /api/listings instead.
    
    Create a new product (seller only).
    
    ARCHITECTURAL NOTE:
    - This endpoint is DEPRECATED. Products should be created by ADMIN only.
    - Sellers should create LISTINGS for existing products, not new products.
    - Use POST /api/listings with productId, images, and pricingTiers.
    
    SECURITY ENFORCEMENT:
    - Requires authenticated user with seller role
    - sellerId is ALWAYS taken from current_user (never from request body)
    - Request body with seller_id field will be REJECTED (extra="forbid")
    - Only users with isSeller=True can access this endpoint
    
    Returns:
        201: Product created successfully with product ID
        400: Validation error (invalid data)
        403: User is not a seller
        409: Duplicate product for this seller
    """
    from datetime import timezone
    from utils.identity import require_objectid
    
    # === IDENTITY GUARD: Validate category_id ===
    try:
        category_oid = require_objectid(product.category_id, "category_id")
    except HTTPException:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_CATEGORY_ID",
                "message": "Invalid category_id format. Must be 24-character hex string."
            }
        )
    
    # === Verify category exists and is active ===
    # SSOT: Use isActive (camelCase)
    category = await db.categories.find_one({"_id": category_oid, "isActive": {"$ne": False}})
    if not category:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "CATEGORY_NOT_FOUND",
                "message": f"Category {product.category_id} not found or is inactive."
            }
        )
    
    # === CRITICAL: Get sellerId from authenticated user ONLY ===
    # NEVER trust seller_id from request body
    seller_id = current_user.get("_id")
    if not seller_id:
        logger.error("[Products API] Authenticated user missing _id")
        raise HTTPException(status_code=500, detail="User identity error")
    
    seller_oid = ObjectId(seller_id) if isinstance(seller_id, str) else seller_id
    
    # === Check for duplicate product name for this seller ===
    # SSOT: Use isActive (camelCase)
    existing_product = await db.products.find_one({
        "name": {"$regex": f"^{re.escape(product.name)}$", "$options": "i"},
        "sellerId": seller_oid,
        "isActive": {"$ne": False}
    })
    
    if existing_product:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "DUPLICATE_PRODUCT",
                "message": f"You already have a product named '{product.name}'."
            }
        )
    
    # === Generate slug ===
    base_slug = re.sub(r'[^a-z0-9]+', '-', product.name.lower()).strip('-')
    slug = base_slug
    
    # Ensure slug uniqueness
    slug_counter = 1
    while await db.products.find_one({"slug": slug}):
        slug = f"{base_slug}-{slug_counter}"
        slug_counter += 1
    
    # === Build product document with CANONICAL schema ===
    now = datetime.now(timezone.utc)
    
    product_doc = {
        "_id": ObjectId(),
        "name": product.name,
        "slug": slug,
        "family": product.family,
        "variant": product.variant,
        "description": product.description,
        "categoryId": category_oid,
        "sellerId": seller_oid,  # CANONICAL: From authenticated user ONLY
        "unit": product.unit,
        "price": product.price,
        "stock": product.stock,
        "moq": product.moq,
        "images": product.images[:10],  # Max 10 images
        "specifications": product.specifications,
        "status": "active",
        "isActive": True,  # SSOT: camelCase
        "createdAt": now,
        "updatedAt": now,
        "createdBy": seller_oid,  # Audit trail
    }
    
    try:
        result = await db.products.insert_one(product_doc)
        product_id = str(result.inserted_id)
        
        logger.info(f"[Products API] Product created: id={product_id}, seller={seller_id}, name={product.name}")
        
        return {
            "success": True,
            "message": "Product created successfully",
            "product": {
                "_id": product_id,
                "name": product.name,
                "slug": slug,
                "categoryId": str(category_oid),
                "sellerId": str(seller_oid),
                "price": product.price,
                "status": "active",
                "createdAt": now.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"[Products API] Failed to create product: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CREATE_FAILED",
                "message": "Failed to create product. Please try again."
            }
        )


@api_router.get("/products/by-category/{category_id}")
async def get_products_by_category(category_id: str):
    """Get all products in a category (for vendor listing)"""
    # Products must be active AND not soft-deleted
    # SSOT: Query both categoryId (ObjectId) and category_id (string) for backward compatibility
    try:
        cat_oid = ObjectId(category_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID format")
    
    products = await db.products.find({
        "$or": [
            {"categoryId": cat_oid},
            {"category_id": category_id}
        ],
        # SSOT: Use isActive (camelCase) - exclude soft-deleted
        "isActive": {"$ne": False},
    }).sort("name", 1).to_list(500)  # Sort by name ascending
    
    # Normalize field name for frontend and filter by active status
    result = []
    for prod in products:
        serialized = serialize_mongo_doc(prod)
        serialized['isActive'] = True  # Only active products reach here
        # Ensure categoryId is present and consistent
        if "categoryId" not in serialized and "category_id" in serialized:
            serialized["categoryId"] = serialized["category_id"]
        result.append(serialized)
    
    logger.info(f"[Products By Category] Found {len(result)} products for category {category_id}")
    return result


# ============== PUBLIC PRODUCT PAGE WITH SELLERS ==============

@api_router.get("/products/detail/{product_identifier}")
async def get_product_with_sellers(product_identifier: str):
    """
    Get product details with all active sellers.
    This is the main buyer product page endpoint.
    
    PRODUCT IDENTITY GOVERNANCE (STRICT ORDER):
    1. Look up by product._id (ObjectId) - internal identity
    2. Look up by product.slug - SEO-friendly URL identity
    3. NEVER use product_name for lookup
    
    All seller lookups use productId (ObjectId) only.
    """
    from urllib.parse import unquote
    from bson import ObjectId
    
    decoded_identifier = unquote(product_identifier)
    product_info = None
    
    # ==================== IDENTITY RESOLUTION ====================
    # STRICT ORDER: ObjectId → slug → (no product_name fallback)
    
    # Step 1: Try ObjectId lookup (24-char hex string)
    if len(decoded_identifier) == 24:
        try:
            product_oid = ObjectId(decoded_identifier)
            product_info = await db.products.find_one({"_id": product_oid})
            if product_info:
                logger.info(f"[ProductDetail] Found by ObjectId: {decoded_identifier}")
        except Exception:
            pass
    
    # Step 2: Try slug lookup (SEO-friendly URL)
    if not product_info:
        product_info = await db.products.find_one({"slug": decoded_identifier})
        if product_info:
            logger.info(f"[ProductDetail] Found by slug: {decoded_identifier}")
    
    # Step 3: No fallback to product_name - return 404
    if not product_info:
        logger.warning(f"[ProductDetail] Product not found: {decoded_identifier}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    # ==================== SELLER LISTINGS LOOKUP ====================
    # CANONICAL: Use productId (ObjectId) for joins - NO legacy fallbacks
    product_oid = product_info["_id"]
    
    listings = await db.sellerListings.find({
        "productId": product_oid,
        "status": "active",
        "isActive": True  # SSOT: camelCase
    }).to_list(100)
    
    logger.info(f"[ProductDetail] Found {len(listings)} active listings for product {product_oid}")
    
    if not listings:
        raise HTTPException(status_code=404, detail="Product has no active sellers")
    
    # ==================== BUILD SELLERS LIST ====================
    sellers = []
    for listing in listings:
        # Get seller info - CANONICAL: Use sellerId (ObjectId)
        seller_info = None
        seller_id = listing.get("sellerId")  # CANONICAL: No fallback to seller_id
        if not isinstance(seller_id, ObjectId):
            logger.warning(f"[ProductDetail] Invalid sellerId type in listing {listing['_id']}")
            continue
        
        seller_id_str = str(seller_id)
        
        try:
            seller = await db.users.find_one({"_id": seller_id})
            if seller:
                seller_info = {
                    "businessName": seller.get("businessName", "Verified Seller"),
                        "city": seller.get("city"),
                        "state": seller.get("state")
                    }
        except Exception:
            pass
        
        # Extract pricing tiers and transform to frontend expected format
        raw_pricing = listing.get("pricingTiers", [])
        serialized_pricing = []
        for tier in (raw_pricing or []):
            if isinstance(tier, dict):
                # Transform camelCase to snake_case for frontend compatibility
                serialized_pricing.append({
                    "quantityMin": tier.get("minQty") or tier.get("quantityMin") or tier.get("min_quantity", 1),
                    "quantityMax": tier.get("maxQty") or tier.get("quantityMax") or tier.get("max_quantity"),
                    "pricePerUnit": tier.get("pricePerUnit") or tier.get("pricePerUnit") or 0,
                })
            else:
                serialized_pricing.append(tier)
        
        # Serialize specifications
        specs = listing.get("specifications", {})
        if isinstance(specs, dict):
            specs = serialize_mongo_doc(specs)
        
        sellers.append({
            "listingId": str(listing["_id"]),
            "sellerId": seller_id_str,
            "companyName": seller_info.get("businessName", "Verified Seller") if seller_info else "Verified Seller",
            "location": f"{seller_info.get('city', '')}, {seller_info.get('state', '')}" if seller_info else "India",
            "moq": listing.get("moq", 1),
            "pricingTiers": serialized_pricing,
            "leadTimeDays": listing.get("leadTime"),
            "stockStatus": listing.get("stockStatus", "in_stock"),
            "images": listing.get("images", [])[:2],
            "specifications": specs
        })
    
    # ==================== BUILD RESPONSE ====================
    # Get category name from categories collection
    category_id = product_info.get("categoryId")
    category_id_str = str(category_id) if isinstance(category_id, ObjectId) else category_id
    category_name = None
    
    if category_id:
        try:
            cat_oid = ObjectId(category_id) if isinstance(category_id, str) else category_id
            category_doc = await db.categories.find_one({"_id": cat_oid})
            if category_doc:
                category_name = category_doc.get("name")
        except Exception as e:
            logger.warning(f"Failed to fetch category name: {e}")
    
    # Serialize spec_schema
    spec_schema = []
    if product_info.get("specSchema"):
        for spec in product_info["specSchema"]:
            spec_schema.append(serialize_mongo_doc(spec) if isinstance(spec, dict) else spec)
    
    # Get images from product (canonical source)
    images = product_info.get("images", [])
    safe_images = []
    for img in (images or []):
        if isinstance(img, ObjectId):
            safe_images.append(str(img))
        elif isinstance(img, dict):
            safe_images.append(serialize_mongo_doc(img))
        else:
            safe_images.append(img)
    
    return {
        "productId": str(product_info["_id"]),
        "productName": product_info.get("name"),
        "slug": product_info.get("slug"),
        "categoryId": category_id_str,
        "categoryName": category_name,
        "description": product_info.get("description"),
        "specifications": serialize_mongo_doc(product_info.get("normalizedSpecs", {})),
        "images": safe_images,
        "specSchema": spec_schema,
        "normalized_spec_hash": product_info.get("normalized_spec_hash"),
        "sellerCount": len(sellers),
        "sellers": sellers
    }


# ============== PRODUCT CATALOG - HIERARCHY & SEARCH ==============
# NOTE: These routes MUST come BEFORE /products/{product_id} to avoid route conflicts

@api_router.get("/products/search/typeahead")
async def product_typeahead(q: str, category_id: Optional[str] = None, limit: int = 20):
    """Type-ahead product search for vendor listing creation"""
    if not q or len(q) < 2:
        return []
    
    match_filter = {"active": True}
    if category_id:
        match_filter["categoryId"] = ObjectId(category_id)
    
    # Search in name, family, variant
    match_filter["$or"] = [
        {"name": {"$regex": q, "$options": "i"}},
        {"family": {"$regex": q, "$options": "i"}},
        {"variant": {"$regex": q, "$options": "i"}}
    ]
    
    pipeline = [
        {"$match": match_filter},
        {"$lookup": {
            "from": "categories",
            "localField": "categoryId",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 1,
            "name": 1,
            "family": 1,
            "variant": 1,
            "unit": 1,
            "categoryId": 1,
            "categoryName": "$category.name",
            "specSchema": 1,
            "description": 1
        }},
        {"$limit": limit}
    ]
    
    products = await db.products.aggregate(pipeline).to_list(limit)
    return serialize_doc(products)

@api_router.get("/products/hierarchy")
async def get_product_hierarchy(category_id: Optional[str] = None):
    """Get product hierarchy: Category → Family → Variant for dropdown selection"""
    match_filter = {"active": True}
    if category_id:
        match_filter["categoryId"] = ObjectId(category_id)
    
    pipeline = [
        {"$match": match_filter},
        {"$lookup": {
            "from": "categories",
            "localField": "categoryId",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": {
                "categoryId": "$categoryId",
                "categoryName": "$category.name",
                "family": "$family"
            },
            "variants": {
                "$push": {
                    "productId": "$_id",
                    "variant": "$variant",
                    "name": "$name",
                    "unit": "$unit",
                    "specSchema": "$spec_schema"
                }
            }
        }},
        {"$group": {
            "_id": {
                "categoryId": "$_id.categoryId",
                "categoryName": "$_id.category_name"
            },
            "families": {
                "$push": {
                    "family": "$_id.family",
                    "variants": "$variants"
                }
            }
        }},
        {"$project": {
            "_id": 0,
            "categoryId": "$_id.categoryId",
            "categoryName": "$_id.category_name",
            "families": 1
        }},
        {"$sort": {"categoryName": 1}}
    ]
    
    hierarchy = await db.products.aggregate(pipeline).to_list(100)
    return serialize_doc(hierarchy)

@api_router.get("/products/families/{category_id}")
async def get_product_families(category_id: str):
    """Get unique product families within a category"""
    pipeline = [
        {"$match": {"categoryId": ObjectId(category_id), "active": True}},
        {"$group": {"_id": "$family"}},
        {"$project": {"_id": 0, "family": "$_id"}},
        {"$sort": {"family": 1}}
    ]
    families = await db.products.aggregate(pipeline).to_list(100)
    return [f["family"] for f in families if f.get("family")]

@api_router.get("/products/variants/{category_id}/{family}")
async def get_product_variants(category_id: str, family: str):
    """Get product variants within a family"""
    products = await db.products.find({
        "categoryId": ObjectId(category_id),
        "family": family,
        "active": True
    }).to_list(100)
    return serialize_doc(products)

# This route MUST come AFTER all specific /products/* routes to avoid conflicts
@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": obj_id})

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return serialize_mongo_doc(product)


# ============== PRODUCT REQUEST ENDPOINTS ==============

@api_router.post("/product-requests")
async def create_product_request(request: ProductRequestCreate, user: dict = Depends(require_auth)):
    """Vendor submits a request for a product not found in catalog"""
    # Check if similar request already exists
    existing = await db.product_requests.find_one({
        "categoryId": ObjectId(request.category_id),
        "productName": {"$regex": f"^{request.product_name}$", "$options": "i"},
        "status": {"$in": ["pending", "approved"]}
    })
    
    if existing:
        if existing.get("status") == "approved":
            return {"message": "This product already exists", "productId": str(existing.get("approved_product_id"))}
        return {"message": "A similar request is already pending review", "request_id": str(existing["_id"])}
    
    request_doc = {
        "_id": ObjectId(),
        "categoryId": ObjectId(request.category_id),
        "family": request.family,
        "variant": request.variant,
        "productName": request.product_name,
        "technicalDetails": request.technical_details,
        "supportingDocument": request.supporting_document,
        "requestedBy": ObjectId(user["_id"]),
        "status": "pending",  # pending, approved, rejected
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.product_requests.insert_one(request_doc)
    return {
        "message": "Product request submitted for admin review",
        "request_id": str(request_doc["_id"]),
        "status": "pending"
    }

@api_router.get("/product-requests/my")
async def get_my_product_requests(user: dict = Depends(require_auth)):
    """Get current user's product requests"""
    requests = await db.product_requests.find({
        "requestedBy": ObjectId(user["_id"])
    }).sort("createdAt", -1).to_list(50)
    return serialize_doc(requests)

@api_router.post("/admin/product-requests/{request_id}/approve")
async def approve_product_request(request_id: str, admin: dict = Depends(require_admin)):
    """Admin approves a product request and creates the product"""
    try:
        request = await db.product_requests.find_one({"_id": ObjectId(request_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request ID format")
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # Create the product
    prod_doc = {
        "_id": ObjectId(),
        "categoryId": request["categoryId"],
        "family": request.get("family", ""),
        "variant": request.get("variant", ""),
        "name": request["productName"],
        "description": request.get("technicalDetails", ""),
        "unit": "pieces",
        "standardParameters": [],
        "specSchema": [],
        "isActive": True,  # SSOT: camelCase
        "createdAt": datetime.now(timezone.utc),
        "createdBy": str(admin["_id"]),
        "created_from_request": ObjectId(request_id)
    }
    await db.products.insert_one(prod_doc)
    
    # Update request status
    await db.product_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "approved",
            "approved_product_id": prod_doc["_id"],
            "approvedBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    logger.info(f"Admin {admin['email']} approved product request: {request_id}")
    return {"message": "Product created", "productId": str(prod_doc["_id"])}

@api_router.post("/admin/product-requests/{request_id}/reject")
async def reject_product_request(
    request_id: str, 
    reason: str = "Does not meet catalog criteria",
    admin: dict = Depends(require_admin)
):
    """Admin rejects a product request"""
    try:
        request = await db.product_requests.find_one({"_id": ObjectId(request_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request ID format")
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    await db.product_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "rejected",
            "rejectionReason": reason,
            "rejectedBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    logger.info(f"Admin {admin['email']} rejected product request: {request_id}")
    return {"message": "Request rejected"}

# ============== LISTING ENDPOINTS ==============

@api_router.post("/listings")
async def create_listing(listing: ListingCreate, user: dict = Depends(require_auth)):
    """
    Create or update a seller listing.
    
    SSOT: Uses seller_listings collection exclusively.
    Unique constraint: (productId, sellerId) - ONE listing per product per seller.
    
    Behavior:
    - If listing exists for this (product, seller) -> UPDATE it
    - If no listing exists -> CREATE new one
    - This prevents 409 conflicts and provides better UX
    """
    # Verify product exists
    product = await db.products.find_one({"_id": ObjectId(listing.productId)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    seller_oid = ObjectId(user["_id"])
    product_oid = ObjectId(listing.productId)
    
    # Check for existing listing (unique constraint: productId + sellerId)
    existing = await db.sellerListings.find_one({
        "productId": product_oid,
        "sellerId": seller_oid
    })
    
    # If not draft, require email verification
    if not listing.isDraft and not user.get("emailVerified", False):
        raise HTTPException(status_code=403, detail="Email verification required to publish")
    
    # If not draft, require GST verification
    if not listing.isDraft:
        user_doc = await db.users.find_one({"_id": seller_oid})
        gst = user_doc.get("gst", {})
        if not gst.get("number"):
            raise HTTPException(status_code=400, detail="GST number required to publish")
        # SSOT: gst.status must be "verified" to publish
        if gst.get("status") != "verified":
            raise HTTPException(
                status_code=403, 
                detail=f"GST verification required. Current status: {gst.get('status', 'none')}"
            )
    
    # Validate mandatory fields for publishing
    if not listing.isDraft:
        if not listing.images:
            raise HTTPException(status_code=400, detail="At least 1 image required to publish")
        if not listing.pricingSlabs:
            raise HTTPException(status_code=400, detail="Pricing slabs required to publish")
        if listing.quantity <= 0 or listing.moq <= 0 or listing.maxCapacity <= 0:
            raise HTTPException(status_code=400, detail="Valid quantity, MOQ, and capacity required")
    
    # Convert pricingSlabs to pricingTiers format (SSOT schema)
    pricing_tiers = []
    for slab in listing.pricingSlabs:
        pricing_tiers.append({
            "minQty": slab.minQuantity,
            "maxQty": slab.maxQuantity,
            "pricePerUnit": slab.pricePerUnit
        })
    
    now = datetime.now(timezone.utc)
    
    # Get categoryId from product (canonical reference)
    category_oid = product.get("categoryId")
    if isinstance(category_oid, str):
        category_oid = ObjectId(category_oid)
    
    if existing:
        # UPDATE existing listing instead of returning 409
        update_data = {
            "status": "inactive" if listing.isDraft else "active",
            "isActive": not listing.isDraft,
            "stock": listing.quantity,
            "moq": listing.moq,
            "maxCapacity": listing.maxCapacity,
            "capacityTimeBasis": listing.capacityTimeBasis,
            "leadTime": listing.leadTime or "7 days",
            "pricingTiers": pricing_tiers,
            "sellerRole": listing.sellerRole,
            "specifications": listing.specifications,
            "description": listing.description,
            "images": listing.images,
            "packagingSize": listing.packagingSize,
            "deliveryLocations": listing.deliveryLocations,
            "sellerNotes": listing.sellerNotes,
            "updatedAt": now,
        }
        
        # Update lastStockUpdate and publishedAt only if publishing
        if not listing.isDraft:
            update_data["lastStockUpdate"] = now
            if not existing.get("publishedAt"):
                update_data["publishedAt"] = now
        
        await db.sellerListings.update_one(
            {"_id": existing["_id"]},
            {"$set": update_data}
        )
        
        # Fetch and return updated document
        updated = await db.sellerListings.find_one({"_id": existing["_id"]})
        logger.info(f"Seller {user['email']} updated listing for product {listing.productId}")
        return {
            **serialize_doc(updated),
            "message": "Listing updated successfully",
            "action": "updated"
        }
    
    # CREATE new listing
    listing_doc = {
        "_id": ObjectId(),
        # CANONICAL SSOT: ObjectId references ONLY - NO string IDs, NO denormalized names
        "productId": product_oid,
        "sellerId": seller_oid,
        "categoryId": category_oid,
        # Status: "active" or "inactive" (replaces isDraft)
        "status": "inactive" if listing.isDraft else "active",
        "isActive": not listing.isDraft,  # SSOT: camelCase
        # Commercial data
        "stock": listing.quantity,
        "moq": listing.moq,
        "maxCapacity": listing.maxCapacity,
        "capacityTimeBasis": listing.capacityTimeBasis,
        "leadTime": listing.leadTime or "7 days",
        "currency": "INR",
        "pricingTiers": pricing_tiers,
        # Additional seller-specific data
        "sellerRole": listing.sellerRole,
        "specifications": listing.specifications,
        "description": listing.description,
        "images": listing.images,
        "packagingSize": listing.packagingSize,
        "deliveryLocations": listing.deliveryLocations,
        "sellerNotes": listing.sellerNotes,
        # Timestamps
        "createdAt": now,
        "updatedAt": now,
        "lastStockUpdate": now if not listing.isDraft else None,
        "publishedAt": now if not listing.isDraft else None
    }
    
    await db.sellerListings.insert_one(listing_doc)
    logger.info(f"Seller {user['email']} created new listing for product {listing.productId}")
    return {
        **serialize_doc(listing_doc),
        "message": "Listing created successfully",
        "action": "created"
    }

@api_router.get("/listings/my")
async def get_my_listings(user: dict = Depends(require_auth)):
    """
    Get current user's listings from seller_listings collection.
    
    SSOT: Uses seller_listings as the single source of truth.
    """
    seller_oid = ObjectId(user["_id"])
    
    pipeline = [
        {"$match": {"sellerId": seller_oid}},
        # Join with products collection
        {"$lookup": {
            "from": "products",
            "localField": "productId",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        # Join with categories for product category info - STRICT camelCase
        {"$lookup": {
            "from": "categories",
            "let": {"catId": "$product.categoryId"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$catId"]}}}
            ],
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"createdAt": -1}},
        # Project to include useful fields
        {"$project": {
            "_id": 1,
            "productId": 1,
            "sellerId": 1,
            "status": 1,
            "stock": 1,
            "moq": 1,
            "maxCapacity": 1,
            "capacityTimeBasis": 1,
            "leadTime": 1,
            "currency": 1,
            "pricingTiers": 1,
            "sellerRole": 1,
            "specifications": 1,
            "description": 1,
            "images": 1,
            "packagingSize": 1,
            "deliveryLocations": 1,
            "sellerNotes": 1,
            "createdAt": 1,
            "updatedAt": 1,
            "lastStockUpdate": 1,
            "publishedAt": 1,
            # Product info
            "product": {
                "_id": "$product._id",
                "name": "$product.name",
                "family": "$product.family",
                "variant": "$product.variant",
                "slug": "$product.slug",
                "unit": "$product.unit"
            },
            # Category info
            "category": {
                "_id": "$category._id",
                "name": "$category.name"
            }
        }}
    ]
    
    listings = await db.sellerListings.aggregate(pipeline).to_list(100)
    return serialize_doc(listings)

@api_router.put("/listings/{listing_id}")
async def update_listing(listing_id: str, update: ListingUpdate, user: dict = Depends(require_auth)):
    """
    Update a seller listing.
    
    SSOT: Uses seller_listings collection exclusively.
    Validates ownership via sellerId.
    """
    # Validate listing_id format
    if not ObjectId.is_valid(listing_id):
        raise HTTPException(status_code=400, detail="Invalid listing ID format")
    
    seller_oid = ObjectId(user["_id"])
    listing_oid = ObjectId(listing_id)
    
    # Verify listing exists and belongs to user
    listing = await db.sellerListings.find_one({
        "_id": listing_oid,
        "sellerId": seller_oid
    })
    
    if not listing:
        # Check if listing exists at all
        exists = await db.sellerListings.find_one({"_id": listing_oid})
        if exists:
            raise HTTPException(status_code=403, detail="Not authorized to update this listing")
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Build update document
    update_dict = {}
    update_data = update.dict(exclude_none=True)
    
    # Map fields to SSOT schema
    field_mapping = {
        "specifications": "specifications",
        "description": "description",
        "images": "images",
        "quantity": "stock",
        "moq": "moq",
        "maxCapacity": "maxCapacity",
        "capacity_time_basis": "capacityTimeBasis",
        "sellerRole": "sellerRole",
        "leadTime": "leadTime",
        "packagingSize": "packagingSize",
        "deliveryLocations": "deliveryLocations",
        "sellerNotes": "sellerNotes"
    }
    
    for old_key, new_key in field_mapping.items():
        if old_key in update_data and update_data[old_key] is not None:
            update_dict[new_key] = update_data[old_key]
    
    # Handle pricing_slabs -> pricingTiers conversion
    if "pricingSlabs" in update_data and update_data["pricingSlabs"]:
        pricing_tiers = []
        for slab in update_data["pricingSlabs"]:
            if isinstance(slab, dict):
                pricing_tiers.append({
                    "minQty": slab.get("min_quantity", 1),
                    "maxQty": slab.get("max_quantity"),
                    "pricePerUnit": slab.get("pricePerUnit", 0)
                })
            else:
                pricing_tiers.append({
                    "minQty": slab.min_quantity,
                    "maxQty": slab.max_quantity,
                    "pricePerUnit": slab.price_per_unit
                })
        update_dict["pricingTiers"] = pricing_tiers
    
    if not update_dict:
        # No fields to update, return current listing
        return serialize_doc(listing)
    
    update_dict["updatedAt"] = datetime.now(timezone.utc)
    
    await db.sellerListings.update_one(
        {"_id": listing_oid, "sellerId": seller_oid},
        {"$set": update_dict}
    )
    
    updated_listing = await db.sellerListings.find_one({"_id": listing_oid})
    return serialize_doc(updated_listing)

@api_router.post("/listings/{listing_id}/update-stock")
async def update_stock(listing_id: str, user: dict = Depends(require_auth)):
    """
    Confirm stock values for the day (UPDATE button).
    
    SSOT: Uses seller_listings collection exclusively.
    """
    seller_oid = ObjectId(user["_id"])
    listing_oid = ObjectId(listing_id)
    
    # Verify listing exists and belongs to user
    listing = await db.sellerListings.find_one({
        "_id": listing_oid,
        "sellerId": seller_oid
    })
    
    if not listing:
        exists = await db.sellerListings.find_one({"_id": listing_oid})
        if exists:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Listing not found")
    
    now = datetime.now(timezone.utc)
    await db.sellerListings.update_one(
        {"_id": listing_oid, "sellerId": seller_oid},
        {"$set": {
            "lastStockUpdate": now,
            "updatedAt": now
        }}
    )
    
    # Cancel any pending notifications for this listing
    await db.notifications.update_many(
        {"listingId": listing_oid, "status": "pending"},
        {"$set": {"status": "cancelled"}}
    )
    
    return {"message": "Stock updated successfully", "updatedAt": now.isoformat()}

@api_router.post("/listings/{listing_id}/publish")
async def publish_listing(listing_id: str, user: dict = Depends(require_verified_user)):
    """
    Publish a draft listing (set status to active).
    
    ENTERPRISE GRADE VALIDATION:
    1. Check GST verification
    2. Check seller account status
    3. Validate listing completeness (all mandatory fields)
    4. Only then allow publishing
    
    SSOT: Uses sellerListings collection exclusively.
    """
    seller_oid = ObjectId(user["_id"])
    listing_oid = ObjectId(listing_id)
    
    # Verify listing exists and belongs to user
    listing = await db.sellerListings.find_one({
        "_id": listing_oid,
        "sellerId": seller_oid
    })
    
    if not listing:
        exists = await db.sellerListings.find_one({"_id": listing_oid})
        if exists:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Check if user has GST verification (required for first publish)
    user_doc = await db.users.find_one({"_id": seller_oid})
    gst = user_doc.get("gst", {})
    if not gst.get("number"):
        raise HTTPException(status_code=400, detail="GST number required to publish")
    
    # SSOT: gst.status must be "verified" to publish
    if gst.get("status") != "verified":
        raise HTTPException(
            status_code=403, 
            detail=f"GST verification required. Current status: {gst.get('status', 'none')}"
        )
    
    # Check seller account status
    seller_status = user_doc.get("sellerStatus", "active")
    if seller_status == "banned":
        raise HTTPException(status_code=403, detail="Seller account is banned")
    if seller_status == "suspended":
        raise HTTPException(status_code=403, detail="Seller account is suspended")
    
    # ENTERPRISE GRADE: Validate all mandatory fields
    required_fields = {
        "pricingTiers": {
            "check": lambda v: v and len(v) > 0,
            "message": "At least one pricing tier required"
        },
        "moq": {
            "check": lambda v: v and v > 0,
            "message": "MOQ (Minimum Order Quantity) must be greater than 0"
        },
        "stock": {
            "check": lambda v: v and v > 0,
            "message": "Stock quantity must be greater than 0"
        },
        "maxCapacity": {
            "check": lambda v: v and v > 0,
            "message": "Maximum capacity must be greater than 0"
        },
        "images": {
            "check": lambda v: v and len(v) > 0,
            "message": "At least one product image required"
        },
        "variantId": {
            "check": lambda v: v is not None,
            "message": "Product variant must be linked"
        }
    }
    
    missing_fields = []
    field_errors = {}
    
    for field, config in required_fields.items():
        value = listing.get(field)
        if not config["check"](value):
            missing_fields.append(field)
            field_errors[field] = config["message"]
    
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Listing is incomplete and cannot be published",
                "missingFields": missing_fields,
                "fieldErrors": field_errors,
                "message": f"Please complete the following fields before publishing: {', '.join(missing_fields)}"
            }
        )
    
    now = datetime.now(timezone.utc)
    await db.sellerListings.update_one(
        {"_id": listing_oid, "sellerId": seller_oid},
        {"$set": {
            "status": "active",
            "publishedAt": now,
            "lastStockUpdate": now,
            "updatedAt": now
        }}
    )
    
    return {"message": "Listing published successfully"}

@api_router.delete("/listings/{listing_id}")
async def delete_listing(listing_id: str, user: dict = Depends(require_verified_user)):
    """
    Soft-delete a seller listing (requires email verification).
    
    ARCHITECTURE: Sets isActive=false and status="archived"
    - Never hard-deletes to preserve data integrity
    - Master product remains unchanged
    
    SSOT: Uses seller_listings collection exclusively.
    """
    seller_oid = ObjectId(user["_id"])
    listing_oid = ObjectId(listing_id)
    
    # Verify listing exists and belongs to user
    listing = await db.sellerListings.find_one({
        "_id": listing_oid,
        "sellerId": seller_oid
    })
    
    if not listing:
        exists = await db.sellerListings.find_one({"_id": listing_oid})
        if exists:
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Soft-delete via isActive=false and status="archived"
    now = datetime.now(timezone.utc)
    await db.sellerListings.update_one(
        {"_id": listing_oid, "sellerId": seller_oid},
        {"$set": {
            "status": "archived",
            "isActive": False,
            "updatedAt": now
        }}
    )
    return {"message": "Listing archived successfully", "status": "archived"}

# ============== SEARCH ENDPOINTS ==============

@api_router.post("/search")
async def search_listings(search: SearchQuery):
    """
    Search listings with intelligent parsing and location-based ranking.
    
    SSOT: Uses seller_listings collection exclusively.
    """
    query_text = search.query.lower().strip()
    
    # Build search filter - SSOT: Use status="active" instead of is_draft=False
    match_filter = {"status": "active"}
    
    # Text search on product names and specifications
    if query_text:
        match_filter["$or"] = [
            {"description": {"$regex": query_text, "$options": "i"}},
            {"specifications": {"$regex": query_text, "$options": "i"}}
        ]
    
    if search.category_id:
        # Get product IDs in this category
        products = await db.products.find({"category_id": ObjectId(search.category_id)}).to_list(500)
        product_ids = [p["_id"] for p in products]
        match_filter["productId"] = {"$in": product_ids}
    
    if search.min_quantity:
        match_filter["stock"] = {"$gte": search.min_quantity}
    
    pipeline = [
        {"$match": match_filter},
        # SSOT: Use productId (ObjectId) for lookup
        {"$lookup": {
            "from": "products",
            "localField": "productId",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        # SSOT: Use sellerId (ObjectId) for lookup
        {"$lookup": {
            "from": "users",
            "localField": "sellerId",
            "foreignField": "_id",
            "as": "seller"
        }},
        {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
        # Exclude deleted users' listings from search
        {"$match": {
            "$or": [
                {"seller.accountStatus": {"$exists": False}},
                {"seller.accountStatus": "active"},
                {"seller.accountStatus": None}
            ]
        }},
        {"$lookup": {
            "from": "categories",
            "localField": "product.categoryId",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}}
    ]
    
    # Add text search on product name
    if query_text:
        pipeline.insert(1, {
            "$match": {
                "$or": [
                    {"product.name": {"$regex": query_text, "$options": "i"}},
                    {"description": {"$regex": query_text, "$options": "i"}}
                ]
            }
        })
    
    # Location filtering
    if not search.expand_to_all_india and (search.city or search.state):
        location_filter = {}
        if search.city:
            location_filter["seller.city"] = {"$regex": search.city, "$options": "i"}
        elif search.state:
            location_filter["seller.state"] = {"$regex": search.state, "$options": "i"}
        pipeline.append({"$match": location_filter})
    
    # Sort by lastStockUpdate (freshness) then by price
    pipeline.append({"$sort": {"lastStockUpdate": -1}})
    pipeline.append({"$limit": 50})
    
    # SSOT: Use seller_listings collection
    listings = await db.sellerListings.aggregate(pipeline).to_list(50)
    
    # Calculate distances and mask vendor info
    results = []
    for listing in listings:
        seller = listing.get("seller", {})
        
        # Calculate distance if coordinates available
        distance = None
        if search.latitude and search.longitude and seller.get("latitude") and seller.get("longitude"):
            distance = calculate_distance(
                search.latitude, search.longitude,
                seller["latitude"], seller["longitude"]
            )
        
        # Calculate "updated X days ago" - SSOT: Use lastStockUpdate
        last_update = listing.get("lastStockUpdate", listing.get("last_stock_update"))
        if last_update:
            if isinstance(last_update, str):
                last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            days_ago = (datetime.now(timezone.utc) - last_update).days
            update_status = "Updated today" if days_ago == 0 else f"Updated {days_ago} days ago"
        else:
            update_status = "Not updated"
        
        # SSOT: Map field names to standard schema
        result = {
            "_id": str(listing["_id"]),
            "productId": str(listing.get("productId", listing.get("productId", ""))),
            "productName": listing.get("product", {}).get("name", ""),
            "categoryName": listing.get("category", {}).get("name", ""),
            "sellerRole": listing.get("sellerRole", listing.get("sellerRole", "")),
            "sellerArea": seller.get("city", ""),
            "sellerState": seller.get("state", ""),
            "distanceKm": round(distance, 1) if distance else None,
            "specifications": listing.get("specifications", {}),
            "description": listing.get("description", ""),
            "images": listing.get("images", [])[:1],  # Show only first image in search
            "quantity": listing.get("stock", listing.get("quantity", 0)),
            "moq": listing.get("moq", 0),
            "maxCapacity": listing.get("maxCapacity", listing.get("maxCapacity", 0)),
            "capacity_time_basis": listing.get("capacityTimeBasis", listing.get("capacity_time_basis", "day")),
            "pricingSlabs": listing.get("pricingTiers", listing.get("pricingSlabs", []))[:3],  # Show 2-3 slabs
            "updateStatus": update_status,
            "isFavourite": False  # Will be updated by frontend if user is logged in
        }
        results.append(result)
    
    # Sort by distance if available
    if search.latitude and search.longitude:
        results.sort(key=lambda x: (x["distanceKm"] or 99999, x["updateStatus"]))
    
    # Check if we should suggest expanding search
    no_results_nearby = len(results) == 0 and not search.expand_to_all_india
    
    return {
        "results": results,
        "total": len(results),
        "no_results_nearby": no_results_nearby,
        "searchScope": "all_india" if search.expand_to_all_india else (search.city or search.state or "nearby")
    }

# ============== DEDUPLICATED PRODUCT SEARCH (NEW) ==============

@api_router.post("/search/products")
@limiter.limit("30/minute")
async def search_products_deduplicated(request: Request, search: SearchQuery):
    """
    Product-level search with deduplication.
    Returns ONE product card per product with multiple sellers nested inside.
    Uses seller_listings collection for active listings.
    """
    query_text = search.query.lower().strip() if search.query else ""
    
    # Build search filter for seller_listings - SSOT: camelCase
    match_filter = {"status": "active", "isActive": True}
    
    if search.category_id:
        # SSOT: categoryId is ObjectId in seller_listings
        try:
            match_filter["categoryId"] = ObjectId(search.category_id)
        except:
            match_filter["categoryId"] = search.category_id
    
    # Aggregation pipeline for deduplicated product search - SSOT: camelCase fields
    pipeline = [
        {"$match": match_filter},
        # Lookup product info (for name, slug, description)
        {"$lookup": {
            "from": "products",
            "localField": "productId",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": False}},
        # Lookup seller info from users
        {"$lookup": {
            "from": "users",
            "localField": "sellerId",
            "foreignField": "_id",
            "as": "seller"
        }},
        {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
        # Lookup category info
        {"$lookup": {
            "from": "categories",
            "localField": "categoryId",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}}
    ]
    
    # Add text search on product name
    if query_text:
        pipeline.append({
            "$match": {
                "$or": [
                    {"product.name": {"$regex": query_text, "$options": "i"}},
                    {"description": {"$regex": query_text, "$options": "i"}},
                    {"category.name": {"$regex": query_text, "$options": "i"}}
                ]
            }
        })
    
    # Location filtering
    if search.city or search.state:
        location_filter = {}
        if search.city:
            location_filter["seller.city"] = {"$regex": search.city, "$options": "i"}
        elif search.state:
            location_filter["seller.state"] = {"$regex": search.state, "$options": "i"}
        pipeline.append({"$match": location_filter})
    
    # Group by product - ONE product card with multiple sellers - SSOT: camelCase
    pipeline.append({
        "$group": {
            "_id": "$productId",
            "productName": {"$first": "$product.name"},
            "productSlug": {"$first": "$product.slug"},
            "category_id": {"$first": {"$toString": "$categoryId"}},
            "categoryName": {"$first": "$category.name"},
            "description": {"$first": "$description"},
            "images": {"$first": "$images"},
            "sellers": {
                "$push": {
                    "listingId": {"$toString": "$_id"},
                    "sellerId": {"$toString": "$sellerId"},
                    "businessName": "$seller.businessName",
                    "city": "$seller.city",
                    "state": "$seller.state",
                    "pricingTiers": "$pricingTiers",
                    "stock": "$stock",
                    "specifications": "$specifications"
                }
            },
            "minPrice": {"$min": {"$arrayElemAt": ["$pricingTiers.price", 0]}},
            "sellerCount": {"$sum": 1}
        }
    })
    
    # Sort products by seller count and minimum price
    pipeline.append({"$sort": {"sellerCount": -1, "minPrice": 1}})
    pipeline.append({"$limit": 50})
    
    products_raw = await db.sellerListings.aggregate(pipeline).to_list(50)
    
    # Format response
    products = []
    for p in products_raw:
        prod_id = p.get("_id")
        products.append({
            "productId": str(prod_id) if prod_id else None,
            "productName": p.get("productName"),
            "productSlug": p.get("productSlug"),
            "category_id": p.get("category_id"),
            "categoryName": p.get("categoryName"),
            "description": p.get("description"),
            "images": p.get("images", []),
            "sellers": p.get("sellers", []),
            "minPrice": p.get("minPrice"),
            "sellerCount": p.get("sellerCount", 0)
        })
    
    return {
        "products": products,
        "total": len(products),
        "query": search.query
    }

@api_router.get("/listings/{listing_id}")
async def get_listing_detail(
    listing_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get listing details (masked vendor info unless enquiry confirmed).
    
    SSOT: Uses sellerListings collection exclusively.
    
    Returns:
        - 200: Listing details with masked/revealed vendor info
        - 400: Invalid listing ID format
        - 404: Listing not found
    """
    # STEP 1: Validate ObjectId format
    try:
        listing_oid = ObjectId(listing_id)
    except Exception:
        logger.warning(f"Invalid listing_id format: {listing_id}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error_code": "INVALID_OBJECT_ID",
                "field": "listing_id",
                "message": "Invalid listing ID format"
            }
        )
    
    try:
        # STEP 2: Build aggregation pipeline with proper field names
        pipeline = [
            {"$match": {"_id": listing_oid}},
            # SSOT: Use productId (ObjectId) for lookup
            {"$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "product"
            }},
            {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
            # SSOT: Use sellerId (ObjectId) for lookup
            {"$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }},
            {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
            # Exclude deleted users' listings from access - SSOT: accountStatus
            {"$match": {
                "$or": [
                    {"seller.accountStatus": {"$exists": False}},
                    {"seller.accountStatus": "active"},
                    {"seller.accountStatus": None}
                ]
            }},
            {"$lookup": {
                "from": "categories",
                "localField": "product.categoryId",  # SSOT: camelCase
                "foreignField": "_id",
                "as": "category"
            }},
            {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}}
        ]
        
        # STEP 3: Execute query with defensive handling
        listings = await db.sellerListings.aggregate(pipeline).to_list(1)
        
        # STEP 4: Check result exists BEFORE accessing
        if not listings:
            raise HTTPException(
                status_code=404, 
                detail={
                    "error_code": "LISTING_NOT_FOUND",
                    "message": "Listing not found"
                }
            )
        
        listing = listings[0]
        seller = listing.get("seller") or {}
        product = listing.get("product") or {}
        category = listing.get("category") or {}
        
        # STEP 5: Check if vendor details should be revealed
        reveal_vendor = False
        if user and user.get("_id"):
            try:
                user_oid = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
                enquiry = await db.inquiries.find_one({
                    "listingId": listing_oid,
                    "buyerId": user_oid,
                    "status": "confirmed"
                })
                reveal_vendor = enquiry is not None
            except Exception as e:
                logger.warning(f"Error checking enquiry: {e}")
                reveal_vendor = False
        
        # STEP 6: Calculate update status - SSOT: Use lastStockUpdate
        update_status = "Not updated"
        last_update = listing.get("lastStockUpdate")
        if last_update:
            try:
                if isinstance(last_update, str):
                    last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                days_ago = (datetime.now(timezone.utc) - last_update).days
                update_status = "Updated today" if days_ago == 0 else f"Updated {days_ago} days ago"
            except Exception:
                update_status = "Not updated"
        
        # STEP 7: Build response with safe field access
        result = {
            "_id": str(listing["_id"]),
            "productId": str(listing.get("productId", "")),
            "productName": product.get("name", ""),
            "productUnit": product.get("unit", "pieces"),
            "categoryName": category.get("name", ""),
            "sellerRole": listing.get("sellerRole", ""),
            "sellerArea": seller.get("city", ""),
            "sellerState": seller.get("state", ""),
            "specifications": listing.get("specifications") or listing.get("attributes") or {},
            "description": listing.get("description", ""),
            "images": listing.get("images") or [],
            "quantity": listing.get("stock") or listing.get("quantity") or 0,
            "moq": listing.get("moq") or 0,
            "maxCapacity": listing.get("maxCapacity") or 0,
            "capacityTimeBasis": listing.get("capacityTimeBasis", "day"),
            "pricingSlabs": listing.get("pricingTiers") or listing.get("pricingSlabs") or [],
            "updateStatus": update_status,
            "vendorRevealed": reveal_vendor
        }
        
        # STEP 8: Add vendor details only if revealed
        if reveal_vendor:
            result["vendor"] = {
                "businessName": seller.get("businessName", ""),
                "phone": seller.get("phone", ""),
                "email": seller.get("email", ""),
                "address": seller.get("address", ""),
                "gstNumber": seller.get("gstNumber", "")
            }
        
        # ENTERPRISE STANDARD: Always serialize before return
        return success_response(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Listing fetch failed for {listing_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LISTING_FETCH_FAILED",
                "message": "Failed to fetch listing"
            }
        )

# ============== ENQUIRY ENDPOINTS ==============

@api_router.post("/enquiries")
async def create_enquiry(enquiry: EnquiryCreate, user: dict = Depends(require_verified_user)):
    """Create a new enquiry - SSOT: Uses seller_listings collection"""
    # SSOT: Use seller_listings collection
    listing = await db.sellerListings.find_one({"_id": ObjectId(enquiry.listingId)})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # SSOT: Use sellerId (ObjectId) - CANONICAL FIELD NAME
    seller_oid = listing.get("sellerId")  # SSOT: camelCase
    if not seller_oid:
        raise HTTPException(status_code=500, detail="Invalid listing: missing sellerId")
    
    seller = await db.users.find_one({"_id": seller_oid})
    if seller:
        subscription = seller.get("subscription", {})
        if subscription.get("status") == "expired":
            # Check enquiry limit
            if subscription.get("enquiriesThisMonth", 0) >= 5:
                raise HTTPException(
                    status_code=400,
                    detail="This seller has reached their monthly enquiry limit. Please try again next month."
                )
    
    enquiry_doc = {
        "_id": ObjectId(),
        "listingId": ObjectId(enquiry.listingId),
        "buyerId": ObjectId(user["_id"]),
        "sellerId": seller_oid,  # SSOT: Store as ObjectId
        "quantity": enquiry.quantity,
        "message": enquiry.message,
        "status": "sent",  # sent, confirmed, closed
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.inquiries.insert_one(enquiry_doc)
    
    # Increment seller's enquiry count if expired subscription
    if seller and seller.get("subscription", {}).get("status") == "expired":
        await db.users.update_one(
            {"_id": seller_oid},  # SSOT: Use seller_oid (already extracted from listing.sellerId)
            {"$inc": {"subscription.enquiriesThisMonth": 1}}
        )
    
    # Get seller phone for WhatsApp
    seller_phone = seller.get("phone", "") if seller else ""
    
    # Generate WhatsApp message - SSOT: Use productId (camelCase)
    product_oid = listing.get("productId")
    product = await db.products.find_one({"_id": product_oid}) if product_oid else None
    product_name = product.get("name", "Product") if product else "Product"
    
    # Get business name safely
    business_name = user.get("profile", {}).get("businessName", "") or ""
    
    whatsapp_message = f"Hi, I'm interested in your {product_name}.\n\nQuantity: {enquiry.quantity}\n"
    if enquiry.message:
        whatsapp_message += f"Message: {enquiry.message}\n"
    whatsapp_message += f"\nFrom: {business_name}\nSent via B2B Marketplace"
    
    return {
        "enquiry_id": str(enquiry_doc["_id"]),
        "message": "Enquiry sent successfully",
        "whatsappLink": f"https://wa.me/{seller_phone}?text={whatsapp_message}" if seller_phone else None
    }

@api_router.get("/enquiries/sent")
async def get_sent_enquiries(user: dict = Depends(require_auth)):
    """Get enquiries sent by current user"""
    pipeline = [
        {"$match": {"buyerId": ObjectId(user["_id"])}},
        {"$lookup": {
            "from": "listings",
            "localField": "listingId",
            "foreignField": "_id",
            "as": "listing"
        }},
        {"$unwind": {"path": "$listing", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "products",
            "localField": "listing.product_id",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"createdAt": -1}}
    ]
    
    enquiries = await db.inquiries.aggregate(pipeline).to_list(100)
    return serialize_doc(enquiries)

@api_router.get("/enquiries/received")
async def get_received_enquiries(user: dict = Depends(require_auth)):
    """Get enquiries received by current user (as seller)"""
    pipeline = [
        {"$match": {"sellerId": ObjectId(user["_id"])}},
        {"$lookup": {
            "from": "listings",
            "localField": "listingId",
            "foreignField": "_id",
            "as": "listing"
        }},
        {"$unwind": {"path": "$listing", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "products",
            "localField": "listing.product_id",
            "foreignField": "_id",
            "as": "product"
        }},
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "users",
            "localField": "buyerId",
            "foreignField": "_id",
            "as": "buyer"
        }},
        {"$unwind": {"path": "$buyer", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"createdAt": -1}}
    ]
    
    enquiries = await db.inquiries.aggregate(pipeline).to_list(100)
    return serialize_doc(enquiries)

@api_router.put("/enquiries/{enquiry_id}/confirm")
async def confirm_enquiry(enquiry_id: str, user: dict = Depends(require_auth)):
    """Confirm an enquiry (seller action) - with proper type handling"""
    # CRITICAL FIX: Validate ObjectId format first
    try:
        enquiry_oid = ObjectId(enquiry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid enquiry ID format")
    
    enquiry = await db.inquiries.find_one({"_id": enquiry_oid})
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    
    # CRITICAL FIX: Normalize both IDs to string for comparison
    seller_id = enquiry.get("sellerId")
    user_id = user.get("_id")
    
    # Convert to string for safe comparison
    if isinstance(seller_id, ObjectId):
        seller_id = str(seller_id)
    elif seller_id is None:
        raise HTTPException(status_code=400, detail="Enquiry has no seller assigned")
    else:
        seller_id = str(seller_id)
    
    if isinstance(user_id, ObjectId):
        user_id = str(user_id)
    else:
        user_id = str(user_id)
    
    if seller_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.inquiries.update_one(
        {"_id": enquiry_oid},
        {"$set": {"status": "confirmed", "updatedAt": datetime.now(timezone.utc)}}
    )
    
    # Create notification for inventory update prompt
    # Store user_id as ObjectId for consistency
    notification_seller_id = enquiry["sellerId"] if isinstance(enquiry["sellerId"], ObjectId) else ObjectId(enquiry["sellerId"])
    await db.notifications.insert_one({
        "_id": ObjectId(),
        "userId": notification_seller_id,  # SSOT: camelCase
        "listingId": enquiry.get("listingId"),
        "type": "inventory_update_prompt",
        "message": "You confirmed an enquiry. Consider updating your inventory.",
        "status": "pending",
        "createdAt": datetime.now(timezone.utc)
    })
    
    return {"message": "Enquiry confirmed. Buyer can now see your contact details."}

@api_router.put("/enquiries/{enquiry_id}/close")
async def close_enquiry(enquiry_id: str, user: dict = Depends(require_auth)):
    """Close an enquiry - with proper type handling"""
    # CRITICAL FIX: Validate ObjectId format first
    try:
        enquiry_oid = ObjectId(enquiry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid enquiry ID format")
    
    enquiry = await db.inquiries.find_one({"_id": enquiry_oid})
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    
    # CRITICAL FIX: Normalize all IDs to string for comparison
    seller_id = enquiry.get("sellerId")
    buyer_id = enquiry.get("buyerId")
    user_id = user.get("_id")
    
    # Convert to string for safe comparison
    if isinstance(seller_id, ObjectId):
        seller_id = str(seller_id)
    else:
        seller_id = str(seller_id) if seller_id else ""
    
    if isinstance(buyer_id, ObjectId):
        buyer_id = str(buyer_id)
    else:
        buyer_id = str(buyer_id) if buyer_id else ""
    
    if isinstance(user_id, ObjectId):
        user_id = str(user_id)
    else:
        user_id = str(user_id)
    
    if seller_id != user_id and buyer_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.inquiries.update_one(
        {"_id": enquiry_oid},
        {"$set": {"status": "closed", "updatedAt": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Enquiry closed"}

# ============== B2B INQUIRY SYSTEM (Standardized) ==============

class InquiryCreate(BaseModel):
    """SSOT: All fields use camelCase - Buyer creates an inquiry for a product/seller"""
    productId: Optional[str] = Field(None, description="Product ID from products collection")
    sellerId: str = Field(..., description="Seller ID")
    listingId: Optional[str] = Field(None, description="Optional: specific listing ID")
    quantity: int = Field(..., ge=1)
    message: Optional[str] = Field(None, max_length=1000, description="Buyer's message/requirement")
    buyerType: Literal["trader", "contractor", "oem", "manufacturer", "other"] = "other"
    locationCity: Optional[str] = Field(None, max_length=100)
    locationState: Optional[str] = Field(None, max_length=100)

# NEW: Standardized inquiry creation endpoint
@api_router.post("/inquiries")
async def create_inquiry(
    inquiry: InquiryCreate, 
    user: dict = Depends(require_auth)
):
    """
    Create a new inquiry from buyer to seller.
    Standardized endpoint replacing /inquiries/b2b.
    
    Buyer info is stored but MASKED until seller accepts.
    
    SSOT POLICY: All foreign keys stored as ObjectId.
    """
    # SSOT: Convert user._id to ObjectId (may come as string from serialization)
    buyer_id = ObjectId(user.get("_id")) if isinstance(user.get("_id"), str) else user.get("_id")
    
    # SSOT: Validate and convert sellerId to ObjectId
    try:
        seller_oid = ObjectId(inquiry.sellerId)
        seller = await db.users.find_one({"_id": seller_oid})
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
    except Exception as e:
        logger.error(f"Invalid sellerId: {inquiry.sellerId}, error: {e}")
        raise HTTPException(status_code=400, detail="Invalid seller ID")
    
    # Check if buyer is not inquiring to themselves
    if buyer_id == seller_oid:
        raise HTTPException(status_code=400, detail="Cannot send inquiry to yourself")
    
    # SSOT: Convert listingId to ObjectId if provided
    listing_oid = None
    listing = None
    product_name = None
    product_oid = None  # Initialize here - will be set from listing or direct productId
    
    if inquiry.listingId:
        try:
            listing_oid = ObjectId(inquiry.listingId)
            listing = await db.sellerListings.find_one({"_id": listing_oid})
            if listing:
                product_name = listing.get("productName")
                
                # CRITICAL FIX: Get productId from listing for "View Product" link
                listing_product_id = listing.get("productId")
                if listing_product_id:
                    product_oid = listing_product_id if isinstance(listing_product_id, ObjectId) else ObjectId(str(listing_product_id))
                    # Also fetch product name from products collection if not in listing
                    if not product_name:
                        product = await db.products.find_one({"_id": product_oid})
                        if product:
                            product_name = product.get("name")
                
                # Verify listing belongs to seller (compare ObjectIds)
                listing_seller = listing.get("sellerId")
                if isinstance(listing_seller, str):
                    listing_seller = ObjectId(listing_seller)
                if listing_seller != seller_oid:
                    raise HTTPException(status_code=400, detail="Listing does not belong to this seller")
        except Exception as e:
            logger.warning(f"Error processing listingId: {e}")
    
    # SSOT: Convert productId to ObjectId if provided directly (fallback if not from listing)
    if inquiry.productId and not product_oid:
        try:
            product_oid = ObjectId(inquiry.productId)
            product = await db.products.find_one({"_id": product_oid})
            if product:
                product_name = product.get("name")
        except Exception:
            pass
    
    now = datetime.now(timezone.utc)
    
    # Build buyer info (stored but masked until accepted)
    buyer_info = {
        "name": user.get("businessName") or user.get("name") or user.get("email", "").split("@")[0],
        "companyName": user.get("businessName"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "city": inquiry.locationCity or user.get("city"),
        "state": inquiry.locationState or user.get("state")
    }
    
    # SSOT: All foreign keys stored as ObjectId
    inquiry_doc = {
        "_id": ObjectId(),
        "productId": product_oid,  # ObjectId or None
        "productName": product_name,
        "listingId": listing_oid,  # ObjectId or None
        "sellerId": seller_oid,    # ObjectId
        "buyerId": buyer_id,       # ObjectId
        "quantity": inquiry.quantity,
        "message": inquiry.message,
        "requirementNote": inquiry.message,  # Backward compatibility
        "buyerType": inquiry.buyerType,
        "buyerInfo": buyer_info,
        "status": "pending",  # pending, accepted, rejected, reported
        "createdAt": now,
        "updatedAt": now
    }
    
    await db.inquiries.insert_one(inquiry_doc)
    
    # Track behavior for ranking boost
    if product_oid and seller_oid:
        try:
            from services.buyer_interaction_service import BuyerInteractionService
            interaction_service = BuyerInteractionService(db)
            await interaction_service.track_inquiry(buyer_id, seller_oid, product_oid)
        except Exception as e:
            logger.warning(f"Failed to track inquiry interaction: {e}")
    
    # ==== SEND EMAIL NOTIFICATIONS ====
    try:
        from services.email_service import get_inquiry_email_service
        email_service = get_inquiry_email_service(db)
        
        # Send buyer confirmation email
        buyer_email = user.get("email")
        buyer_name = user.get("businessName") or user.get("name") or buyer_email.split("@")[0] if buyer_email else "Buyer"
        seller_name = seller.get("businessName") or seller.get("name") or "Seller"
        
        if buyer_email:
            await email_service.send_buyer_inquiry_confirmation(
                to_email=buyer_email,
                buyer_name=buyer_name,
                product_name=product_name or "Product",
                seller_name=seller_name,
                quantity=inquiry.quantity,
                inquiry_id=str(inquiry_doc["_id"])
            )
        
        # Send seller notification email
        seller_email = seller.get("email")
        if seller_email:
            await email_service.send_seller_new_inquiry_notification(
                to_email=seller_email,
                seller_name=seller_name,
                buyer_name=buyer_name,
                buyer_company=user.get("businessName"),
                product_name=product_name or "Product",
                quantity=inquiry.quantity,
                inquiry_id=str(inquiry_doc["_id"]),
                message=inquiry.message
            )
    except Exception as e:
        logger.warning(f"Failed to send inquiry email notifications: {e}")
    
    logger.info(f"Inquiry created: buyer={user.get('email')}, seller={str(seller_oid)}, product={product_name}")
    
    return {
        "success": True,
        "message": "Inquiry sent successfully",
        "inquiryId": str(inquiry_doc["_id"]),
        "status": "pending"
    }

# NEW: Buyer inquiries endpoint
@api_router.get("/buyer/inquiries")
async def get_buyer_inquiries(
    user: dict = Depends(require_auth),
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, rejected"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get all inquiries submitted by the current user (buyer view).
    Shows inquiry status and seller contact if accepted.
    
    SSOT POLICY: Query using ObjectId for foreign keys.
    """
    # SSOT: Convert user._id to ObjectId for query
    buyer_oid = ObjectId(user.get("_id")) if isinstance(user.get("_id"), str) else user.get("_id")
    
    query = {"buyerId": buyer_oid}
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    
    inquiries = await db.inquiries.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.inquiries.count_documents(query)
    
    result = []
    for inq in inquiries:
        inq_id = str(inq["_id"])
        
        # Get listing/product info - SSOT: listing_id is now ObjectId
        listing_info = None
        listing_id = inq.get("listingId")
        listing_product_id = None  # To fix missing productId
        
        if listing_id:
            try:
                # Handle both ObjectId and string (for backward compatibility)
                if isinstance(listing_id, str):
                    listing_id = ObjectId(listing_id)
                listing = await db.sellerListings.find_one({"_id": listing_id})
                if listing:
                    listing_info = {
                        "name": listing.get("productName"),
                        "image": listing.get("images", [None])[0] if listing.get("images") else None,
                        "category": listing.get("categoryName")
                    }
                    # CRITICAL FIX: Get productId from listing for "View Product" link
                    listing_product_id = listing.get("productId")
                    if listing_product_id and isinstance(listing_product_id, ObjectId):
                        listing_product_id = str(listing_product_id)
                    elif listing_product_id:
                        listing_product_id = str(listing_product_id)
            except Exception:
                pass
        
        # Get seller info - SSOT: seller_id is now ObjectId
        seller_info = {"businessName": "Seller"}
        seller_id = inq.get("sellerId")
        if seller_id:
            try:
                # Handle both ObjectId and string (for backward compatibility)
                if isinstance(seller_id, str):
                    seller_id = ObjectId(seller_id)
                seller = await db.users.find_one({"_id": seller_id})
                if seller:
                    # Get profile data (may be nested in 'profile' object)
                    profile = seller.get("profile") or {}
                    
                    seller_info = {
                        "businessName": profile.get("businessName") or seller.get("businessName") or "Verified Seller",
                        "city": profile.get("city") or seller.get("city"),
                        "state": profile.get("state") or seller.get("state")
                    }
                    # Include contact info only if inquiry is accepted
                    if inq.get("status") == "accepted":
                        # Phone can be in profile or top-level
                        phone = profile.get("phone") or seller.get("phone")
                        seller_info["phone"] = phone
                        seller_info["email"] = seller.get("email")
                        seller_info["whatsapp"] = phone  # WhatsApp uses same phone
            except Exception as e:
                logger.warning(f"Error fetching seller info: {e}")
        
        # SSOT: Serialize ObjectId fields to string for API response
        # Use productId from inquiry, or fallback to listing's productId
        product_id_val = inq.get("productId")
        if isinstance(product_id_val, ObjectId):
            product_id_val = str(product_id_val)
        
        # CRITICAL FIX: If inquiry has no productId, use listing's productId
        if not product_id_val and listing_product_id:
            product_id_val = listing_product_id
        
        result.append({
            "_id": inq_id,
            "productId": product_id_val,
            "productName": inq.get("productName") or (listing_info.get("name") if listing_info else None),
            "listing": listing_info,
            "seller": seller_info,
            "quantity": inq.get("quantity"),
            "message": inq.get("message") or inq.get("requirementNote"),
            "status": inq.get("status"),
            "sellerResponse": inq.get("sellerResponse") if inq.get("status") == "accepted" else None,
            "createdAt": inq.get("createdAt").isoformat() if inq.get("createdAt") else None,
            "updatedAt": inq.get("updatedAt").isoformat() if inq.get("updatedAt") else None
        })
    
    # DATA INTEGRITY LOG: Verify response structure
    response_data = {
        "inquiries": result,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total > 0 else 1
    }
    logger.info(f"[DATA INTEGRITY] /api/buyer/inquiries: buyer_id={str(buyer_oid)}, total={total}, page={page}, pages={response_data['pages']}, result_count={len(result)}")
    
    return response_data

# DEPRECATED: Keep for backward compatibility, redirects to new endpoint
class B2BInquiryCreate(BaseModel):
    """SSOT: All fields use camelCase - DEPRECATED, use InquiryCreate"""
    listingId: str
    quantity: int = Field(..., ge=1)
    requirementNote: Optional[str] = Field(None, max_length=1000)
    buyerType: Literal["trader", "contractor", "oem", "manufacturer", "other"] = "other"
    locationCity: Optional[str] = Field(None, max_length=100)
    locationState: Optional[str] = Field(None, max_length=100)

@api_router.post("/inquiries/b2b")
async def create_b2b_inquiry(
    inquiry: B2BInquiryCreate, 
    user: dict = Depends(require_auth)
):
    """
    DEPRECATED: Use POST /api/inquiries instead.
    Kept for backward compatibility.
    """
    # Get sellerId from listing
    try:
        listing = await db.sellerListings.find_one({"_id": ObjectId(inquiry.listingId)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid listing ID")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing.get("status") != "active":
        raise HTTPException(status_code=400, detail="Listing is not available for inquiries")
    
    # SSOT: Use camelCase field names (sellerId, productId)
    seller_oid = listing.get("sellerId")
    product_oid = listing.get("productId")
    
    # Forward to new endpoint logic
    new_inquiry = InquiryCreate(
        productId=str(product_oid) if product_oid else None,
        sellerId=str(seller_oid) if seller_oid else None,
        listingId=inquiry.listingId,
        quantity=inquiry.quantity,
        message=inquiry.requirementNote,
        buyerType=inquiry.buyerType,
        locationCity=inquiry.locationCity,
        locationState=inquiry.locationState
    )
    
    return await create_inquiry(new_inquiry, user)

# DEPRECATED: Keep for backward compatibility
@api_router.get("/inquiries/b2b/my")
async def get_my_b2b_inquiries(
    user: dict = Depends(require_auth),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    DEPRECATED: Use GET /api/buyer/inquiries instead.
    Kept for backward compatibility.
    """
    return await get_buyer_inquiries(user, status, page, limit)

# ============== NOTIFICATION ENDPOINTS ==============

@api_router.get("/notifications")
async def get_notifications(user: dict = Depends(require_auth)):
    """Get user notifications"""
    notifications = await db.notifications.find({
        "user_id": ObjectId(user["_id"]),
        "status": "pending"
    }).sort("createdAt", -1).to_list(50)
    
    return serialize_doc(notifications)

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(require_auth)):
    """Mark notification as read"""
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": ObjectId(user["_id"])},
        {"$set": {"status": "read"}}
    )
    return {"message": "Notification marked as read"}

# ============== SUBSCRIPTION ENDPOINTS ==============

@api_router.get("/subscription")
async def get_subscription(user: dict = Depends(require_auth)):
    """Get current subscription status"""
    return user.get("subscription", {})

@api_router.post("/subscription/subscribe")
async def subscribe(user: dict = Depends(require_auth)):
    """Subscribe to premium (placeholder for payment integration)"""
    # This would integrate with a payment gateway
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {
            "subscription.status": "active",
            "subscription.subscribed_at": datetime.now(timezone.utc),
            "subscription.expires_at": datetime.now(timezone.utc) + timedelta(days=90),
            "subscription.enquiriesThisMonth": 0
        }}
    )
    return {"message": "Subscription activated for 90 days"}

# ============== SEED DATA ENDPOINT ==============

@api_router.post("/admin/seed")
async def seed_data(admin: dict = Depends(require_admin)):
    """Seed initial categories and products (admin only) - Legacy endpoint"""
    # Check if already seeded
    existing = await db.categories.count_documents({})
    if existing > 0:
        return {"message": "Data already seeded"}
    
    # Redirect to new seed endpoint
    return await seed_industrial_catalog_internal()

@api_router.post("/admin/seed-v2")
async def seed_industrial_catalog(admin: dict = Depends(require_admin)):
    """
    Seed industrial product catalog with:
    - Categories
    - Product Families
    - Product Variants
    - Locked Technical Specifications
    """
    return await seed_industrial_catalog_internal()

async def seed_industrial_catalog_internal():
    """
    Seed industrial product catalog with:
    - Categories
    - Product Families
    - Product Variants
    - Locked Technical Specifications
    """
    # Clear existing data for fresh seed
    await db.categories.delete_many({})
    await db.products.delete_many({})
    
    # Industrial Categories with full hierarchy
    catalog = [
        {
            "name": "Electrical Equipment",
            "description": "Motors, transformers, switchgear, and electrical machinery",
            "icon": "flash-outline",
            "families": [
                {
                    "family": "Electric Motor",
                    "variants": [
                        {
                            "variant": "AC Motor",
                            "name": "Three Phase AC Motor",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Phase", "key": "phase", "type": "dropdown", "options": ["Single Phase", "Three Phase"], "required": True},
                                {"name": "Voltage", "key": "voltage", "type": "dropdown", "options": ["220V", "380V", "415V", "440V"], "unit": "V", "required": True},
                                {"name": "Frequency", "key": "frequency", "type": "dropdown", "options": ["50 Hz", "60 Hz"], "required": True},
                                {"name": "Power Rating", "key": "power_rating", "type": "dropdown", "options": ["0.5 HP", "1 HP", "2 HP", "3 HP", "5 HP", "7.5 HP", "10 HP", "15 HP", "20 HP", "25 HP", "30 HP", "40 HP", "50 HP"], "required": True},
                                {"name": "Efficiency Class", "key": "efficiency_class", "type": "dropdown", "options": ["IE1", "IE2", "IE3", "IE4"], "required": False},
                                {"name": "Mounting Type", "key": "mounting_type", "type": "dropdown", "options": ["Foot Mounted", "Flange Mounted", "Foot + Flange"], "required": True},
                                {"name": "RPM", "key": "rpm", "type": "dropdown", "options": ["750", "1000", "1500", "3000"], "required": True}
                            ]
                        },
                        {
                            "variant": "DC Motor",
                            "name": "Brushless DC Motor",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Voltage", "key": "voltage", "type": "dropdown", "options": ["12V", "24V", "48V", "72V", "110V"], "unit": "V", "required": True},
                                {"name": "Power Rating", "key": "power_rating", "type": "dropdown", "options": ["0.25 HP", "0.5 HP", "1 HP", "2 HP", "3 HP", "5 HP"], "required": True},
                                {"name": "Motor Type", "key": "motor_type", "type": "dropdown", "options": ["Brushed", "Brushless"], "required": True},
                                {"name": "RPM", "key": "rpm", "type": "dropdown", "options": ["1000", "1500", "2000", "3000", "4000"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "Power Cable",
                    "variants": [
                        {
                            "variant": "Copper Cable",
                            "name": "Armoured Copper Cable",
                            "unit": "meters",
                            "specSchema": [
                                {"name": "Core Size", "key": "core_size", "type": "dropdown", "options": ["1.5 sq mm", "2.5 sq mm", "4 sq mm", "6 sq mm", "10 sq mm", "16 sq mm", "25 sq mm", "35 sq mm", "50 sq mm", "70 sq mm", "95 sq mm"], "required": True},
                                {"name": "Number of Cores", "key": "cores", "type": "dropdown", "options": ["1 Core", "2 Core", "3 Core", "3.5 Core", "4 Core"], "required": True},
                                {"name": "Voltage Grade", "key": "voltage_grade", "type": "dropdown", "options": ["650V", "1.1kV", "3.3kV", "6.6kV", "11kV"], "required": True},
                                {"name": "Armour Type", "key": "armour", "type": "dropdown", "options": ["Unarmoured", "Steel Wire Armoured", "Steel Tape Armoured"], "required": True},
                                {"name": "Insulation", "key": "insulation", "type": "dropdown", "options": ["PVC", "XLPE", "Rubber"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "Switchgear",
                    "variants": [
                        {
                            "variant": "MCB",
                            "name": "Miniature Circuit Breaker",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Poles", "key": "poles", "type": "dropdown", "options": ["Single Pole", "Double Pole", "Triple Pole", "Four Pole"], "required": True},
                                {"name": "Current Rating", "key": "current_rating", "type": "dropdown", "options": ["6A", "10A", "16A", "20A", "25A", "32A", "40A", "50A", "63A"], "required": True},
                                {"name": "Breaking Capacity", "key": "breaking_capacity", "type": "dropdown", "options": ["6kA", "10kA", "15kA"], "required": True},
                                {"name": "Curve Type", "key": "curve_type", "type": "dropdown", "options": ["B Curve", "C Curve", "D Curve"], "required": True}
                            ]
                        },
                        {
                            "variant": "MCCB",
                            "name": "Moulded Case Circuit Breaker",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Frame Size", "key": "frame_size", "type": "dropdown", "options": ["100A Frame", "160A Frame", "250A Frame", "400A Frame", "630A Frame", "800A Frame"], "required": True},
                                {"name": "Current Rating", "key": "current_rating", "type": "dropdown", "options": ["16A", "25A", "32A", "40A", "50A", "63A", "80A", "100A", "125A", "160A", "200A", "250A", "320A", "400A"], "required": True},
                                {"name": "Breaking Capacity", "key": "breaking_capacity", "type": "dropdown", "options": ["25kA", "36kA", "50kA", "70kA"], "required": True},
                                {"name": "Trip Unit", "key": "trip_unit", "type": "dropdown", "options": ["Thermal Magnetic", "Electronic"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Steel & Metals",
            "description": "Steel products, metal sheets, pipes, and raw materials",
            "icon": "cube-outline",
            "families": [
                {
                    "family": "TMT Bars",
                    "variants": [
                        {
                            "variant": "Fe-500D TMT",
                            "name": "Fe-500D Grade TMT Bars",
                            "unit": "tons",
                            "specSchema": [
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["Fe-415", "Fe-500", "Fe-500D", "Fe-550", "Fe-550D", "Fe-600"], "required": True},
                                {"name": "Diameter", "key": "diameter", "type": "dropdown", "options": ["8mm", "10mm", "12mm", "16mm", "20mm", "25mm", "32mm"], "required": True},
                                {"name": "Length", "key": "length", "type": "dropdown", "options": ["12m Standard", "Custom Cut"], "required": True},
                                {"name": "Standard", "key": "standard", "type": "dropdown", "options": ["IS 1786", "ASTM A615"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "MS Plates",
                    "variants": [
                        {
                            "variant": "Hot Rolled MS Plate",
                            "name": "Hot Rolled Mild Steel Plate",
                            "unit": "kg",
                            "specSchema": [
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["IS 2062 E250", "IS 2062 E350", "ASTM A36", "S275JR", "S355JR"], "required": True},
                                {"name": "Thickness", "key": "thickness", "type": "dropdown", "options": ["3mm", "4mm", "5mm", "6mm", "8mm", "10mm", "12mm", "16mm", "20mm", "25mm"], "required": True},
                                {"name": "Width", "key": "width", "type": "dropdown", "options": ["1250mm", "1500mm", "1800mm", "2000mm"], "required": True},
                                {"name": "Length", "key": "length", "type": "dropdown", "options": ["2500mm", "3000mm", "6000mm", "Custom"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "MS Pipes",
                    "variants": [
                        {
                            "variant": "ERW MS Pipe",
                            "name": "Electric Resistance Welded MS Pipe",
                            "unit": "meters",
                            "specSchema": [
                                {"name": "Outer Diameter", "key": "od", "type": "dropdown", "options": ["15mm", "20mm", "25mm", "32mm", "40mm", "50mm", "65mm", "80mm", "100mm", "150mm"], "required": True},
                                {"name": "Thickness", "key": "thickness", "type": "dropdown", "options": ["1.6mm", "2mm", "2.5mm", "3mm", "3.5mm", "4mm", "5mm", "6mm"], "required": True},
                                {"name": "Length", "key": "length", "type": "dropdown", "options": ["6m Standard", "Custom Length"], "required": True},
                                {"name": "Standard", "key": "standard", "type": "dropdown", "options": ["IS 1239", "IS 3589", "ASTM A53"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "Stainless Steel",
                    "variants": [
                        {
                            "variant": "SS Sheet",
                            "name": "Stainless Steel Sheet",
                            "unit": "kg",
                            "specSchema": [
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["SS 304", "SS 304L", "SS 316", "SS 316L", "SS 202", "SS 430"], "required": True},
                                {"name": "Thickness", "key": "thickness", "type": "dropdown", "options": ["0.5mm", "0.8mm", "1mm", "1.2mm", "1.5mm", "2mm", "3mm", "4mm", "5mm", "6mm"], "required": True},
                                {"name": "Finish", "key": "finish", "type": "dropdown", "options": ["No.1", "2B", "BA", "No.4", "Mirror", "Hairline"], "required": True},
                                {"name": "Width", "key": "width", "type": "dropdown", "options": ["1000mm", "1220mm", "1250mm", "1500mm"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Industrial Chemicals",
            "description": "Solvents, acids, and industrial chemicals",
            "icon": "flask-outline",
            "families": [
                {
                    "family": "Caustic Soda",
                    "variants": [
                        {
                            "variant": "Caustic Soda Flakes",
                            "name": "Sodium Hydroxide Flakes",
                            "unit": "kg",
                            "specSchema": [
                                {"name": "Purity", "key": "purity", "type": "dropdown", "options": ["96%", "98%", "99%"], "required": True},
                                {"name": "Form", "key": "form", "type": "dropdown", "options": ["Flakes", "Pearls", "Lye (Solution)"], "required": True},
                                {"name": "Packaging", "key": "packaging", "type": "dropdown", "options": ["25 kg Bag", "50 kg Bag", "Drum", "Tanker"], "required": True},
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["Technical Grade", "Food Grade", "Pharma Grade"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "Sulphuric Acid",
                    "variants": [
                        {
                            "variant": "Commercial Sulphuric Acid",
                            "name": "Sulphuric Acid H2SO4",
                            "unit": "liters",
                            "specSchema": [
                                {"name": "Concentration", "key": "concentration", "type": "dropdown", "options": ["50%", "70%", "98%", "99%"], "required": True},
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["Commercial", "CP Grade", "AR Grade", "Battery Grade"], "required": True},
                                {"name": "Packaging", "key": "packaging", "type": "dropdown", "options": ["Carboy", "Drum", "IBC", "Tanker"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Building Materials",
            "description": "Cement, bricks, sand, and construction materials",
            "icon": "business-outline",
            "families": [
                {
                    "family": "Cement",
                    "variants": [
                        {
                            "variant": "OPC Cement",
                            "name": "Ordinary Portland Cement",
                            "unit": "bags",
                            "specSchema": [
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["OPC 33", "OPC 43", "OPC 53"], "required": True},
                                {"name": "Brand", "key": "brand", "type": "dropdown", "options": ["UltraTech", "ACC", "Ambuja", "Shree", "Dalmia", "JK Cement", "Birla", "Other"], "required": True},
                                {"name": "Bag Size", "key": "bag_size", "type": "dropdown", "options": ["50 kg"], "required": True},
                                {"name": "Standard", "key": "standard", "type": "dropdown", "options": ["IS 269", "IS 8112", "IS 12269"], "required": True}
                            ]
                        },
                        {
                            "variant": "PPC Cement",
                            "name": "Portland Pozzolana Cement",
                            "unit": "bags",
                            "specSchema": [
                                {"name": "Type", "key": "type", "type": "dropdown", "options": ["Fly Ash Based", "Calcined Clay Based"], "required": True},
                                {"name": "Brand", "key": "brand", "type": "dropdown", "options": ["UltraTech", "ACC", "Ambuja", "Shree", "Dalmia", "JK Cement", "Birla", "Other"], "required": True},
                                {"name": "Bag Size", "key": "bag_size", "type": "dropdown", "options": ["50 kg"], "required": True},
                                {"name": "Standard", "key": "standard", "type": "dropdown", "options": ["IS 1489 Part 1", "IS 1489 Part 2"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "Ready Mix Concrete",
                    "variants": [
                        {
                            "variant": "Standard RMC",
                            "name": "Ready Mix Concrete",
                            "unit": "cubic meters",
                            "specSchema": [
                                {"name": "Grade", "key": "grade", "type": "dropdown", "options": ["M10", "M15", "M20", "M25", "M30", "M35", "M40", "M45", "M50"], "required": True},
                                {"name": "Slump", "key": "slump", "type": "dropdown", "options": ["25-50mm", "50-75mm", "75-100mm", "100-150mm", "150-200mm"], "required": True},
                                {"name": "Max Aggregate Size", "key": "aggregate_size", "type": "dropdown", "options": ["10mm", "20mm", "40mm"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Bearings & Transmission",
            "description": "Ball bearings, roller bearings, belts, and power transmission",
            "icon": "settings-outline",
            "families": [
                {
                    "family": "Ball Bearings",
                    "variants": [
                        {
                            "variant": "Deep Groove Ball Bearing",
                            "name": "DGBB Ball Bearing",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Bore Diameter", "key": "bore_dia", "type": "dropdown", "options": ["10mm", "12mm", "15mm", "17mm", "20mm", "25mm", "30mm", "35mm", "40mm", "50mm", "60mm", "70mm", "80mm"], "required": True},
                                {"name": "Series", "key": "series", "type": "dropdown", "options": ["6000", "6200", "6300", "6400"], "required": True},
                                {"name": "Shield Type", "key": "shield", "type": "dropdown", "options": ["Open", "ZZ (Metal Shield)", "2RS (Rubber Seal)"], "required": True},
                                {"name": "Brand", "key": "brand", "type": "dropdown", "options": ["SKF", "FAG", "NSK", "NTN", "Timken", "NBC", "ZKL", "Other"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "V-Belts",
                    "variants": [
                        {
                            "variant": "Classical V-Belt",
                            "name": "Classical Section V-Belt",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Section", "key": "section", "type": "dropdown", "options": ["A Section", "B Section", "C Section", "D Section", "E Section"], "required": True},
                                {"name": "Length", "key": "length", "type": "dropdown", "options": ["20\"", "25\"", "30\"", "35\"", "40\"", "45\"", "50\"", "55\"", "60\"", "70\"", "80\"", "90\"", "100\"", "Custom"], "required": True},
                                {"name": "Brand", "key": "brand", "type": "dropdown", "options": ["Fenner", "Gates", "Optibelt", "PIX", "Continental", "Other"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Safety & PPE",
            "description": "Personal protective equipment and safety gear",
            "icon": "shield-outline",
            "families": [
                {
                    "family": "Safety Helmets",
                    "variants": [
                        {
                            "variant": "Industrial Safety Helmet",
                            "name": "Hard Hat Safety Helmet",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Type", "key": "type", "type": "dropdown", "options": ["Type I (Top Impact)", "Type II (Top + Side Impact)"], "required": True},
                                {"name": "Shell Material", "key": "material", "type": "dropdown", "options": ["HDPE", "ABS", "Fiberglass"], "required": True},
                                {"name": "Suspension", "key": "suspension", "type": "dropdown", "options": ["Ratchet", "Pin Lock", "Push Key"], "required": True},
                                {"name": "Standard", "key": "standard", "type": "dropdown", "options": ["IS 2925", "ANSI Z89.1", "EN 397"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "Safety Shoes",
                    "variants": [
                        {
                            "variant": "Steel Toe Safety Shoe",
                            "name": "Steel Toe Industrial Safety Shoe",
                            "unit": "pairs",
                            "specSchema": [
                                {"name": "Size Range", "key": "size", "type": "dropdown", "options": ["6", "7", "8", "9", "10", "11", "12"], "required": True},
                                {"name": "Toe Cap", "key": "toe_cap", "type": "dropdown", "options": ["Steel Toe", "Composite Toe", "Aluminum Toe"], "required": True},
                                {"name": "Sole Type", "key": "sole", "type": "dropdown", "options": ["PU Sole", "Rubber Sole", "PU/Rubber Double Density"], "required": True},
                                {"name": "Standard", "key": "standard", "type": "dropdown", "options": ["IS 15298", "EN ISO 20345", "ASTM F2413"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Packaging Materials",
            "description": "Boxes, tapes, films, and packaging supplies",
            "icon": "cube-outline",
            "families": [
                {
                    "family": "Corrugated Boxes",
                    "variants": [
                        {
                            "variant": "3-Ply Corrugated Box",
                            "name": "3-Ply Corrugated Carton",
                            "unit": "pieces",
                            "specSchema": [
                                {"name": "Ply", "key": "ply", "type": "dropdown", "options": ["3 Ply", "5 Ply", "7 Ply"], "required": True},
                                {"name": "Flute Type", "key": "flute", "type": "dropdown", "options": ["A Flute", "B Flute", "C Flute", "E Flute", "BC Flute"], "required": True},
                                {"name": "GSM", "key": "gsm", "type": "dropdown", "options": ["100 GSM", "120 GSM", "150 GSM", "180 GSM", "200 GSM"], "required": True},
                                {"name": "Box Type", "key": "box_type", "type": "dropdown", "options": ["Regular Slotted", "Half Slotted", "Die Cut", "Custom"], "required": True}
                            ]
                        }
                    ]
                },
                {
                    "family": "BOPP Tape",
                    "variants": [
                        {
                            "variant": "Brown BOPP Tape",
                            "name": "Brown Packing Tape",
                            "unit": "rolls",
                            "specSchema": [
                                {"name": "Width", "key": "width", "type": "dropdown", "options": ["24mm", "36mm", "48mm", "72mm"], "required": True},
                                {"name": "Length", "key": "length", "type": "dropdown", "options": ["40m", "65m", "100m", "200m"], "required": True},
                                {"name": "Micron", "key": "micron", "type": "dropdown", "options": ["38 micron", "40 micron", "45 micron", "48 micron"], "required": True},
                                {"name": "Color", "key": "color", "type": "dropdown", "options": ["Brown", "Transparent", "White", "Custom Print"], "required": True}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    
    # Insert data
    for cat_data in catalog:
        cat_doc = {
            "_id": ObjectId(),
            "name": cat_data["name"],
            "description": cat_data["description"],
            "icon": cat_data["icon"],
            "createdAt": datetime.now(timezone.utc),
            "active": True
        }
        await db.categories.insert_one(cat_doc)
        
        for family_data in cat_data.get("families", []):
            for variant_data in family_data.get("variants", []):
                prod_doc = {
                    "_id": ObjectId(),
                    "category_id": cat_doc["_id"],
                    "family": family_data["family"],
                    "variant": variant_data["variant"],
                    "name": variant_data["name"],
                    "description": f"{variant_data['name']} - Industrial Grade",
                    "unit": variant_data["unit"],
                    "standardParameters": [spec["key"] for spec in variant_data.get("specSchema", [])],
                    "specSchema": variant_data.get("specSchema", []),
                    "createdAt": datetime.now(timezone.utc),
                    "active": True
                }
                await db.products.insert_one(prod_doc)
    
    # Count inserted
    cat_count = await db.categories.count_documents({})
    prod_count = await db.products.count_documents({})
    
    return {
        "message": "Industrial catalog seeded successfully",
        "categories": cat_count,
        "products": prod_count
    }

# ============== ADMIN MANAGEMENT ENDPOINTS ==============

# === Admin Pydantic Models ===

class AdminCategoryCreate(BaseModel):
    """
    Create a new category (admin only).
    SSOT: All fields use camelCase to match database schema.
    """
    name: str = Field(..., min_length=2, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    imageUrl: Optional[str] = Field(None, description="Category image URL (Firebase URL)")
    displayOrder: Optional[int] = Field(0, ge=0, description="Display order for sorting")

class AdminCategoryUpdate(BaseModel):
    """
    Update a category (admin only).
    SSOT: All fields use camelCase to match database schema.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    imageUrl: Optional[str] = Field(None, description="Category image URL (Firebase URL)")
    displayOrder: Optional[int] = Field(None, ge=0)
    isActive: Optional[bool] = None

class SpecField(BaseModel):
    """
    Specification field definition for templates.
    SSOT: All fields use camelCase to match database schema.
    """
    key: str = Field(..., description="Unique field key (e.g., 'power', 'voltage')")
    label: str = Field(..., description="Display label")
    fieldType: str = Field(..., description="Field type: text, number, dropdown, boolean")
    unit: Optional[str] = Field(None, description="Unit of measurement (kg, mm, volt)")
    options: Optional[List[str]] = Field(None, description="Options for dropdown type")
    required: bool = Field(False, description="Whether field is required")
    displayOrder: int = Field(0, ge=0, description="Display order")

class AdminSpecTemplateCreate(BaseModel):
    """
    Create a specification template (admin only).
    SSOT: All fields use camelCase to match database schema.
    """
    name: str = Field(..., min_length=2, max_length=100)
    categoryId: str = Field(..., description="Category ID (ObjectId string)")
    fields: List[SpecField]

class AdminSpecTemplateUpdate(BaseModel):
    """
    Update a specification template (admin only).
    SSOT: All fields use camelCase to match database schema.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    fields: Optional[List[SpecField]] = None
    isActive: Optional[bool] = None

class AdminProductCreate(BaseModel):
    """
    Admin creates products as structural definitions (templates) only.
    Products define WHAT can be sold, not WHO sells it or for HOW MUCH.
    
    ARCHITECTURAL RULE:
    - Admin creates product TEMPLATE with: name, categoryId, coverImageUrl, description
    - Seller creates LISTING with: productId, sellerId, images, price (pricing.slabs)
    - Price belongs to SELLER, NOT to PRODUCT
    
    SSOT: All fields use camelCase to match database schema.
    
    SYSTEM FIELDS (generated by backend, NOT accepted from frontend):
    - isActive, createdAt, updatedAt, createdBy, categoryName
    """
    # Required user-provided fields
    name: str = Field(..., min_length=2, max_length=200, description="Product name")
    categoryId: str = Field(..., description="Category ID (ObjectId string)")
    
    # Optional user-provided fields
    coverImageUrl: Optional[str] = Field(None, description="Product cover image URL (Cloudinary URL)")
    description: Optional[str] = Field(None, max_length=2000, description="Product description")
    specTemplateIds: List[str] = Field(default_factory=list, description="IDs of spec templates for this product")
    family: Optional[str] = Field(None, max_length=100)
    variant: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20, description="Unit of measurement")
    
    @field_validator('coverImageUrl')
    @classmethod
    def validate_cloudinary_url(cls, v):
        if v is None or v == '':
            return None
        # Validate Cloudinary URL format
        CLOUDINARY_CLOUD_NAME = 'dco24qmoq'
        valid_prefix = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/'
        if not v.startswith(valid_prefix):
            raise ValueError(f'Invalid image URL. Must be from Cloudinary (start with {valid_prefix})')
        return v

class AdminProductUpdate(BaseModel):
    """Update a product definition (admin only) - SSOT: camelCase"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    specTemplateIds: Optional[List[str]] = None
    family: Optional[str] = None
    variant: Optional[str] = None
    coverImageUrl: Optional[str] = None
    unit: Optional[str] = None
    isActive: Optional[bool] = None
    
    @field_validator('coverImageUrl')
    @classmethod
    def validate_cloudinary_url(cls, v):
        if v is None or v == '':
            return None
        # Validate Cloudinary URL format
        CLOUDINARY_CLOUD_NAME = 'dco24qmoq'
        valid_prefix = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/'
        if not v.startswith(valid_prefix):
            raise ValueError(f'Invalid image URL. Must be from Cloudinary (start with {valid_prefix})')
        return v

# === Category Admin Endpoints ===

@api_router.get("/admin/categories")
async def admin_list_categories(
    admin: dict = Depends(require_admin),
    include_inactive: bool = Query(False)
):
    """List all categories (admin only)"""
    query = {} if include_inactive else {"isActive": {"$ne": False}}  # SSOT: camelCase
    categories = await db.categories.find(query).sort("display_order", 1).to_list(length=100)
    
    # Safe serialization and add counts
    serialized_categories = []
    for cat in categories:
        serialized = serialize_mongo_doc(cat)
        # SSOT: Query with both categoryId (ObjectId) and category_id (string) for backward compatibility
        cat_oid = cat["_id"]
        cat_str = str(cat["_id"])
        serialized["productCount"] = await db.products.count_documents({
            "$or": [
                {"categoryId": cat_oid},
                {"category_id": cat_str}
            ]
        })
        # SSOT: Use seller_listings collection
        serialized["listingCount"] = await db.sellerListings.count_documents({"status": "active"})
        serialized_categories.append(serialized)
    
    return {"categories": serialized_categories, "total": len(serialized_categories)}

@api_router.post("/admin/categories")
async def admin_create_category(
    category: AdminCategoryCreate,
    admin: dict = Depends(require_admin)
):
    """Create a new category (admin only) - SSOT: camelCase"""
    # Check for duplicate name
    existing = await db.categories.find_one({"name": {"$regex": f"^{category.name}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    now = datetime.now(timezone.utc)
    category_doc = {
        "_id": ObjectId(),
        "name": category.name,
        "description": category.description,
        "imageUrl": category.imageUrl,  # SSOT: camelCase - Firebase URL
        "displayOrder": category.displayOrder or 0,  # SSOT: camelCase
        "isActive": True,
        "createdAt": now,
        "createdBy": admin["_id"],  # ObjectId
        "updatedAt": now
    }
    
    await db.categories.insert_one(category_doc)
    
    # Safe serialization
    serialized = serialize_mongo_doc(category_doc)
    
    logger.info(f"Admin {admin['email']} created category: {category.name}")
    return {"message": "Category created successfully", "category": serialized}

@api_router.patch("/admin/categories/{category_id}")
async def admin_update_category(
    category_id: str,
    updates: AdminCategoryUpdate,
    admin: dict = Depends(require_admin)
):
    """Update a category (admin only) - SSOT: camelCase"""
    existing = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = {"updatedAt": datetime.now(timezone.utc)}  # SSOT: camelCase
    
    if updates.name is not None:
        # Check for duplicate name
        dup = await db.categories.find_one({
            "_id": {"$ne": ObjectId(category_id)},
            "name": {"$regex": f"^{updates.name}$", "$options": "i"}
        })
        if dup:
            raise HTTPException(status_code=400, detail="Category with this name already exists")
        update_data["name"] = updates.name
    
    if updates.description is not None:
        update_data["description"] = updates.description
    if updates.imageUrl is not None:
        update_data["imageUrl"] = updates.imageUrl  # SSOT: camelCase - Firebase URL
    if updates.displayOrder is not None:
        update_data["displayOrder"] = updates.displayOrder  # SSOT: camelCase
    
    await db.categories.update_one({"_id": ObjectId(category_id)}, {"$set": update_data})
    
    updated = await db.categories.find_one({"_id": ObjectId(category_id)})
    serialized = serialize_mongo_doc(updated)
    
    logger.info(f"Admin {admin['email']} updated category: {category_id}")
    return {"message": "Category updated successfully", "category": serialized}


# ============== SECURE IMAGE UPLOAD ENDPOINTS ==============

@api_router.post("/admin/upload/category-image")
@limiter.limit("10/minute")
async def admin_upload_category_image(
    request: Request,
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin)
):
    """
    Upload a category image (admin only).
    
    Security:
    - Only JPEG, PNG, WEBP allowed
    - Max 1MB
    - Image validated and re-encoded
    - Stored as data URL
    
    Returns: { image_url: "data:image/jpeg;base64,..." }
    """
    # Read file content
    content = await file.read()
    
    # Validate and process
    processed_image, mime_type = validate_and_process_image(
        file_content=content,
        file_type=file.content_type or 'application/octet-stream',
        max_size=IMAGE_SIZE_LIMITS['category'],
        context="category image"
    )
    
    # Convert to data URL
    image_url = image_to_data_url(processed_image, mime_type)
    
    logger.info(f"Admin {admin['email']} uploaded category image ({len(processed_image)} bytes)")
    
    return {
        "imageUrl": image_url,
        "sizeBytes": len(processed_image),
        "message": "Image uploaded successfully"
    }


@api_router.post("/upload/product-images")
@limiter.limit("20/minute")
async def upload_product_images(
    request: Request,
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_auth)
):
    """
    Upload product images (sellers only) with automatic optimization.
    
    Processing Pipeline:
    1. Validate MIME type and file header
    2. Verify image integrity
    3. Check minimum dimensions (600x600)
    4. Resize to max dimensions (1600x1600)
    5. Strip EXIF metadata (security)
    6. Compress to 100-300KB as WEBP
    
    Rules:
    - Only JPEG, PNG, WEBP input allowed
    - Max 3MB upload per image (compressed to ~200KB)
    - 1-5 images per product
    
    Returns: { images: ["data:image/webp;base64,..."], sizes_kb: [...] }
    """
    # Check if user is a seller
    if not user.get("isSeller"):
        raise HTTPException(
            status_code=403,
            detail="Only sellers can upload product images"
        )
    
    # Check image count
    if len(files) > MAX_IMAGES_PER_PRODUCT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_IMAGES_PER_PRODUCT} images allowed per product"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one image is required"
        )
    
    image_urls = []
    sizes_kb = []
    
    for idx, file in enumerate(files):
        try:
            content = await file.read()
            
            # Validate and process with WEBP compression
            processed_image, mime_type = validate_and_process_product_image(
                file_content=content,
                file_type=file.content_type or 'application/octet-stream'
            )
            
            # Convert to data URL
            image_url = image_to_data_url(processed_image, mime_type)
            image_urls.append(image_url)
            sizes_kb.append(round(len(processed_image) / 1024, 1))
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing image {idx + 1}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image {idx + 1}: {str(e)}"
            )
    
    total_size_kb = sum(sizes_kb)
    logger.info(f"Seller {user.get('email')} uploaded {len(image_urls)} images ({total_size_kb:.1f}KB total)")
    
    return {
        "images": image_urls,
        "count": len(image_urls),
        "sizesKb": sizes_kb,
        "total_size_kb": total_size_kb,
        "message": f"{len(image_urls)} image(s) optimized and uploaded successfully"
    }


@api_router.post("/upload/datasheet")
@limiter.limit("10/minute")
async def upload_datasheet(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(require_auth)
):
    """
    Upload a product datasheet (PDF only).
    
    Rules:
    - Only PDF files allowed
    - Max 10MB file size
    - Returns base64 data URL
    """
    # Check if user is a seller
    if not user.get("isSeller"):
        raise HTTPException(
            status_code=403,
            detail="Only sellers can upload datasheets"
        )
    
    # Validate file type
    content_type = file.content_type or ''
    filename = (file.filename or '').lower()
    
    if content_type != 'application/pdf' and not filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed for datasheets"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="Datasheet file too large. Maximum size: 10MB"
        )
    
    # Verify it's actually a PDF (check magic bytes)
    if not content.startswith(b'%PDF'):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file"
        )
    
    # Convert to base64 data URL
    import base64
    b64_content = base64.b64encode(content).decode('utf-8')
    data_url = f"data:application/pdf;base64,{b64_content}"
    
    size_kb = len(content) / 1024
    logger.info(f"Seller {user.get('email')} uploaded datasheet ({size_kb:.1f}KB)")
    
    return {
        "url": data_url,
        "sizeKb": round(size_kb, 1),
        "filename": file.filename,
        "message": "Datasheet uploaded successfully"
    }


@api_router.delete("/admin/categories/{category_id}")
async def admin_delete_category(
    category_id: str,
    force: bool = Query(False),
    admin: dict = Depends(require_admin)
):
    """Soft-delete a category (admin only). Blocked if products/listings exist unless force=true."""
    existing = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check for existing products - SSOT: Use seller_listings for listing count
    product_count = await db.products.count_documents({"category_id": category_id})
    listing_count = await db.sellerListings.count_documents({"status": "active"})
    
    if (product_count > 0 or listing_count > 0) and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category. It has {product_count} products and {listing_count} listings. Use force=true to soft-delete anyway."
        )
    
    # Soft delete (set isActive = False) - SSOT: camelCase
    await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {
            "isActive": False,
            "deletedAt": datetime.now(timezone.utc),
            "deletedBy": str(admin["_id"])
        }}
    )
    
    logger.info(f"Admin {admin['email']} soft-deleted category: {category_id}")
    return {"message": "Category deactivated successfully"}

# === Spec Template Admin Endpoints ===

@api_router.get("/admin/spec-templates")
async def admin_list_spec_templates(
    admin: dict = Depends(require_admin),
    category_id: Optional[str] = None,
    include_inactive: bool = Query(False)
):
    """List all specification templates (admin only)"""
    query = {}
    if not include_inactive:
        query["isActive"] = {"$ne": False}  # SSOT: camelCase
    if category_id:
        query["categoryId"] = category_id  # SSOT: camelCase
    
    templates = await db.specTemplates.find(query).to_list(length=100)
    
    # Safe serialization
    serialized_templates = []
    for template in templates:
        serialized = serialize_mongo_doc(template)
        # Get category name
        try:
            cat = await db.categories.find_one({"_id": ObjectId(template.get("category_id", ""))})
            serialized["categoryName"] = cat["name"] if cat else "Unknown"
        except Exception:
            serialized["categoryName"] = "Unknown"
        serialized_templates.append(serialized)
    
    return {"templates": serialized_templates, "total": len(serialized_templates)}

@api_router.get("/admin/spec-templates/{template_id}")
async def admin_get_spec_template(
    template_id: str,
    admin: dict = Depends(require_admin)
):
    """Get a specific spec template (admin only)"""
    try:
        template = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID format")
    
    if not template:
        raise HTTPException(status_code=404, detail="Spec template not found")
    
    # Safe serialization
    serialized = serialize_mongo_doc(template)
    try:
        cat = await db.categories.find_one({"_id": ObjectId(template.get("category_id", ""))})
        serialized["categoryName"] = cat["name"] if cat else "Unknown"
    except Exception:
        serialized["categoryName"] = "Unknown"
    
    return {"template": serialized}

@api_router.post("/admin/spec-templates")
async def admin_create_spec_template(
    template: AdminSpecTemplateCreate,
    admin: dict = Depends(require_admin)
):
    """Create a new specification template (admin only)"""
    # Verify category exists - SSOT: use camelCase field
    category = await db.categories.find_one({"_id": ObjectId(template.categoryId)})
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    
    category_oid = ObjectId(template.categoryId)
    
    # Check for duplicate name in same category - SSOT: use camelCase
    existing = await db.specTemplates.find_one({
        "categoryId": category_oid,
        "name": {"$regex": f"^{template.name}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(status_code=400, detail="Spec template with this name already exists in this category")
    
    template_doc = {
        "_id": ObjectId(),
        "name": template.name,
        "categoryId": category_oid,  # FIXED: Store as ObjectId
        "fields": [field.model_dump() for field in template.fields],
        "isActive": True,  # SSOT: camelCase
        "createdAt": datetime.now(timezone.utc),
        "createdBy": str(admin["_id"]),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.specTemplates.insert_one(template_doc)
    
    # Safe serialization
    serialized = serialize_mongo_doc(template_doc)
    
    logger.info(f"Admin {admin['email']} created spec template: {template.name}")
    return {"message": "Spec template created successfully", "template": serialized}

@api_router.patch("/admin/spec-templates/{template_id}")
async def admin_update_spec_template(
    template_id: str,
    updates: AdminSpecTemplateUpdate,
    admin: dict = Depends(require_admin)
):
    """Update a specification template (admin only)"""
    try:
        existing = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID format")
    
    if not existing:
        raise HTTPException(status_code=404, detail="Spec template not found")
    
    update_data = {"updatedAt": datetime.now(timezone.utc)}  # SSOT: camelCase
    
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.fields is not None:
        update_data["fields"] = [field.model_dump() for field in updates.fields]
    if updates.isActive is not None:
        update_data["isActive"] = updates.isActive  # SSOT: camelCase in DB
    
    await db.specTemplates.update_one({"_id": ObjectId(template_id)}, {"$set": update_data})
    
    updated = await db.specTemplates.find_one({"_id": ObjectId(template_id)})
    serialized = serialize_mongo_doc(updated)
    
    logger.info(f"Admin {admin['email']} updated spec template: {template_id}")
    return {"message": "Spec template updated successfully", "template": serialized}
# GET SPEC TEMPLATE BY ID
# ===============================
@api_router.get("/spec-templates/{template_id}")
async def get_spec_template(template_id: str):
    try:
        template = await db.specTemplates.find_one(
            {"_id": ObjectId(template_id)}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    if not template:
        raise HTTPException(status_code=404, detail="Spec template not found")

    return serialize_mongo_doc(template)

    
@api_router.delete("/admin/spec-templates/{template_id}")
async def admin_delete_spec_template(
    template_id: str,
    force: bool = Query(False),
    admin: dict = Depends(require_admin)
):
    """
    Soft-delete a spec template (admin only).
    
    ARCHITECTURAL FIX: Automatically removes template reference from all products.
    """

    # Validate ObjectId
    try:
        template_oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    # Check if template exists
    existing = await db.specTemplates.find_one({"_id": template_oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Spec template not found")

    # Count products using this template
    product_count = await db.products.count_documents({
        "specTemplateIds": template_oid
    })

    if product_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete spec template. {product_count} products use this template. Use force=true to soft-delete anyway."
        )

    # ARCHITECTURAL FIX: Remove template reference from all products
    # This ensures no orphan references
    cleanup_result = await db.products.update_many(
        {"specTemplateIds": template_oid},
        {"$pull": {"specTemplateIds": template_oid}}
    )
    
    if cleanup_result.modified_count > 0:
        logger.info(f"Cleaned up template reference from {cleanup_result.modified_count} products")

    # Soft delete the template
    await db.specTemplates.update_one(
        {"_id": template_oid},
        {"$set": {
            "isActive": False,
            "deletedAt": datetime.now(timezone.utc),
            "deletedBy": str(admin["_id"])
        }}
    )

    logger.info(f"Admin {admin['email']} soft-deleted spec template: {template_id}")

    return {
        "message": "Spec template deactivated successfully",
        "productsUpdated": cleanup_result.modified_count
    }


@api_router.post("/admin/products/cleanup-template-refs")
async def admin_cleanup_template_refs(
    admin: dict = Depends(require_admin)
):
    """
    ARCHITECTURAL FIX: Cleanup invalid template references from all products.
    
    This endpoint:
    1. Gets all valid template IDs from specTemplates collection
    2. Scans all products with specTemplateIds
    3. Removes any template IDs that don't exist or are inactive
    4. Returns summary of cleanup
    
    Run this once to fix existing data integrity issues.
    """
    # Get all valid template IDs (active templates)
    valid_templates = await db.specTemplates.find(
        {"isActive": {"$ne": False}},
        {"_id": 1, "categoryId": 1}
    ).to_list(length=None)
    
    valid_template_ids = {str(t["_id"]): str(t.get("categoryId", "")) for t in valid_templates}
    
    # Find all products with specTemplateIds
    products = await db.products.find(
        {"specTemplateIds": {"$exists": True, "$ne": []}},
        {"_id": 1, "name": 1, "categoryId": 1, "specTemplateIds": 1}
    ).to_list(length=None)
    
    cleaned_count = 0
    invalid_refs_removed = 0
    category_mismatch_removed = 0
    products_cleaned = []
    
    for product in products:
        product_id = product["_id"]
        product_category = str(product.get("categoryId", ""))
        current_template_ids = product.get("specTemplateIds", [])
        
        valid_for_product = []
        removed = []
        
        for tid in current_template_ids:
            tid_str = str(tid)
            
            # Check if template exists and is active
            if tid_str not in valid_template_ids:
                removed.append({"id": tid_str, "reason": "not_found_or_inactive"})
                invalid_refs_removed += 1
                continue
            
            # Check category match
            template_category = valid_template_ids[tid_str]
            if template_category and template_category != product_category:
                removed.append({"id": tid_str, "reason": "category_mismatch"})
                category_mismatch_removed += 1
                continue
            
            # Valid
            valid_for_product.append(tid)
        
        # Update product if any templates were removed
        if len(valid_for_product) != len(current_template_ids):
            await db.products.update_one(
                {"_id": product_id},
                {"$set": {"specTemplateIds": valid_for_product}}
            )
            cleaned_count += 1
            products_cleaned.append({
                "productId": str(product_id),
                "name": product.get("name", "Unknown"),
                "removed": removed
            })
    
    logger.info(f"Admin {admin['email']} ran template cleanup: {cleaned_count} products cleaned")
    
    return {
        "message": f"Cleanup complete. {cleaned_count} products updated.",
        "summary": {
            "productsScanned": len(products),
            "productsCleaned": cleaned_count,
            "invalidRefsRemoved": invalid_refs_removed,
            "categoryMismatchRemoved": category_mismatch_removed,
            "validTemplatesCount": len(valid_template_ids)
        },
        "details": products_cleaned if cleaned_count <= 50 else f"{cleaned_count} products cleaned (details truncated)"
    }


@api_router.post("/admin/data-integrity/migrate")
async def admin_data_integrity_migration(
    admin: dict = Depends(require_admin)
):
    """
    ENTERPRISE DATA INTEGRITY MIGRATION
    
    This endpoint performs a comprehensive database migration:
    
    STEP 1: Convert specTemplates.categoryId string → ObjectId
    STEP 2: Convert products.categoryId string → ObjectId
    STEP 3: Remove orphan template references from products
    STEP 4: Enforce category matching (remove cross-category refs)
    
    Run this ONCE to fix all existing data integrity issues.
    """
    results = {
        "step1_specTemplates_categoryId_converted": 0,
        "step2_products_categoryId_converted": 0,
        "step3_orphan_refs_removed": 0,
        "step4_category_mismatch_removed": 0,
        "errors": []
    }
    
    # STEP 1: Convert specTemplates.categoryId string → ObjectId
    try:
        spec_templates = await db.specTemplates.find({}).to_list(length=None)
        for template in spec_templates:
            category_id = template.get("categoryId")
            if category_id and isinstance(category_id, str):
                try:
                    # Convert string to ObjectId
                    await db.specTemplates.update_one(
                        {"_id": template["_id"]},
                        {"$set": {"categoryId": ObjectId(category_id)}}
                    )
                    results["step1_specTemplates_categoryId_converted"] += 1
                except Exception as e:
                    results["errors"].append(f"Template {template['_id']}: {str(e)}")
    except Exception as e:
        results["errors"].append(f"Step 1 error: {str(e)}")
    
    # STEP 2: Convert products.categoryId string → ObjectId
    try:
        products = await db.products.find({}).to_list(length=None)
        for product in products:
            category_id = product.get("categoryId")
            if category_id and isinstance(category_id, str):
                try:
                    await db.products.update_one(
                        {"_id": product["_id"]},
                        {"$set": {"categoryId": ObjectId(category_id)}}
                    )
                    results["step2_products_categoryId_converted"] += 1
                except Exception as e:
                    results["errors"].append(f"Product {product['_id']}: {str(e)}")
    except Exception as e:
        results["errors"].append(f"Step 2 error: {str(e)}")
    
    # STEP 3: Remove orphan template references
    try:
        # Get all valid template IDs
        valid_templates = await db.specTemplates.find(
            {"isActive": {"$ne": False}},
            {"_id": 1}
        ).to_list(length=None)
        valid_template_ids = set(str(t["_id"]) for t in valid_templates)
        
        # Scan products
        products = await db.products.find(
            {"specTemplateIds": {"$exists": True, "$ne": []}}
        ).to_list(length=None)
        
        for product in products:
            current_ids = product.get("specTemplateIds", [])
            valid_ids = [
                tid for tid in current_ids
                if str(tid) in valid_template_ids
            ]
            
            if len(valid_ids) != len(current_ids):
                orphan_count = len(current_ids) - len(valid_ids)
                results["step3_orphan_refs_removed"] += orphan_count
                await db.products.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"specTemplateIds": valid_ids}}
                )
    except Exception as e:
        results["errors"].append(f"Step 3 error: {str(e)}")
    
    # STEP 4: Enforce category matching
    try:
        # Refresh products after step 3
        products = await db.products.find(
            {"specTemplateIds": {"$exists": True, "$ne": []}}
        ).to_list(length=None)
        
        for product in products:
            product_category = product.get("categoryId")
            if not product_category:
                continue
            
            product_category_str = str(product_category)
            current_ids = product.get("specTemplateIds", [])
            
            # Find valid templates matching category
            valid_for_category = []
            for tid in current_ids:
                template = await db.specTemplates.find_one({"_id": tid})
                if template:
                    template_category = template.get("categoryId")
                    if template_category and str(template_category) == product_category_str:
                        valid_for_category.append(tid)
                    else:
                        results["step4_category_mismatch_removed"] += 1
            
            if len(valid_for_category) != len(current_ids):
                await db.products.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"specTemplateIds": valid_for_category}}
                )
    except Exception as e:
        results["errors"].append(f"Step 4 error: {str(e)}")
    
    logger.info(f"Admin {admin['email']} ran data integrity migration: {results}")
    
    return {
        "message": "Data integrity migration complete",
        "results": results,
        "totalFixes": (
            results["step1_specTemplates_categoryId_converted"] +
            results["step2_products_categoryId_converted"] +
            results["step3_orphan_refs_removed"] +
            results["step4_category_mismatch_removed"]
        )
    }


# === Product Admin Endpoints ===

@api_router.get("/admin/products")
async def admin_list_products(
    admin: dict = Depends(require_admin),
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """List all products in master catalog (admin only)"""
    query = {}
    if not include_inactive:
        query["isActive"] = {"$ne": False}  # SSOT: camelCase
    if category_id:
        query["categoryId"] = ObjectId(category_id) if ObjectId.is_valid(category_id) else category_id  # SSOT: camelCase
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"family": {"$regex": search, "$options": "i"}},
            {"variant": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    total = await db.products.count_documents(query)
    products = await db.products.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    # Serialize all products to prevent ObjectId serialization errors
    serialized_products = []
    for product in products:
        # Safe serialization of entire document
        serialized = serialize_mongo_doc(product)
        product_id = serialized.get("_id")
        product_name = serialized.get("name")
        
        # Get category name - CANONICAL: categoryId is ObjectId
        try:
            category_id = product.get("categoryId")
            if category_id:
                cat_oid = category_id if isinstance(category_id, ObjectId) else ObjectId(category_id)
                cat = await db.categories.find_one({"_id": cat_oid})
                serialized["categoryName"] = cat["name"] if cat else "[Deleted Category]"
                serialized["category_exists"] = cat is not None
            else:
                serialized["categoryName"] = "[No Category]"
                serialized["category_exists"] = False
        except Exception:
            serialized["categoryName"] = "[Invalid Category]"
            serialized["category_exists"] = False
        
        # Count active listings from seller_listings collection
        # SSOT: Use productId (ObjectId) for joins
        try:
            product_oid = ObjectId(product_id) if isinstance(product_id, str) else product_id
            listing_count = await db.sellerListings.count_documents({
                "productId": product_oid,
                "status": "active"
            })
            serialized["listingCount"] = listing_count
        except Exception:
            serialized["listingCount"] = 0
        serialized_products.append(serialized)
    
    # DATA INTEGRITY LOG: Verify response structure
    response_data = {
        "products": serialized_products,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }
    logger.info(f"[DATA INTEGRITY] /api/admin/products: total={total}, page={page}, pages={response_data['pages']}, result_count={len(serialized_products)}")
    
    return response_data

@api_router.get("/admin/products/{product_id}")
async def admin_get_product(
    product_id: str,
    admin: dict = Depends(require_admin)
):
    """Get a specific product (admin only)"""
    try:
        product = await db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Safe serialization
    serialized = serialize_mongo_doc(product)
    
    # Get category
    try:
        cat = await db.categories.find_one({"_id": ObjectId(product.get("category_id", ""))})
        serialized["categoryName"] = cat["name"] if cat else "Unknown"
    except Exception:
        serialized["categoryName"] = "Unknown"
    
    # Get spec template if exists
    if product.get("spec_template_id"):
        try:
            template = await db.specTemplates.find_one({"_id": ObjectId(product["spec_template_id"])})
            if template:
                serialized["specTemplate"] = serialize_mongo_doc(template)
        except Exception:
            pass
    
    # Get active seller_listings for this product (match by product_id or product_name)
    try:
        product_id = serialized.get("_id")
        product_name = serialized.get("name")
        
        # Try product_id first, fallback to product_name
        listings = await db.sellerListings.find({
            "productId": product_id,
            "status": "active"
        }).to_list(length=50)
        
        if not listings and product_name:
            listings = await db.sellerListings.find({
                "productName": product_name,
                "status": "active"
            }).to_list(length=50)
        
        serialized_listings = []
        for listing in listings:
            serialized_listing = serialize_mongo_doc(listing)
            try:
                # SSOT: Use sellerId (camelCase, ObjectId)
                seller_oid = listing.get("sellerId")
                seller = await db.users.find_one({"_id": seller_oid}) if seller_oid else None
                serialized_listing["sellerName"] = seller.get("businessName", "Unknown") if seller else "Unknown"
            except Exception:
                serialized_listing["sellerName"] = "Unknown"
            serialized_listings.append(serialized_listing)
        
        serialized["listings"] = serialized_listings
        serialized["listingCount"] = len(serialized_listings)
    except Exception:
        serialized["listings"] = []
        serialized["listingCount"] = 0
    
    return {"product": serialized}


# ==================== SPEC TEMPLATE VALIDATION HELPER ====================

async def validate_spec_template_ids(
    template_ids: List[str],
    category_id: str,
    db_instance
) -> List[ObjectId]:
    """
    ARCHITECTURAL FIX: Strict validation of spec template IDs.
    
    Validates that each template:
    1. Exists in specTemplates collection
    2. Is active (isActive != false)
    3. Has matching categoryId
    
    Returns list of validated ObjectIds.
    Raises HTTPException if any validation fails.
    """
    if not template_ids:
        return []
    
    validated_oids = []
    category_oid = ObjectId(category_id) if isinstance(category_id, str) else category_id
    category_id_str = str(category_oid)
    
    for template_id in template_ids:
        # Step 1: Convert to ObjectId safely
        try:
            template_oid = ObjectId(template_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid template ID format",
                    "templateId": template_id,
                    "message": f"Template ID '{template_id}' is not a valid ObjectId"
                }
            )
        
        # Step 2: Fetch template from DB
        template = await db_instance.specTemplates.find_one({"_id": template_oid})
        
        if not template:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Template not found",
                    "templateId": template_id,
                    "message": f"Spec template '{template_id}' does not exist"
                }
            )
        
        # Step 3: Check if template is active
        if template.get("isActive") == False:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Template is inactive",
                    "templateId": template_id,
                    "message": f"Spec template '{template_id}' has been deactivated"
                }
            )
        
        # Step 4: Check category match
        template_category = template.get("categoryId")
        template_category_str = str(template_category) if template_category else None
        
        if template_category_str != category_id_str:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Category mismatch",
                    "templateId": template_id,
                    "templateCategory": template_category_str,
                    "productCategory": category_id_str,
                    "message": f"Spec template '{template_id}' belongs to a different category"
                }
            )
        
        validated_oids.append(template_oid)
    
    return validated_oids


@api_router.post("/admin/products")
async def admin_create_product(
    product: AdminProductCreate,
    admin: dict = Depends(require_admin)
):
    """
    Create a new product in master catalog (admin only).
    
    PRODUCT IDENTITY GOVERNANCE:
    - Products are uniquely identified by: (name, category_id, spec_template_id, normalized_spec_hash)
    - Duplicate products are prevented at database level
    - If a product with the same identity exists, returns that product
    
    Products are structural definitions only:
    - Define WHAT can be sold
    - Assign specification templates (multiple allowed)
    - NO manufacturer, NO pricing, NO values
    
    Sellers create listings using these products.
    """
    # Initialize identity service
    identity_service = ProductIdentityService(db)
    
    # Verify category exists - SSOT: Use camelCase field from Pydantic model
    try:
        category = await db.categories.find_one({"_id": ObjectId(product.categoryId)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # ARCHITECTURAL FIX: Strict validation of specTemplateIds
    spec_template_ids = list(product.specTemplateIds) if product.specTemplateIds else []
    
    # Validate all templates: exist, active, matching category
    validated_template_oids = await validate_spec_template_ids(
        spec_template_ids,
        product.categoryId,
        db
    )
    
    # Gather spec fields from validated templates for hash
    spec_fields = {}
    for template_oid in validated_template_oids:
        template = await db.specTemplates.find_one({"_id": template_oid})
        if template and template.get("fields"):
            for field in template["fields"]:
                key = field.get("key", field.get("name", ""))
                spec_fields[key] = ""  # Empty placeholder
    
    # Generate normalized spec hash for product identity
    spec_hash = identity_service.generate_spec_hash(spec_fields)
    normalized_specs = identity_service.normalize_specifications(spec_fields)
    
    # Check for duplicate using identity signature
    existing_product = await identity_service.find_existing_product(
        name=product.name,
        category_id=product.categoryId,
        spec_template_id=str(validated_template_oids[0]) if validated_template_oids else None,
        specifications=spec_fields
    )
    
    if existing_product:
        # Return existing product instead of creating duplicate
        logger.info(f"Product identity match found: {existing_product['_id']} for {product.name}")
        return {
            "message": "Product with this identity already exists",
            "product": existing_product,
            "isExisting": True
        }
    
    # Create new product with identity hash
    # SSOT: ALL fields use camelCase - NO snake_case duplicates
    from datetime import timezone as tz
    now = datetime.now(tz.utc)
    
    # Get category for categoryName
    category = await db.categories.find_one({"_id": ObjectId(product.categoryId)})
    category_name = category.get("name", "Unknown") if category else "Unknown"
    
    product_doc = {
        "_id": ObjectId(),
        "name": product.name,
        # SSOT: Use camelCase ONLY
        "categoryId": ObjectId(product.categoryId),
        "categoryName": category_name,  # SSOT: Include category name
        "description": product.description,
        # Admin provides mandatory product cover image - Firebase URL
        "coverImageUrl": product.coverImageUrl,  # SSOT: camelCase
        # ARCHITECTURAL FIX: Use validated ObjectIds directly
        "specTemplateIds": validated_template_oids,
        "specTemplateVersions": [],  # Will be populated on first use
        "unit": product.unit,
        "family": product.family,
        "variant": product.variant,
        # Status and timestamps - camelCase
        "isActive": True,
        "createdAt": now,
        "createdBy": admin["_id"],  # ObjectId
        "updatedAt": now
    }
    
    try:
        await db.products.insert_one(product_doc)
    except Exception as e:
        # Handle race condition - another request created the product
        if "duplicate key error" in str(e).lower() or "E11000" in str(e):
            existing_product = await identity_service.find_existing_product(
                name=product.name,
                category_id=product.categoryId,
                spec_template_id=spec_template_ids[0] if spec_template_ids else None,
                specifications=spec_fields
            )
            if existing_product:
                return {
                    "message": "Product with this identity already exists",
                    "product": existing_product,
                    "isExisting": True  # SSOT: camelCase
                }
        raise
    
    # Safe serialization before returning
    serialized = serialize_mongo_doc(product_doc)
    
    logger.info(f"Admin {admin['email']} created product: {product.name}")
    return {"message": "Product created successfully", "product": serialized, "isNew": True}  # SSOT: camelCase

@api_router.patch("/admin/products/{product_id}")
async def admin_update_product(
    product_id: str,
    updates: AdminProductUpdate,
    admin: dict = Depends(require_admin)
):
    """Update a product in master catalog (admin only)"""
    try:
        existing = await db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # SSOT: camelCase for all fields
    update_data = {"updatedAt": datetime.now(timezone.utc)}
    
    if updates.name is not None:
        # Check for duplicate name using camelCase field
        dup = await db.products.find_one({
            "_id": {"$ne": ObjectId(product_id)},
            "categoryId": existing.get("categoryId"),
            "name": {"$regex": f"^{updates.name}$", "$options": "i"}
        })
        if dup:
            raise HTTPException(status_code=400, detail="Product with this name already exists in this category")
        update_data["name"] = updates.name
    
    if updates.description is not None:
        update_data["description"] = updates.description
    
    # ARCHITECTURAL FIX: Strict validation of specTemplateIds
    if updates.specTemplateIds is not None:
        # Get the product's category for validation
        product_category_id = existing.get("categoryId")
        if not product_category_id:
            raise HTTPException(status_code=400, detail="Product has no category assigned")
        
        # Validate all templates: exist, active, matching category
        validated_template_oids = await validate_spec_template_ids(
            updates.specTemplateIds,
            str(product_category_id),
            db
        )
        update_data["specTemplateIds"] = validated_template_oids
    
    if updates.family is not None:
        update_data["family"] = updates.family
    if updates.variant is not None:
        update_data["variant"] = updates.variant
    if updates.coverImageUrl is not None:
        update_data["coverImageUrl"] = updates.coverImageUrl
    if updates.unit is not None:
        update_data["unit"] = updates.unit
    if updates.isActive is not None:
        update_data["isActive"] = updates.isActive
    
    await db.products.update_one({"_id": ObjectId(product_id)}, {"$set": update_data})
    
    updated = await db.products.find_one({"_id": ObjectId(product_id)})
    
    # Safe serialization
    serialized = serialize_mongo_doc(updated)
    
    logger.info(f"Admin {admin['email']} updated product: {product_id}")
    return {"message": "Product updated successfully", "product": serialized}

@api_router.delete("/admin/products/{product_id}")
async def admin_delete_product(
    product_id: str,
    force: bool = Query(False),
    admin: dict = Depends(require_admin)
):
    """Soft-delete a product from master catalog (admin only). Blocked if seller listings exist unless force=true."""
    existing = await db.products.find_one({"_id": ObjectId(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check for existing seller_listings (match by product_name)
    listing_count = await db.sellerListings.count_documents({
        "productName": existing.get("name"),
        "status": "active"
    })
    
    if listing_count > 0 and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete product. {listing_count} active seller listings exist. Use force=true to soft-delete anyway."
        )
    
    await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {
            "isActive": False,  # SSOT: camelCase
            "deletedAt": datetime.now(timezone.utc),
            "deletedBy": str(admin["_id"])
        }}
    )
    
    logger.info(f"Admin {admin['email']} soft-deleted product: {product_id}")
    return {"message": "Product deactivated successfully"}

# === Admin User Management ===

@api_router.get("/admin/users")
async def admin_list_users(
    admin: dict = Depends(require_admin),
    search: Optional[str] = None,
    status: Optional[str] = None,  # active, deleted, all
    is_seller: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """List all users (admin only) - SSOT: camelCase"""
    query = {}
    
    # SSOT: Use camelCase field names
    if status == "active":
        query["accountStatus"] = {"$ne": "deleted"}
    elif status == "deleted":
        query["accountStatus"] = "deleted"
    
    if is_seller is not None:
        # isSeller flag or check GST status
        if is_seller:
            query["$or"] = [
                {"isSeller": True},
                {"gst.status": "verified"}
            ]
        else:
            query["$and"] = [
                {"$or": [{"isSeller": False}, {"isSeller": {"$exists": False}}]},
                {"$or": [{"gst.status": {"$ne": "verified"}}, {"gst": {"$exists": False}}]}
            ]
    
    if search:
        # SSOT: Use camelCase field names in profile
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"profile.businessName": {"$regex": search, "$options": "i"}},
            {"profile.phone": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    total = await db.users.count_documents(query)
    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    # Get all user IDs for batch subscription lookup
    user_ids = [u["_id"] for u in users]
    
    # Batch fetch subscriptions - SSOT: userId is ObjectId
    subscriptions_cursor = db.subscriptions.find({"userId": {"$in": user_ids}})
    subscriptions_map = {}
    async for sub in subscriptions_cursor:
        subscriptions_map[str(sub["userId"])] = sub
    
    result_users = []
    for user in users:
        user_object_id = user["_id"]
        user_id_str = str(user_object_id)
        
        # Get nested objects that may contain data
        business = user.get("business", {}) or {}
        profile_obj = user.get("profile", {}) or {}
        gst_obj = user.get("gst", {}) or {}
        subscription_obj = user.get("subscription", {}) or {}
        
        # Build profile - check multiple possible field locations
        # Priority: profile.businessName > business.name > business_name
        profile = {
            "businessName": (
                profile_obj.get("businessName") or 
                business.get("name") or 
                user.get("businessName") or 
                user.get("businessName")
            ),
            "phone": profile_obj.get("phone") or user.get("phone"),
            "city": profile_obj.get("city") or user.get("city"),
            "state": profile_obj.get("state") or user.get("state"),
            "pincode": profile_obj.get("pincode") or user.get("pincode"),
            "address": profile_obj.get("address") or user.get("address"),
        }
        
        # Build GST - check multiple possible field locations
        # Priority: gst.number > business.gst > gst_number
        gst = {
            "number": (
                gst_obj.get("number") or 
                business.get("gst") or 
                user.get("gstNumber") or
                user.get("gstNumber")
            ),
            "status": gst_obj.get("status") or user.get("gstStatus") or user.get("gstStatus"),
            "verified": gst_obj.get("verified") or business.get("gstVerified", False),
        }
        
        # Build response object - support both camelCase and snake_case field names
        user_response = {
            "id": user_id_str,
            "email": user.get("email"),
            "profile": profile,
            "gst": gst,
            "roles": user.get("roles", []),
            "isAdmin": user.get("isAdmin") or user.get("isAdmin", False),
            "isSeller": user.get("isSeller") or user.get("is_seller", False),
            "accountStatus": user.get("accountStatus") or user.get("accountStatus", "active"),
            "emailVerified": user.get("emailVerified") or user.get("emailVerified", False),
            "canLogin": user.get("canLogin") if user.get("canLogin") is not None else user.get("canLogin", True),
            "isActive": user.get("isActive") if user.get("isActive") is not None else user.get("isActive", True),
            "createdAt": (user.get("createdAt") or user.get("createdAt")).isoformat() if (user.get("createdAt") or user.get("createdAt")) else None,
            "updatedAt": (user.get("updatedAt") or user.get("updatedAt")).isoformat() if (user.get("updatedAt") or user.get("updatedAt")) else None,
            "deletedAt": (user.get("deletedAt") or user.get("deletedAt")).isoformat() if (user.get("deletedAt") or user.get("deletedAt")) else None,
        }
        
        # Add listing count - SSOT: sellerId is ObjectId
        user_response["listingCount"] = await db.sellerListings.count_documents({"sellerId": user_object_id})
        
        # Add subscription data
        sub = subscriptions_map.get(user_id_str)
        if sub:
            sub = calculate_subscription_fields(sub)
            user_response["subscriptionStatus"] = sub.get("status", "active")
            user_response["subscriptionPlan"] = sub.get("planName", "free")
            user_response["subscriptionEnd"] = sub.get("endDate").isoformat() if sub.get("endDate") else None
            user_response["daysRemaining"] = sub.get("daysRemaining", -1)
            user_response["isExpiringSoon"] = sub.get("isExpiringSoon", False)
        else:
            user_response["subscriptionStatus"] = "active"
            user_response["subscriptionPlan"] = "free"
            user_response["subscriptionEnd"] = None
            user_response["daysRemaining"] = -1
            user_response["isExpiringSoon"] = False
        
        result_users.append(user_response)
    
    response_data = {
        "users": result_users,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }
    logger.info(f"[DATA INTEGRITY] /api/admin/users: total={total}, page={page}, pages={response_data['pages']}, result_count={len(result_users)}")
    
    return response_data

@api_router.patch("/admin/users/{user_id}/toggle-admin")
async def admin_toggle_admin_status(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    """Toggle admin status for a user (admin only)"""
    if str(admin["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin status")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_status = not user.get("isAdmin", False)
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"isAdmin": new_status, "updatedAt": datetime.now(timezone.utc)}}
    )
    
    logger.info(f"Admin {admin['email']} toggled admin status for user {user_id}: isAdmin={new_status}")
    return {"message": f"Admin status {'granted' if new_status else 'revoked'}", "isAdmin": new_status}

@api_router.post("/admin/users/{user_id}/restore")
async def admin_restore_user(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    """Restore a deleted user account (admin only - bypasses 30-day limit)"""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("accountStatus") != "deleted":
        raise HTTPException(status_code=400, detail="User account is not deleted")
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "accountStatus": "active",
            "isActive": True,
            "canLogin": True,
            "restoredAt": datetime.now(timezone.utc),
            "restoredBy": str(admin["_id"]),
            "updatedAt": datetime.now(timezone.utc)
        },
        "$unset": {"deletedAt": "", "deletionReason": ""}}
    )
    
    # SSOT: Republish user's listings using seller_listings with sellerId
    await db.sellerListings.update_many(
        {"sellerId": ObjectId(user_id), "unpublishedReason": "account_deleted"},
        {"$set": {"status": "active"}, "$unset": {"unpublishedReason": ""}}
    )
    
    logger.info(f"Admin {admin['email']} restored user account: {user_id}")
    return {"message": "User account restored successfully"}


@api_router.get("/admin/users/{user_id}/detail")
async def admin_get_user_detail(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    """Get detailed user information (admin only)"""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # SSOT: Get listing count using seller_listings with sellerId
    listing_count = await db.sellerListings.count_documents({"sellerId": ObjectId(user_id)})
    
    # Get nested objects that may contain data
    business = user.get("business", {}) or {}
    profile_obj = user.get("profile", {}) or {}
    gst_obj = user.get("gst", {}) or {}
    subscription_obj = user.get("subscription", {}) or {}
    
    # Build profile - check multiple possible field locations
    profile = {
        "businessName": (
            profile_obj.get("businessName") or 
            business.get("name") or 
            user.get("businessName") or 
            user.get("businessName")
        ),
        "phone": profile_obj.get("phone") or user.get("phone"),
        "city": profile_obj.get("city") or user.get("city"),
        "state": profile_obj.get("state") or user.get("state"),
        "pincode": profile_obj.get("pincode") or user.get("pincode"),
        "address": profile_obj.get("address") or user.get("address"),
    }
    
    # Build GST - check multiple possible field locations
    gst = {
        "number": (
            gst_obj.get("number") or 
            business.get("gst") or 
            user.get("gstNumber") or
            user.get("gstNumber")
        ),
        "status": gst_obj.get("status") or user.get("gstStatus") or user.get("gstStatus"),
        "verified": gst_obj.get("verified") or business.get("gstVerified", False),
    }
    
    # Build response - support both naming conventions
    return {
        "id": str(user["_id"]),
        "_id": str(user["_id"]),  # Legacy support
        "email": user.get("email"),
        "profile": profile,
        "gst": gst,
        # Legacy flat fields for backward compatibility
        "businessName": profile.get("businessName"),
        "phone": profile.get("phone"),
        "city": profile.get("city"),
        "state": profile.get("state"),
        "pincode": profile.get("pincode"),
        "gstNumber": gst.get("number"),
        "gstStatus": gst.get("status"),
        # Boolean flags
        "isSeller": user.get("isSeller", False) or gst.get("status") == "verified",
        "isAdmin": user.get("isAdmin", False),
        "accountStatus": user.get("accountStatus", "active"),
        "createdAt": user.get("createdAt").isoformat() if user.get("createdAt") else None,
        "listingCount": listing_count,
        "roles": user.get("roles", []),
        "subscription": subscription_obj,
    }


# === Admin Subscription Management ===
# 
# SINGLE SOURCE OF TRUTH: Subscription stored in users.subscription object
# Schema: { plan: "free"|"trial"|"pro", start_date, end_date, inquiry_limit, active }
# NEVER store inquiries_used - always calculate from inquiries collection
#

class SubscriptionUpdateNew(BaseModel):
    """Update seller subscription - Single Source of Truth schema"""
    plan: str = Field(..., description="free, trial, or pro")
    endDate: Optional[datetime] = Field(None, description="When subscription ends (required for trial/pro)")
    note: Optional[str] = Field(None, max_length=500)
    
    model_config = {"populate_by_name": True}
    
    @field_validator('plan')
    @classmethod
    def validate_plan(cls, v):
        if v not in ["free", "trial", "pro"]:
            raise ValueError("Plan must be: free, trial, or pro")
        return v

@api_router.patch("/admin/users/{user_id}/subscription")
async def admin_update_subscription(
    user_id: str,
    data: SubscriptionUpdateNew,
    admin: dict = Depends(require_admin)
):
    """
    Update seller subscription status (admin only).
    
    SINGLE SOURCE OF TRUTH: Uses users.subscription object.
    
    Plans:
    - free: 5 accepted inquiries per month, no expiration
    - trial: Unlimited inquiries, 90 days, cannot renew
    - pro: Unlimited inquiries, renewable, ₹999/quarter
    
    NEVER store inquiries_used - always calculate from inquiries collection.
    """
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    now = datetime.now(timezone.utc)
    plan_config = SUBSCRIPTION_PLANS.get(data.plan, {})
    
    # Build subscription object - SINGLE SOURCE OF TRUTH
    new_subscription = {
        "plan": data.plan,
        "startDate": now,
        "inquiryLimit": plan_config.get("inquiryLimit", 5),
        "active": True
    }
    
    # Set end_date based on plan
    if data.plan == "free":
        new_subscription["endDate"] = None
        new_subscription["active"] = True
    elif data.plan == "trial":
        # Trial is 90 days, cannot be renewed if user had trial before
        if user.get("subscription", {}).get("plan") == "trial":
            raise HTTPException(status_code=400, detail="Trial cannot be renewed. User already had a trial.")
        new_subscription["endDate"] = data.endDate or (now + timedelta(days=90))
    elif data.plan == "pro":
        # Pro requires endDate (quarterly by default)
        new_subscription["endDate"] = data.endDate or (now + timedelta(days=90))
    
    # Prepare update
    update_query = {
        "$set": {
            "subscription": new_subscription,
            "subscriptionUpdatedAt": now,
            "subscriptionUpdatedBy": str(admin["_id"]),
            # Legacy fields for backward compatibility
            "subscriptionStatus": "paid" if data.plan == "pro" else data.plan,
            "subscriptionPlan": plan_config.get("name", data.plan.title()),
            "subscriptionEndDate": new_subscription.get("endDate")
        }
    }
    
    if data.note:
        update_query["$set"]["subscriptionNote"] = data.note
    
    await db.users.update_one({"_id": ObjectId(user_id)}, update_query)
    
    # SSOT: Log subscription history with ObjectId foreign keys
    await db.subscriptionHistory.insert_one({
        "user_id": ObjectId(user_id),  # SSOT: Store as ObjectId
        "action": "admin_update",
        "oldSubscription": user.get("subscription"),
        "newSubscription": new_subscription,
        "admin_id": ObjectId(admin["_id"]) if isinstance(admin["_id"], str) else admin["_id"],  # SSOT: Store as ObjectId
        "adminEmail": admin.get("email"),
        "note": data.note,
        "createdAt": now
    })
    
    logger.info(f"Admin {admin['email']} updated subscription for user {user_id}: plan={data.plan}")
    
    return {
        "message": "Subscription updated successfully",
        "user_id": user_id,
        "subscription": {
            "plan": data.plan,
            "startDate": now.isoformat(),
            "endDate": new_subscription.get("endDate").isoformat() if new_subscription.get("endDate") else None,
            "inquiryLimit": new_subscription.get("inquiryLimit"),
            "active": new_subscription.get("active")
        }
    }

@api_router.get("/admin/subscriptions")
async def admin_list_subscriptions(
    admin: dict = Depends(require_admin),
    status: Optional[str] = None,  # free, trial, paid
    expiring_soon: bool = Query(False, description="Show subscriptions expiring in 7 days"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """List all seller subscriptions (admin only)"""
    # SSOT: Use roles array and gst schema
    query = {
        "roles": "seller",
        "gst.status": "verified"
    }
    
    if status:
        query["subscriptionStatus"] = status
    
    if expiring_soon:
        now = datetime.now(timezone.utc)
        week_later = now + timedelta(days=7)
        query["subscriptionStatus"] = "paid"
        query["subscriptionEndDate"] = {"$lte": week_later, "$gt": now}
    
    skip = (page - 1) * limit
    total = await db.users.count_documents(query)
    users = await db.users.find(
        query,
        projection={
            "firebaseUid": 0,
            "passwordHash": 0
        }
    ).skip(skip).limit(limit).to_list(length=limit)
    
    result = []
    for user in users:
        # Store ObjectId for queries before serializing
        user_oid = user["_id"]
        
        # SSOT: Use ObjectId for seller_listings query
        listing_count = await db.sellerListings.count_documents({
            "sellerId": user_oid,  # SSOT: sellerId is ObjectId
            "status": "active"
        })
        
        # SSOT: Use ObjectId for inquiries query
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1)
        inquiries_count = await db.inquiries.count_documents({
            "sellerId": user_oid,  # SSOT: seller_id is ObjectId
            "status": "accepted",
            "acceptedAt": {"$gte": month_start}
        })
        
        # CRITICAL: Serialize entire user document to convert all ObjectIds
        serialized_user = serialize_mongo_doc(user)
        serialized_user["listingCount"] = listing_count
        serialized_user["inquiries_accepted_this_month"] = inquiries_count
        
        result.append(serialized_user)
    
    # DATA INTEGRITY LOG: Verify response structure
    response_data = {
        "subscriptions": result,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }
    logger.info(f"[DATA INTEGRITY] /api/admin/user/subscriptions: total={total}, page={page}, pages={response_data['pages']}, result_count={len(result)}")
    
    return response_data


# ================== SUBSCRIPTION MANAGEMENT SYSTEM ==================
#
# SINGLE SOURCE OF TRUTH: Dedicated `subscriptions` collection
# 
# Schema:
# {
#   user_id: string,
#   plan_name: string (free/trial/pro),
#   duration_days: number,
#   start_date: timestamp,
#   end_date: timestamp,
#   status: "active" | "expired" | "suspended",
#   days_remaining: number (calculated),
#   is_expiring_soon: boolean (calculated),
#   last_updated_by: admin_id,
#   updated_at: timestamp,
#   notes: string
# }
#

class SubscriptionStatus(str, Enum):
    """Valid subscription statuses"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"

class SubscriptionCreate(BaseModel):
    """SSOT: All fields use camelCase - Create/Activate subscription"""
    planName: str = Field(..., description="free, trial, or pro")
    startDate: datetime = Field(..., description="When subscription starts")
    durationDays: Optional[int] = Field(None, description="Duration in days (auto-set based on plan if not provided)")
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('planName')
    @classmethod
    def validate_plan(cls, v):
        if v not in ["free", "trial", "pro"]:
            raise ValueError("Plan must be: free, trial, or pro")
        return v

class SubscriptionExtend(BaseModel):
    """SSOT: All fields use camelCase - Extend subscription by X days"""
    extendDays: int = Field(..., ge=1, le=365, description="Days to extend")
    notes: Optional[str] = Field(None, max_length=500)

class SubscriptionSuspend(BaseModel):
    """Suspend subscription"""
    reason: str = Field(..., max_length=500)


def calculate_subscription_fields(subscription: dict) -> dict:
    """
    Calculate derived fields for a subscription.
    ALWAYS called before returning subscription data.
    
    Returns updated subscription with:
    - daysRemaining
    - isExpiringSoon
    - status (may be updated to 'expired' if endDate passed)
    """
    from datetime import timezone
    now = datetime.now(timezone.utc)
    
    # Handle free plan (no expiration)
    if subscription.get("planName") == "free":
        subscription["daysRemaining"] = -1  # -1 = unlimited/no expiration
        subscription["isExpiringSoon"] = False
        subscription["status"] = "active"
        return subscription
    
    # For trial/pro, check expiration
    end_date = subscription.get("endDate")
    current_status = subscription.get("status", "active")
    
    if not end_date:
        subscription["daysRemaining"] = 0
        subscription["isExpiringSoon"] = False
        subscription["status"] = "expired"
        return subscription
    
    # Ensure end_date is datetime and timezone-aware
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    elif end_date.tzinfo is None:
        # Make naive datetime timezone-aware (assume UTC)
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    # Calculate days remaining
    delta = end_date - now
    days_remaining = max(0, delta.days)
    subscription["daysRemaining"] = days_remaining
    
    # Check if expiring soon (within 10 days)
    subscription["isExpiringSoon"] = 0 < days_remaining <= 10 and current_status == "active"
    
    # Auto-expire if past end_date
    if now > end_date and current_status == "active":
        subscription["status"] = "expired"
    
    return subscription


async def get_or_create_subscription(user_id: str) -> dict:
    """
    Get existing subscription or create default free subscription.
    ALWAYS returns calculated fields.
    
    SSOT POLICY: user_id is stored as ObjectId.
    """
    # SSOT: Convert user_id to ObjectId for query
    user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
    
    subscription = await db.subscriptions.find_one({"user_id": user_oid})
    
    if not subscription:
        # Create default free subscription with ObjectId user_id
        now = datetime.now(timezone.utc)
        subscription = {
            "user_id": user_oid,  # SSOT: Store as ObjectId
            "planName": "free",
            "durationDays": 0,
            "startDate": now,
            "endDate": None,
            "status": "active",
            "lastUpdatedBy": "system",
            "updatedAt": now,
            "notes": "Default free plan",
            "createdAt": now
        }
        await db.subscriptions.insert_one(subscription)
        subscription = await db.subscriptions.find_one({"user_id": user_oid})
    
    # Calculate derived fields
    subscription = calculate_subscription_fields(subscription)
    
    # Update status in DB if it changed
    if subscription.get("status") == "expired":
        await db.subscriptions.update_one(
            {"user_id": user_oid},
            {"$set": {"status": "expired", "updatedAt": datetime.now(timezone.utc)}}
        )
    
    return subscription


@api_router.get("/admin/subscriptions/manage/{user_id}")
async def admin_get_subscription(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Get subscription details for a user.
    Returns calculated fields (days_remaining, is_expiring_soon, etc.)
    """
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    subscription = await get_or_create_subscription(user_id)
    
    # CRITICAL: Serialize the entire document to convert all ObjectIds
    serialized_subscription = serialize_mongo_doc(subscription)
    
    return {
        "subscription": serialized_subscription,
        "user": {
            "id": str(user["_id"]),
            "businessName": user.get("businessName"),
            "email": user.get("email"),
            "isSeller": user.get("isSeller", False)
        }
    }


@api_router.post("/admin/subscriptions/activate/{user_id}")
async def admin_activate_subscription(
    user_id: str,
    data: SubscriptionCreate,
    admin: dict = Depends(require_admin)
):
    """
    Activate or update subscription with admin-set start date.
    
    UNIFIED SUBSCRIPTION ENGINE:
    - Uses activate_or_extend() for all activation logic
    - Properly extends existing subscriptions
    - Records activation source as "admin"
    - Maintains history
    """
    try:
        from services.subscription_engine import SubscriptionEngine
        
        user_oid = ObjectId(user_id)

        user = await db.users.find_one({"_id": user_oid})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        now = datetime.now(timezone.utc)
        
        # Determine duration
        if data.durationDays:
            duration_days = data.durationDays
        elif data.planName == "trial":
            duration_days = 90
        elif data.planName == "pro":
            duration_days = 90
        else:
            duration_days = 0

        # Use unified subscription engine
        engine = SubscriptionEngine(db)
        result = await engine.activate_or_extend(
            user_id=user_oid,
            plan_name=data.planName,
            duration_days=duration_days,
            source="admin",
            activated_by=ObjectId(admin["_id"]) if isinstance(admin["_id"], str) else admin["_id"],
            notes=data.notes
        )
        
        subscription_doc = result["subscription"]
        
        # Legacy: Update users.subscription for backwards compatibility
        end_date = subscription_doc.get("endDate")
        legacy_subscription = {
            "plan": data.planName,
            "startDate": subscription_doc.get("startDate", now),
            "endDate": end_date,
            "inquiryLimit": subscription_doc.get("enquiryLimit", -1),
            "active": True
        }

        await db.users.update_one(
            {"_id": user_oid},
            {"$set": {
                "subscription": legacy_subscription,
                "subscriptionUpdatedAt": now,
                "subscriptionUpdatedBy": str(admin["_id"])
            }}
        )

        subscription_doc = calculate_subscription_fields(subscription_doc)

        logger.info(f"[SUBSCRIPTION] Admin {admin['email']} {result['action']} {data.planName} for user {user_id}")

        return {
            "message": f"Subscription {result['action']} successfully",
            "subscription": {
                "userId": user_id,
                "planName": subscription_doc.get("planName"),
                "startDate": subscription_doc.get("startDate").isoformat() if subscription_doc.get("startDate") else None,
                "endDate": subscription_doc.get("endDate").isoformat() if subscription_doc.get("endDate") else None,
                "durationDays": subscription_doc.get("durationDays"),
                "daysRemaining": subscription_doc.get("daysRemaining"),
                "isExpiringSoon": subscription_doc.get("isExpiringSoon"),
                "status": subscription_doc.get("status", "active"),
                "action": result["action"],
                "activationSource": "admin"
            }
        }

    except Exception as e:
        logger.error(f"[SUBSCRIPTION ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail="Subscription activation failed")
		

@api_router.post("/admin/subscriptions/extend/{user_id}")
async def admin_extend_subscription(
    user_id: str,
    data: SubscriptionExtend,
    admin: dict = Depends(require_admin)
):
    user_oid = ObjectId(user_id)

    subscription = await db.subscriptions.find_one({"userId": user_oid})
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found. Activate first.")

    if subscription.get("planName") == "free":
        raise HTTPException(status_code=400, detail="Cannot extend free plan.")

    now = datetime.now(timezone.utc)
    old_end_date = subscription.get("endDate")

    if not old_end_date or now > old_end_date:
        new_end_date = now + timedelta(days=data.extendDays)
    else:
        new_end_date = old_end_date + timedelta(days=data.extendDays)

    new_duration = subscription.get("durationDays", 0) + data.extendDays

    await db.subscriptions.update_one(
        {"userId": user_oid},
        {"$set": {
            "endDate": new_end_date,
            "durationDays": new_duration,
            "status": "active",
            "lastUpdatedBy": str(admin["_id"]),
            "updatedAt": now
        }}
    )

    return {
        "message": f"Subscription extended by {data.extendDays} days",
        "subscription": {
            "userId": user_id,
            "newEndDate": new_end_date.isoformat(),
            "status": "active"
        }
    }

@api_router.post("/admin/subscriptions/suspend/{user_id}")
async def admin_suspend_subscription(
    user_id: str,
    data: SubscriptionSuspend,
    admin: dict = Depends(require_admin)
):
    user_oid = ObjectId(user_id)

    subscription = await db.subscriptions.find_one({"userId": user_oid})
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    now = datetime.now(timezone.utc)

    await db.subscriptions.update_one(
        {"userId": user_oid},
        {"$set": {
            "status": "suspended",
            "suspendedAt": now,
            "suspendedReason": data.reason,
            "updatedAt": now
        }}
    )

    return {
        "message": "Subscription suspended",
        "subscription": {
            "userId": user_id,
            "status": "suspended"
        }
    }

@api_router.post("/admin/subscriptions/reactivate/{user_id}")
async def admin_reactivate_subscription(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    user_oid = ObjectId(user_id)

    subscription = await db.subscriptions.find_one({"userId": user_oid})
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    now = datetime.now(timezone.utc)
    end_date = subscription.get("endDate")

    new_status = "active"
    if end_date and now > end_date:
        new_status = "expired"

    await db.subscriptions.update_one(
        {"userId": user_oid},
        {"$set": {
            "status": new_status,
            "updatedAt": now
        }}
    )

    return {
        "message": f"Subscription reactivated ({new_status})",
        "subscription": {
            "userId": user_id,
            "status": new_status
        }
    }

@api_router.post("/admin/subscriptions/run-expiry-check")
async def admin_run_expiry_check(admin: dict = Depends(require_admin)):
    """
    Manual trigger for expiry check (normally run by cron).
    Updates all expired subscriptions.
    """
    now = datetime.now(timezone.utc)
    
    # Find all active subscriptions past their end_date
    result = await db.subscriptions.update_many(
        {
            "status": "active",
            "planName": {"$in": ["trial", "pro"]},
            "endDate": {"$lt": now}
        },
        {
            "$set": {
                "status": "expired",
                "expiredAt": now,
                "updatedAt": now,
                "lastUpdatedBy": "system_cron"
            }
        }
    )
    
    # Also update legacy subscriptions
    await db.users.update_many(
        {
            "subscription.active": True,
            "subscription.plan": {"$in": ["trial", "pro"]},
            "subscription.end_date": {"$lt": now}
        },
        {
            "$set": {
                "subscription.active": False,
                "subscriptionUpdatedAt": now
            }
        }
    )
    
    logger.info(f"[SUBSCRIPTION CRON] Expired {result.modified_count} subscriptions")
    
    return {
        "message": f"Expiry check complete",
        "expiredCount": result.modified_count,
        "checkedAt": now.isoformat()
    }


@api_router.get("/admin/subscriptions/expiring")
async def admin_get_expiring_subscriptions(
    admin: dict = Depends(require_admin),
    days: int = Query(10, ge=1, le=30, description="Days until expiration")
):
    """
    Get list of subscriptions expiring within X days.
    Useful for proactive renewal outreach.
    """
    now = datetime.now(timezone.utc)
    future_date = now + timedelta(days=days)
    
    expiring = await db.subscriptions.find({
        "status": "active",
        "planName": {"$in": ["trial", "pro"]},
        "endDate": {"$gte": now, "$lte": future_date}
    }).to_list(100)
    
    # Enrich with user data and calculate fields
    result = []
    for sub in expiring:
        sub = calculate_subscription_fields(sub)
        
        # CRITICAL: Serialize entire subscription document
        serialized_sub = serialize_mongo_doc(sub)
        
        # Get user_id for lookup (handle both string and ObjectId)
        user_id = sub.get("user_id")
        if isinstance(user_id, str):
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = None
        else:
            user_oid = user_id
        
        user = None
        if user_oid:
            user = await db.users.find_one(
                {"_id": user_oid},
                projection={"businessName": 1, "email": 1, "phone": 1}
            )
        
        serialized_sub["user"] = {
            "id": serialized_sub.get("user_id"),
            "businessName": user.get("businessName") if user else None,
            "email": user.get("email") if user else None,
            "phone": user.get("phone") if user else None
        }
        result.append(serialized_sub)
    
    return {
        "expiring_within_days": days,
        "count": len(result),
        "subscriptions": result
    }


# === Seller Subscription Endpoint (Updated) ===

@api_router.get("/seller/subscription/status")
async def seller_get_subscription_status(user: dict = Depends(get_current_user)):
    """
    Get seller's subscription status from dedicated subscriptions collection.
    
    SINGLE SOURCE OF TRUTH: subscriptions collection via subscription_service
    
    Returns:
    - All subscription fields
    - Calculated: days_remaining, is_expiring_soon
    - Feature access flags
    """
    from services.subscription_service import get_subscription_status_for_seller
    
    user_oid = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(user["_id"])
    
    # Use the centralized subscription service (SSOT)
    status_data = await get_subscription_status_for_seller(db, user_oid)
    
    # Get subscription info
    sub_info = status_data["subscription"]
    usage_info = status_data["usage"]
    
    plan = sub_info["planName"]
    is_active = sub_info["status"] == "active"
    is_unlimited = sub_info["isUnlimited"]
    
    # Calculate next reset
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime(now.year, now.month + 1, 1)
    
    return {
        "subscription": {
            "planName": plan,
            "status": sub_info["status"],
            "startDate": None,  # Not stored in new service
            "endDate": sub_info.get("endDate"),
            "daysRemaining": sub_info["daysRemaining"],
            "isExpiringSoon": sub_info["isExpiringSoon"],
            "isActive": is_active
        },
        "usage": {
            "accepted_this_month": usage_info["used"],
            "monthlyLimit": usage_info["limit"],
            "remaining": usage_info["remaining"],
            "limitReached": usage_info["remaining"] == 0 and not is_unlimited,
            "resetsOn": usage_info["resetsOn"] or next_month.strftime("%B 1, %Y")
        },
        "features": {
            "can_accept_inquiries": is_active or plan == "free",  # Free users can still accept up to limit
            "unlimitedInquiries": is_unlimited,
            "verifiedBadge": plan == "pro" and is_active,
            "prioritySupport": plan == "pro" and is_active,
            "analyticsAccess": plan == "pro" and is_active
        },
        "show_expiry_warning": sub_info["isExpiringSoon"],
        "show_upgrade_cta": status_data.get("showUpgradeCta", plan == "free")
    }


# ================== ADMIN INQUIRIES ENDPOINT ==================
# 
# SINGLE SOURCE OF TRUTH: All lead/inquiry data comes from `inquiries` collection
# This replaces any old endpoint that pulled from other sources
#

@api_router.get("/admin/inquiries")
async def admin_get_inquiries(
    admin: dict = Depends(require_admin),
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, rejected, reported"),
    seller_id: Optional[str] = Query(None, description="Filter by seller"),
    buyer_id: Optional[str] = Query(None, description="Filter by buyer"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Admin endpoint to view all inquiries/leads.
    
    SINGLE SOURCE OF TRUTH: All data comes from the `inquiries` collection.
    
    Returns:
    - Buyer info
    - Seller info
    - Product info
    - Category
    - Status
    - Created date
    - Seller subscription plan at time of acceptance
    """
    query = {}
    
    if status:
        query["status"] = status
    # CRITICAL FIX: Convert string IDs to ObjectId for proper MongoDB matching
    if seller_id:
        try:
            query["sellerId"] = ObjectId(seller_id)
        except Exception:
            query["sellerId"] = seller_id  # Fallback to string if invalid
    if buyer_id:
        try:
            query["buyerId"] = ObjectId(buyer_id)
        except Exception:
            query["buyerId"] = buyer_id  # Fallback to string if invalid
    
    # Date range filtering
    if date_from or date_to:
        query["createdAt"] = {}
        if date_from:
            try:
                query["createdAt"]["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            except:
                pass
        if date_to:
            try:
                query["createdAt"]["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except:
                pass
    
    skip = (page - 1) * limit
    
    # Get inquiries
    inquiries = await db.inquiries.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.inquiries.count_documents(query)
    
    result = []
    for inq in inquiries:
        inq_id = str(inq["_id"])
        
        # Get IDs - support both camelCase (new) and snake_case (legacy)
        seller_id_val = inq.get("sellerId")
        buyer_id_val = inq.get("buyerId")
        listing_id_val = inq.get("listingId")
        product_id_val = inq.get("productId")
        created_at_val = inq.get("createdAt")
        accepted_at_val = inq.get("acceptedAt")
        
        # Get seller info - FIXED: Use profile.* nested fields
        seller = None
        seller_subscription = None
        if seller_id_val:
            try:
                seller = await db.users.find_one(
                    {"_id": ObjectId(seller_id_val) if isinstance(seller_id_val, str) else seller_id_val},
                    projection={"profile.businessName": 1, "profile.city": 1, "profile.state": 1, "email": 1, "subscription": 1}
                )
                if seller:
                    seller_subscription = seller.get("subscription", {}).get("plan", "free")
            except:
                pass
        
        # Get buyer info - FIXED: Use profile.* nested fields
        buyer = None
        if buyer_id_val:
            try:
                buyer = await db.users.find_one(
                    {"_id": ObjectId(buyer_id_val) if isinstance(buyer_id_val, str) else buyer_id_val},
                    projection={"profile.businessName": 1, "profile.city": 1, "profile.state": 1, "email": 1}
                )
            except:
                pass
        
        # Get listing/product info
        listing = None
        category_name = None
        product_name_from_product = None
        if listing_id_val:
            try:
                listing = await db.sellerListings.find_one(
                    {"_id": ObjectId(listing_id_val) if isinstance(listing_id_val, str) else listing_id_val},
                    projection={"productName": 1, "categoryName": 1, "categoryId": 1, "productId": 1}
                )
                if listing:
                    category_name = listing.get("categoryName")
                    
                    # CRITICAL FIX: Get product name from products collection via productId
                    product_id_from_listing = listing.get("productId")
                    if product_id_from_listing:
                        try:
                            pid = ObjectId(product_id_from_listing) if isinstance(product_id_from_listing, str) else product_id_from_listing
                            product_doc = await db.products.find_one(
                                {"_id": pid},
                                projection={"name": 1, "family": 1, "variant": 1}
                            )
                            if product_doc:
                                product_name_from_product = product_doc.get("name")
                                # If no category from listing, try from product's category
                        except:
                            pass
                    
                    # If no category name, fetch from categories collection
                    if not category_name:
                        cat_id = listing.get("categoryId")
                        if cat_id:
                            try:
                                category_doc = await db.categories.find_one(
                                    {"_id": ObjectId(cat_id) if isinstance(cat_id, str) else cat_id},
                                    projection={"name": 1}
                                )
                                if category_doc:
                                    category_name = category_doc.get("name")
                            except:
                                pass
            except:
                pass
        
        # Apply category filter after getting data
        if category and category_name and category.lower() not in category_name.lower():
            continue
        
        # Get product name from various sources (priority order)
        # 1. Inquiry document (stored at creation time)
        # 2. Products collection (via listing.productId) - MOST RELIABLE
        # 3. Listing document (legacy field)
        product_name = inq.get("productName")
        if not product_name:
            product_name = product_name_from_product
        if not product_name and listing:
            product_name = listing.get("productName")
        
        result.append({
            "_id": inq_id,
            "buyer": {
                "id": str(buyer_id_val) if buyer_id_val else None,
                "name": (
                    inq.get("buyerInfo", {}).get("name") 
                    or (buyer.get("profile", {}).get("businessName") if buyer else None)
                ),
                "email": buyer.get("email") if buyer else None,
                "city": (
                    inq.get("buyerInfo", {}).get("city") 
                    or (buyer.get("profile", {}).get("city") if buyer else None)
                ),
                "state": (
                    inq.get("buyerInfo", {}).get("state") 
                    or (buyer.get("profile", {}).get("state") if buyer else None)
                ),
            },
            "seller": {
                "id": str(seller_id_val) if seller_id_val else None,
                "name": (
                    seller.get("profile", {}).get("businessName") 
                    or seller.get("email") 
                    if seller else None
                ),
                "email": seller.get("email") if seller else None,
                "city": seller.get("profile", {}).get("city") if seller else None,
                "state": seller.get("profile", {}).get("state") if seller else None,
            },
            "product": {
                "id": str(product_id_val) if product_id_val else None,
                "name": product_name,
                "listingId": str(listing_id_val) if listing_id_val else None,
            },
            # SSOT: Also include productName at top level for frontend compatibility
            "productName": product_name,
            "category": category_name,
            "quantity": inq.get("quantity"),
            "message": inq.get("message") or inq.get("requirementNote"),
            "status": inq.get("status"),
            "buyerType": inq.get("buyerType"),
            "createdAt": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
            "acceptedAt": accepted_at_val.isoformat() if isinstance(accepted_at_val, datetime) else accepted_at_val,
            "quote": inq.get("quote"),
            "rejection": inq.get("rejection"),
            "report": inq.get("report"),
            # SSOT: Use camelCase for frontend consistency
            "sellerSubscriptionPlan": seller_subscription
        })
    
    # DATA INTEGRITY LOG: Verify response structure before sending
    response_data = {
        "inquiries": result,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }
    logger.info(f"[DATA INTEGRITY] /api/admin/inquiries: total={total}, page={page}, pages={response_data['pages']}, result_count={len(result)}")
    
    return response_data


@api_router.get("/admin/inquiries/export")
async def admin_export_inquiries(
    admin: dict = Depends(require_admin),
    status: Optional[str] = Query(None),
    seller_id: Optional[str] = Query(None),
    buyer_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Export inquiries as CSV-ready JSON data.
    
    SINGLE SOURCE OF TRUTH: All data from `inquiries` collection.
    """
    import io
    import csv
    from fastapi.responses import StreamingResponse
    
    query = {}
    if status:
        query["status"] = status
    if seller_id:
        query["sellerId"] = seller_id
    if buyer_id:
        query["buyerId"] = buyer_id
    
    if date_from or date_to:
        query["createdAt"] = {}
        if date_from:
            try:
                query["createdAt"]["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            except:
                pass
        if date_to:
            try:
                query["createdAt"]["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except:
                pass
    
    inquiries = await db.inquiries.find(query).sort("createdAt", -1).to_list(10000)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Status", "Created At", "Product Name", "Quantity",
        "Buyer Name", "Buyer City", "Buyer Type",
        "Seller ID", "Seller Subscription",
        "Message", "Accepted At", "Rejected At"
    ])
    
    for inq in inquiries:
        # Get seller subscription
        seller_sub = "free"
        if inq.get("sellerId"):
            try:
                seller = await db.users.find_one(
                    {"_id": ObjectId(inq["sellerId"])},
                    projection={"subscription": 1}
                )
                if seller:
                    seller_sub = seller.get("subscription", {}).get("plan", "free")
            except:
                pass
        
        writer.writerow([
            str(inq["_id"]),
            inq.get("status", ""),
            inq.get("createdAt").isoformat() if isinstance(inq.get("createdAt"), datetime) else "",
            inq.get("productName", ""),
            inq.get("quantity", ""),
            inq.get("buyerInfo", {}).get("name", ""),
            inq.get("buyerInfo", {}).get("city", ""),
            inq.get("buyerType", ""),
            inq.get("sellerId", ""),
            seller_sub,
            inq.get("message", "") or inq.get("requirementNote", ""),
            inq.get("acceptedAt").isoformat() if isinstance(inq.get("acceptedAt"), datetime) else "",
            inq.get("rejectedAt").isoformat() if isinstance(inq.get("rejectedAt"), datetime) else ""
        ])
    
    output.seek(0)
    
    logger.info(f"[DATA INTEGRITY] /api/admin/inquiries/export: exported {len(inquiries)} inquiries")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inquiries_export_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
    )


# === Admin Dashboard Stats ===

@api_router.get("/admin/stats")
async def admin_get_stats(admin: dict = Depends(require_admin)):
    """
    Get admin dashboard statistics.
    
    SINGLE SOURCE OF TRUTH:
    - All inquiry/lead stats come from the `inquiries` collection
    - All subscription stats come from `users.subscription` object
    """
    # Get this month's date range for inquiry stats
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1)
    
    stats = {
        "users": {
            "total": await db.users.count_documents({}),
            "active": await db.users.count_documents({"accountStatus": {"$ne": "deleted"}}),
            "deleted": await db.users.count_documents({"accountStatus": "deleted"}),
            # SSOT: Use roles array
            "sellers": await db.users.count_documents({"roles": "seller"}),
            # SSOT: Use gst.status
            "pendingGst": await db.users.count_documents({"roles": "seller", "gst.status": "pending"})
        },
        "catalog": {
            "categories": await db.categories.count_documents({"isActive": {"$ne": False}}),  # SSOT: camelCase
            "products": await db.products.count_documents({"isActive": {"$ne": False}}),  # SSOT: camelCase
            "manufacturers": await db.manufacturers.count_documents({"status": "approved"}),
            "specTemplates": await db.specTemplates.count_documents({"isActive": {"$ne": False}})  # SSOT: camelCase
        },
        "listings": {
            "total": await db.sellerListings.count_documents({}),
            "active": await db.sellerListings.count_documents({"status": "active"}),
            "drafts": await db.sellerListings.count_documents({"status": "draft"}),
            "paused": await db.sellerListings.count_documents({"status": "paused"})
        },
        "requests": {
            "pendingManufacturers": await db.manufacturer_requests.count_documents({"status": "pending"}),
            "pendingProducts": await db.product_requests.count_documents({"status": "pending"})
        },
        # SINGLE SOURCE OF TRUTH: All inquiry stats from inquiries collection
        "inquiries": {
            "total": await db.inquiries.count_documents({}),
            "pending": await db.inquiries.count_documents({"status": "pending"}),
            "accepted": await db.inquiries.count_documents({"status": "accepted"}),
            "rejected": await db.inquiries.count_documents({"status": "rejected"}),
            "reported": await db.inquiries.count_documents({"status": "reported"}),
            "thisMonth": await db.inquiries.count_documents({"createdAt": {"$gte": month_start}}),
            "accepted_this_month": await db.inquiries.count_documents({
                "status": "accepted",
                "acceptedAt": {"$gte": month_start}
            })
        },
        # Subscription stats - SSOT: use roles array
        "subscriptions": {
            "free": await db.users.count_documents({"roles": "seller", "subscription.plan": "free"}),
            "trial": await db.users.count_documents({"roles": "seller", "subscription.plan": "trial"}),
            "pro": await db.users.count_documents({"roles": "seller", "subscription.plan": "pro"}),
            # Legacy sellers without new subscription object default to free
            "noSubscription": await db.users.count_documents({
                "roles": "seller",
                "subscription": {"$exists": False}
            }),
            # Expiring in next 7 days
            "expiringSoon": await db.users.count_documents({
                "roles": "seller",
                "subscription.end_date": {
                    "$gte": now,
                    "$lte": now + timedelta(days=7)
                }
            })
        }
    }
    
    # DATA INTEGRITY LOG: Verify response structure
    logger.info(f"[DATA INTEGRITY] /api/admin/stats: users={stats['users']}, inquiries={stats['inquiries']}, subscriptions={stats['subscriptions']}")
    
    return {"stats": stats, "generatedAt": datetime.now(timezone.utc).isoformat()}


# === Admin Analytics Endpoint ===

@api_router.get("/admin/analytics")
async def admin_get_analytics(
    admin: dict = Depends(require_admin),
    days: int = Query(30, ge=1, le=90, description="Number of days for analytics")
):
    """
    Admin analytics endpoint for leads, sellers, and fraud monitoring.
    
    SINGLE SOURCE OF TRUTH:
    - All lead stats come from `inquiries` collection
    - All seller stats come from `users.subscription` object
    
    Returns:
    - Leads per day (last N days)
    - Approval vs rejection percentage
    - Top products by inquiries
    - Top sellers by inquiries
    - Fraud monitoring (high rejection ratio, spam detection)
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # === Leads per day ===
    leads_pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$createdAt"},
                    "month": {"$month": "$createdAt"},
                    "day": {"$dayOfMonth": "$createdAt"}
                },
                "count": {"$sum": 1},
                "accepted": {"$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}},
                "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}}
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
    ]
    leads_per_day_raw = await db.inquiries.aggregate(leads_pipeline).to_list(None)
    
    # Format leads per day
    leads_per_day = []
    for item in leads_per_day_raw:
        date_str = f"{item['_id']['year']}-{item['_id']['month']:02d}-{item['_id']['day']:02d}"
        leads_per_day.append({
            "date": date_str,
            "total": item["count"],
            "accepted": item["accepted"],
            "rejected": item["rejected"],
            "pending": item["pending"]
        })
    
    # === Approval vs Rejection Rate ===
    total_inquiries = await db.inquiries.count_documents({"createdAt": {"$gte": start_date}})
    accepted_count = await db.inquiries.count_documents({"status": "accepted", "createdAt": {"$gte": start_date}})
    rejected_count = await db.inquiries.count_documents({"status": "rejected", "createdAt": {"$gte": start_date}})
    
    approval_rate = (accepted_count / total_inquiries * 100) if total_inquiries > 0 else 0
    rejection_rate = (rejected_count / total_inquiries * 100) if total_inquiries > 0 else 0
    
    # === Top Products by Inquiries ===
    top_products_pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$product_name",
                "count": {"$sum": 1},
                "accepted": {"$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}},
                "listingId": {"$first": "$listing_id"}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_products_raw = await db.inquiries.aggregate(top_products_pipeline).to_list(None)
    
    top_products = []
    for item in top_products_raw:
        top_products.append({
            "productName": item["_id"] or "Unknown",
            "inquiryCount": item["count"],
            "acceptedCount": item["accepted"],
            "conversionRate": (item["accepted"] / item["count"] * 100) if item["count"] > 0 else 0
        })
    
    # === Top Sellers by Inquiries ===
    top_sellers_pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$sellerId",
                "count": {"$sum": 1},
                "accepted": {"$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_sellers_raw = await db.inquiries.aggregate(top_sellers_pipeline).to_list(None)
    
    # Enrich with seller info
    top_sellers = []
    for item in top_sellers_raw:
        seller_info = None
        subscription_plan = "free"
        if item["_id"]:
            try:
                seller = await db.users.find_one(
                    {"_id": ObjectId(item["_id"])},
                    projection={"businessName": 1, "subscription": 1}
                )
                if seller:
                    seller_info = seller.get("businessName")
                    subscription_plan = seller.get("subscription", {}).get("plan", "free")
            except:
                pass
        
        rejection_ratio = (item["rejected"] / item["count"] * 100) if item["count"] > 0 else 0
        top_sellers.append({
            "sellerId": item["_id"],
            "sellerName": seller_info or "Unknown",
            "subscriptionPlan": subscription_plan,
            "inquiryCount": item["count"],
            "acceptedCount": item["accepted"],
            "rejectedCount": item["rejected"],
            "rejectionRatio": rejection_ratio
        })
    
    # === Fraud Monitoring ===
    # 1. High rejection ratio detection (sellers with >50% rejection rate and >5 inquiries)
    high_rejection_pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$sellerId",
                "total": {"$sum": 1},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}}
            }
        },
        {
            "$match": {
                "total": {"$gte": 5}
            }
        },
        {
            "$addFields": {
                "rejectionRatio": {"$divide": ["$rejected", "$total"]}
            }
        },
        {
            "$match": {
                "rejectionRatio": {"$gte": 0.5}
            }
        },
        {"$sort": {"rejectionRatio": -1}},
        {"$limit": 10}
    ]
    high_rejection_raw = await db.inquiries.aggregate(high_rejection_pipeline).to_list(None)
    
    high_rejection_sellers = []
    for item in high_rejection_raw:
        seller_info = None
        if item["_id"]:
            try:
                seller = await db.users.find_one(
                    {"_id": ObjectId(item["_id"])},
                    projection={"businessName": 1, "email": 1}
                )
                if seller:
                    seller_info = {
                        "name": seller.get("businessName"),
                        "email": seller.get("email")
                    }
            except:
                pass
        
        high_rejection_sellers.append({
            "sellerId": item["_id"],
            "seller": seller_info,
            "totalInquiries": item["total"],
            "rejectedCount": item["rejected"],
            "rejectionRatio": round(item["rejectionRatio"] * 100, 1)
        })
    
    # 2. Lead spam detection (buyers sending >10 inquiries in a day)
    spam_detection_pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "buyerId": "$buyerId",
                    "date": {
                        "year": {"$year": "$createdAt"},
                        "month": {"$month": "$createdAt"},
                        "day": {"$dayOfMonth": "$createdAt"}
                    }
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gte": 10}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    spam_raw = await db.inquiries.aggregate(spam_detection_pipeline).to_list(None)
    
    potential_spam = []
    for item in spam_raw:
        buyer_info = None
        if item["_id"]["buyerId"]:
            try:
                buyer = await db.users.find_one(
                    {"_id": ObjectId(item["_id"]["buyerId"])},
                    projection={"businessName": 1, "email": 1}
                )
                if buyer:
                    buyer_info = {
                        "name": buyer.get("businessName"),
                        "email": buyer.get("email")
                    }
            except:
                pass
        
        date_str = f"{item['_id']['date']['year']}-{item['_id']['date']['month']:02d}-{item['_id']['date']['day']:02d}"
        potential_spam.append({
            "buyerId": item["_id"]["buyerId"],
            "buyer": buyer_info,
            "date": date_str,
            "inquiryCount": item["count"]
        })
    
    analytics = {
        "periodDays": days,
        "leads_per_day": leads_per_day,
        "rates": {
            "totalInquiries": total_inquiries,
            "accepted": accepted_count,
            "rejected": rejected_count,
            "approvalRate": round(approval_rate, 1),
            "rejectionRate": round(rejection_rate, 1)
        },
        "topProducts": top_products,
        "topSellers": top_sellers,
        "fraudMonitoring": {
            "high_rejection_sellers": high_rejection_sellers,
            "potential_spam_buyers": potential_spam
        }
    }
    
    logger.info(f"[DATA INTEGRITY] /api/admin/analytics: period={days}d, leads_count={len(leads_per_day)}, top_products={len(top_products)}, top_sellers={len(top_sellers)}")
    
    return analytics


# === Admin KPI Metrics Endpoint ===

@api_router.get("/admin/kpi-metrics")
async def admin_get_kpi_metrics(admin: dict = Depends(require_admin)):
    """
    Admin KPI metrics for revenue, subscriptions, and monetization signals.
    
    Returns comprehensive business metrics for the analytics dashboard:
    - Seller overview (total, active pro, conversion rate)
    - Subscription health (renewals, expired, churn)
    - Usage & monetization signals (limit exhaustion, upgrade interest)
    - Revenue metrics (current quarter)
    """
    now = datetime.now(timezone.utc)
    
    # Quarter calculation
    current_quarter = (now.month - 1) // 3
    quarter_start = datetime(now.year, current_quarter * 3 + 1, 1)
    
    # Month calculation
    month_start = datetime(now.year, now.month, 1)
    
    # === Seller Overview ===
    total_sellers = await db.users.count_documents({"isSeller": True})
    pro_sellers = await db.users.count_documents({
        "isSeller": True,
        "subscription.plan": "pro",
        "subscription.end_date": {"$gte": now}
    })
    trial_sellers = await db.users.count_documents({
        "isSeller": True,
        "subscription.plan": "trial",
        "subscription.end_date": {"$gte": now}
    })
    free_sellers = total_sellers - pro_sellers - trial_sellers
    
    # Conversion rate (Free → Pro)
    conversion_rate = (pro_sellers / total_sellers * 100) if total_sellers > 0 else 0
    
    # === Subscription Health ===
    # Renewals this quarter (users who renewed - have start_date in this quarter)
    renewals_this_quarter = await db.users.count_documents({
        "isSeller": True,
        "subscription.plan": "pro",
        "subscription.start_date": {"$gte": quarter_start}
    })
    
    # Expired subscriptions (end_date passed)
    expired_subscriptions = await db.users.count_documents({
        "isSeller": True,
        "subscription.end_date": {"$lt": now},
        "subscription.plan": {"$in": ["pro", "trial"]}
    })
    
    # Churn rate calculation
    total_ever_subscribed = pro_sellers + expired_subscriptions
    churn_rate = (expired_subscriptions / total_ever_subscribed * 100) if total_ever_subscribed > 0 else 0
    
    # Expiring soon (next 7 days)
    expiring_soon = await db.users.count_documents({
        "isSeller": True,
        "subscription.end_date": {
            "$gte": now,
            "$lte": now + timedelta(days=7)
        }
    })
    
    # === Usage & Monetization Signals ===
    # Free sellers who hit their inquiry limit this month
    FREE_MONTHLY_LIMIT = 5
    
    # Count free sellers who have accepted >= 5 inquiries this month
    limit_exhaustion_pipeline = [
        {
            "$match": {
                "status": "accepted",
                "acceptedAt": {"$gte": month_start}
            }
        },
        {
            "$group": {
                "_id": "$sellerId",
                "acceptedCount": {"$sum": 1}
            }
        },
        {
            "$match": {
                "acceptedCount": {"$gte": FREE_MONTHLY_LIMIT}
            }
        }
    ]
    sellers_at_limit = await db.inquiries.aggregate(limit_exhaustion_pipeline).to_list(None)
    
    # Filter to only free sellers
    sellers_at_limit_count = 0
    for seller in sellers_at_limit:
        if seller["_id"]:
            try:
                user = await db.users.find_one(
                    {"_id": ObjectId(seller["_id"])},
                    projection={"subscription": 1}
                )
                if user and user.get("subscription", {}).get("plan", "free") == "free":
                    sellers_at_limit_count += 1
            except:
                pass
    
    limit_exhaustion_rate = (sellers_at_limit_count / free_sellers * 100) if free_sellers > 0 else 0
    
    # === Revenue Metrics (Placeholder - would come from payment system) ===
    # Since we don't have actual payment integration, estimate based on Pro count
    QUARTERLY_PRICE = 999  # INR
    estimated_revenue_quarter = pro_sellers * QUARTERLY_PRICE
    
    # === Growth Trends (last 6 months) ===
    growth_trends = []
    for i in range(5, -1, -1):
        trend_month = now - timedelta(days=i * 30)
        month_name = trend_month.strftime("%b %Y")
        
        # Count sellers registered by that point
        sellers_by_month = await db.users.count_documents({
            "isSeller": True,
            "createdAt": {"$lte": trend_month}
        })
        
        # Count pro sellers at that point
        pro_by_month = await db.users.count_documents({
            "isSeller": True,
            "subscription.plan": "pro",
            "subscription.start_date": {"$lte": trend_month}
        })
        
        # Count inquiries for that month
        month_start_trend = datetime(trend_month.year, trend_month.month, 1)
        month_end_trend = month_start_trend + timedelta(days=30)
        inquiries_month = await db.inquiries.count_documents({
            "createdAt": {"$gte": month_start_trend, "$lt": month_end_trend}
        })
        
        growth_trends.append({
            "month": month_name,
            "totalSellers": sellers_by_month,
            "proSellers": pro_by_month,
            "freeSellers": sellers_by_month - pro_by_month,
            "inquiries": inquiries_month,
            "revenue": pro_by_month * QUARTERLY_PRICE // 3  # Monthly estimate
        })
    
    # === Auto-Generated Insights ===
    insights = []
    
    if limit_exhaustion_rate >= 30:
        insights.append({
            "type": "positive",
            "message": f"Free limit exhaustion is at {round(limit_exhaustion_rate, 1)}%, indicating strong upgrade pressure."
        })
    elif limit_exhaustion_rate >= 15:
        insights.append({
            "type": "neutral",
            "message": f"Free limit exhaustion is at {round(limit_exhaustion_rate, 1)}%, moderate upgrade pressure."
        })
    
    if conversion_rate >= 8:
        insights.append({
            "type": "positive",
            "message": f"Conversion rate is {round(conversion_rate, 1)}%, above SaaS industry average."
        })
    elif conversion_rate >= 3:
        insights.append({
            "type": "neutral",
            "message": f"Conversion rate is {round(conversion_rate, 1)}%, within SaaS industry range."
        })
    else:
        insights.append({
            "type": "warning",
            "message": f"Conversion rate is {round(conversion_rate, 1)}%, below SaaS industry average. Consider optimizing pricing page."
        })
    
    if churn_rate <= 5:
        insights.append({
            "type": "positive",
            "message": f"Churn rate is {round(churn_rate, 1)}%, indicating healthy retention."
        })
    elif churn_rate <= 10:
        insights.append({
            "type": "neutral",
            "message": f"Churn rate is {round(churn_rate, 1)}%, monitor for improvement opportunities."
        })
    else:
        insights.append({
            "type": "warning",
            "message": f"Churn rate is {round(churn_rate, 1)}%, consider retention initiatives."
        })
    
    kpi_metrics = {
        "sellerOverview": {
            "totalSellers": total_sellers,
            "proSellers": pro_sellers,
            "trialSellers": trial_sellers,
            "freeSellers": free_sellers,
            "conversionRate": round(conversion_rate, 1)
        },
        "subscriptionHealth": {
            "renewals_this_quarter": renewals_this_quarter,
            "expiredSubscriptions": expired_subscriptions,
            "churnRate": round(churn_rate, 1),
            "expiringSoon": expiring_soon
        },
        "monetizationSignals": {
            "free_sellers_at_limit": sellers_at_limit_count,
            "limit_exhaustion_rate": round(limit_exhaustion_rate, 1),
            "free_monthly_limit": FREE_MONTHLY_LIMIT
        },
        "revenue": {
            "quarterlyPrice": QUARTERLY_PRICE,
            "estimated_quarterly_revenue": estimated_revenue_quarter,
            "currency": "INR"
        },
        "growthTrends": growth_trends,
        "insights": insights,
        "generatedAt": now.isoformat()
    }
    
    logger.info(f"[DATA INTEGRITY] /api/admin/kpi-metrics: sellers={total_sellers}, pro={pro_sellers}, conversion={round(conversion_rate, 1)}%")
    
    return kpi_metrics


# ============== ADMIN LISTINGS (SELLER_LISTINGS SSOT) ==============
# 
# This is the Admin governance panel for seller_listings collection.
# SINGLE SOURCE OF TRUTH for all commercial data (pricing, stock, etc.)
#

@api_router.get("/admin/listings")
async def admin_get_listings(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    seller_id: Optional[str] = Query(None, description="Filter by seller ID"),
    status: Optional[str] = Query(None, description="Filter by status (active/inactive)"),
    low_stock: Optional[int] = Query(None, description="Filter listings with stock <= this value"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("createdAt", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    admin: dict = Depends(require_admin)
):
    """
    Admin Listings Panel - View and manage seller_listings collection.
    
    This endpoint provides a governance view of all commercial listings.
    Returns listings with joined product and seller information.
    
    Filters:
    - product_id: Filter by product
    - seller_id: Filter by seller  
    - status: "active" or "inactive"
    - low_stock: Show listings with stock <= threshold
    
    Returns:
    - listings: Array of listing documents with product/seller info
    - total: Total count
    - page: Current page
    - pages: Total pages
    """
    listing_service = ListingService(db)
    
    skip = (page - 1) * limit
    order = -1 if sort_order.lower() == "desc" else 1
    
    result = await listing_service.get_listings_for_admin(
        product_id=product_id,
        seller_id=seller_id,
        status=status,
        low_stock_threshold=low_stock,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=order
    )
    
    logger.info(f"[DATA INTEGRITY] /api/admin/listings: total={result['total']}, page={result['page']}, pages={result['pages']}, result_count={len(result['listings'])}")
    
    # ENTERPRISE STANDARD: Always serialize before return
    return success_response(result)


@api_router.get("/admin/listings/{listing_id}")
async def admin_get_listing_detail(
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Get detailed listing information including product and seller data.
    """
    listing_service = ListingService(db)
    
    listing = await listing_service.get_listing_by_id(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Get product info
    product = await db.products.find_one({"_id": ObjectId(listing["productId"])})
    
    # Get seller info
    seller = await db.users.find_one(
        {"_id": ObjectId(listing["sellerId"])},
        {"_id": 1, "businessName": 1, "email": 1, "phone": 1, "city": 1, "state": 1}
    )
    
    # Compute aggregates for this product
    aggregates = await listing_service.get_product_aggregates(listing["productId"])
    
    return {
        "listing": listing,
        "product": serialize_mongo_doc(product) if product else None,
        "seller": serialize_mongo_doc(seller) if seller else None,
        "productAggregates": aggregates
    }


@api_router.patch("/admin/listings/{listing_id}")
async def admin_update_listing(
    listing_id: str,
    updates: Dict[str, Any] = Body(...),
    admin: dict = Depends(require_admin)
):
    """
    Admin update listing - can change status, stock, pricing tiers.
    
    Allowed fields:
    - status: "active" | "inactive"
    - stock: number
    - leadTime: number
    - pricingTiers: array of {minQty, maxQty, pricePerUnit}
    - currency: string
    """
    listing_service = ListingService(db)
    
    updated = await listing_service.update_listing(listing_id, updates)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    logger.info(f"[ADMIN] Updated listing {listing_id} by admin {admin.get('_id')}")
    
    return {"message": "Listing updated", "listing": updated}


@api_router.delete("/admin/listings/{listing_id}")
async def admin_delete_listing(
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Admin hard delete a listing.
    Use with caution - prefer toggling status to inactive.
    """
    listing_service = ListingService(db)
    
    deleted = await listing_service.delete_listing(listing_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    logger.info(f"[ADMIN] Deleted listing {listing_id} by admin {admin.get('_id')}")
    
    return {"message": "Listing deleted"}


@api_router.post("/admin/listings/{listing_id}/toggle-status")
async def admin_toggle_listing_status(
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Toggle listing status between active and inactive.
    """
    listing_service = ListingService(db)
    
    updated = await listing_service.toggle_listing_status(listing_id)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    logger.info(f"[ADMIN] Toggled listing {listing_id} status to {updated.get('status')} by admin {admin.get('_id')}")
    
    return {"message": f"Listing status changed to {updated.get('status')}", "listing": updated}


@api_router.post("/admin/listings/cleanup-orphaned")
async def admin_cleanup_orphaned_listings(
    dry_run: bool = Query(True, description="If true, only report orphaned listings without deleting"),
    admin: dict = Depends(require_admin)
):
    """
    Find and optionally cleanup orphaned listings.
    
    Orphaned listings are those where:
    - The referenced product has been deleted
    - The referenced seller/user has been deleted
    
    Args:
        dry_run: If true, only report orphaned listings. If false, delete them.
    
    Returns:
        List of orphaned listing IDs and cleanup status.
    """
    # Find all listings
    listings = await db.sellerListings.find({}).to_list(1000)
    
    orphaned = []
    
    for listing in listings:
        listing_id = str(listing.get("_id"))
        product_id = listing.get("productId")
        seller_id = listing.get("sellerId")
        
        issues = []
        
        # Check product exists
        if product_id:
            product = await db.products.find_one({"_id": product_id})
            if not product:
                issues.append(f"Product {product_id} not found")
        else:
            issues.append("Missing productId")
        
        # Check seller exists
        if seller_id:
            seller = await db.users.find_one({"_id": seller_id})
            if not seller:
                issues.append(f"Seller {seller_id} not found")
        else:
            issues.append("Missing sellerId")
        
        if issues:
            orphaned.append({
                "listingId": listing_id,
                "productId": str(product_id) if product_id else None,
                "sellerId": str(seller_id) if seller_id else None,
                "issues": issues,
                "status": listing.get("status"),
                "createdAt": listing.get("createdAt").isoformat() if listing.get("createdAt") else None
            })
    
    deleted_count = 0
    if not dry_run and orphaned:
        # Delete orphaned listings
        orphaned_ids = [ObjectId(o["listingId"]) for o in orphaned]
        result = await db.sellerListings.delete_many({"_id": {"$in": orphaned_ids}})
        deleted_count = result.deleted_count
        logger.warning(f"[ADMIN CLEANUP] Deleted {deleted_count} orphaned listings by admin {admin.get('_id')}")
    
    return {
        "orphanedCount": len(orphaned),
        "orphanedListings": orphaned,
        "dryRun": dry_run,
        "deletedCount": deleted_count,
        "message": f"Found {len(orphaned)} orphaned listings" + (f", deleted {deleted_count}" if not dry_run else " (dry run - no changes made)")
    }


@api_router.get("/admin/listings/health")
async def admin_listings_health_check(
    admin: dict = Depends(require_admin)
):
    """
    Health check for listings data integrity.
    Returns statistics about listings and any data issues.
    """
    total_listings = await db.sellerListings.count_documents({})
    active_listings = await db.sellerListings.count_documents({"status": "active"})
    inactive_listings = await db.sellerListings.count_documents({"status": "inactive"})
    
    # Check for orphaned references
    pipeline = [
        {
            "$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "product"
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "sellerId",
                "foreignField": "_id",
                "as": "seller"
            }
        },
        {
            "$project": {
                "hasProduct": {"$gt": [{"$size": "$product"}, 0]},
                "hasSeller": {"$gt": [{"$size": "$seller"}, 0]}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "orphanedProducts": {"$sum": {"$cond": ["$has_product", 0, 1]}},
                "orphanedSellers": {"$sum": {"$cond": ["$has_seller", 0, 1]}}
            }
        }
    ]
    
    result = await db.sellerListings.aggregate(pipeline).to_list(1)
    
    health_data = result[0] if result else {"total": 0, "orphanedProducts": 0, "orphanedSellers": 0}
    
    # Check for missing fields
    missing_product_id = await db.sellerListings.count_documents({"productId": {"$exists": False}})
    missing_seller_id = await db.sellerListings.count_documents({"sellerId": {"$exists": False}})
    string_product_ids = await db.sellerListings.count_documents({"productId": {"$type": "string"}})
    string_seller_ids = await db.sellerListings.count_documents({"sellerId": {"$type": "string"}})
    
    return {
        "status": "healthy" if health_data.get("orphanedProducts", 0) == 0 and health_data.get("orphanedSellers", 0) == 0 else "issues_found",
        "totalListings": total_listings,
        "activeListings": active_listings,
        "inactiveListings": inactive_listings,
        "orphanedProducts": health_data.get("orphanedProducts", 0),
        "orphanedSellers": health_data.get("orphanedSellers", 0),
        "missing_product_id": missing_product_id,
        "missing_sellerId": missing_seller_id,
        "string_product_ids": string_product_ids,
        "string_seller_ids": string_seller_ids,
        "issues": [
            f"{health_data.get('orphaned_products', 0)} listings with deleted products",
            f"{health_data.get('orphaned_sellers', 0)} listings with deleted sellers",
            f"{missing_product_id} listings missing productId",
            f"{missing_seller_id} listings missing sellerId",
            f"{string_product_ids} listings with string productId (should be ObjectId)",
            f"{string_seller_ids} listings with string sellerId (should be ObjectId)"
        ] if any([
            health_data.get("orphanedProducts", 0),
            health_data.get("orphanedSellers", 0),
            missing_product_id,
            missing_seller_id,
            string_product_ids,
            string_seller_ids
        ]) else []
    }


# ============== ADMIN LISTINGS - DROPDOWN DATA ==============
# 
# These endpoints provide searchable dropdown data for filtering listings
#

@api_router.get("/admin/listings/dropdown/products")
async def admin_get_products_for_dropdown(
    search: Optional[str] = Query(None, description="Search term for product name"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    admin: dict = Depends(require_admin)
):
    """
    Get products for searchable dropdown filter.
    Returns minimal data: _id and name only.
    """
    # Include products with status=active, status=None, or no status field
    query = {
        "$or": [
            {"status": "active"},
            {"status": None},
            {"status": {"$exists": False}}
        ]
    }
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    cursor = db.products.find(
        query,
        {"_id": 1, "name": 1, "category_id": 1}
    ).sort("name", 1).limit(limit)
    
    products = await cursor.to_list(length=limit)
    
    return {
        "products": [
            {
                "_id": str(p["_id"]),
                "name": p.get("name", "Unknown")
            }
            for p in products
        ]
    }


@api_router.get("/admin/listings/dropdown/sellers")
async def admin_get_sellers_for_dropdown(
    search: Optional[str] = Query(None, description="Search term for seller name/email"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    admin: dict = Depends(require_admin)
):
    """
    Get sellers for searchable dropdown filter.
    Returns minimal data: _id, business_name, email.
    """
    query = {"isSeller": True}
    if search:
        query["$or"] = [
            {"businessName": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = db.users.find(
        query,
        {"_id": 1, "businessName": 1, "email": 1}
    ).sort("businessName", 1).limit(limit)
    
    sellers = await cursor.to_list(length=limit)
    
    return {
        "sellers": [
            {
                "_id": str(s["_id"]),
                "businessName": s.get("businessName") or s.get("email", "Unknown"),
                "email": s.get("email", "")
            }
            for s in sellers
        ]
    }


# ============== SELLER BADGE SYSTEM ==============
# Badge Types: none, choice (UdyogConnect Choice), trusted (UdyogConnect Trusted)

VALID_BADGE_TYPES = ["none", "choice", "trusted"]

class UpdateBadgeRequest(BaseModel):
    badgeType: str = Field(..., description="Badge type: none, choice, or trusted")
    
    @field_validator('badgeType')
    @classmethod
    def validate_badge_type(cls, v):
        if v not in VALID_BADGE_TYPES:
            raise ValueError(f"Invalid badge type. Must be one of: {VALID_BADGE_TYPES}")
        return v


@api_router.put("/admin/sellers/{seller_id}/badge")
async def admin_update_seller_badge(
    seller_id: str,
    request: UpdateBadgeRequest,
    admin: dict = Depends(require_admin)
):
    """
    Admin endpoint to update seller badge.
    
    Badge Types:
    - none: No badge
    - choice: UdyogConnect Choice (yellow badge)
    - trusted: UdyogConnect Trusted (green badge)
    """
    try:
        seller_oid = ObjectId(seller_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid seller ID format")
    
    # Verify seller exists
    seller = await db.users.find_one({"_id": seller_oid, "isSeller": True})
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Update badge
    result = await db.users.update_one(
        {"_id": seller_oid},
        {
            "$set": {
                "badgeType": request.badgeType,
                "badgeUpdatedAt": datetime.now(timezone.utc),
                "badgeUpdatedBy": str(admin["_id"])
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update badge")
    
    logger.info(f"Admin {admin.get('email')} updated seller {seller_id} badge to {request.badgeType}")
    
    return {
        "success": True,
        "message": f"Badge updated to {request.badgeType}",
        "sellerId": seller_id,
        "badgeType": request.badgeType
    }


@api_router.get("/admin/sellers")
async def admin_get_sellers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    badgeFilter: Optional[str] = Query(None, description="Filter by badge type"),
    admin: dict = Depends(require_admin)
):
    """
    Admin endpoint to get all sellers with badge info.
    """
    query = {"isSeller": True}
    
    if search:
        query["$or"] = [
            {"businessName": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"gstNumber": {"$regex": search, "$options": "i"}}
        ]
    
    if badgeFilter and badgeFilter in VALID_BADGE_TYPES:
        query["badgeType"] = badgeFilter
    
    skip = (page - 1) * limit
    
    total = await db.users.count_documents(query)
    
    cursor = db.users.find(
        query,
        {
            "_id": 1, "businessName": 1, "email": 1, "phone": 1,
            "gstNumber": 1, "gstVerified": 1, "badgeType": 1,
            "city": 1, "state": 1, "createdAt": 1, "status": 1
        }
    ).sort("createdAt", -1).skip(skip).limit(limit)
    
    sellers = await cursor.to_list(length=limit)
    
    return {
        "sellers": [
            {
                "_id": str(s["_id"]),
                "businessName": s.get("businessName", ""),
                "email": s.get("email", ""),
                "phone": s.get("phone", ""),
                "gstNumber": s.get("gstNumber", ""),
                "gstVerified": s.get("gstVerified", False),
                "badgeType": s.get("badgeType", "none"),
                "city": s.get("city", ""),
                "state": s.get("state", ""),
                "createdAt": s.get("createdAt").isoformat() if s.get("createdAt") else None,
                "status": s.get("status", "active")
            }
            for s in sellers
        ],
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit
    }


# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "B2B Marketplace API", "status": "running"}



# ================== HEALTH ENDPOINTS ==================
#
# HEALTH CHECK STRATEGY:
# ======================
#
# /api/health (PUBLIC - Liveness Probe)
# - Purpose: Kubernetes/Docker liveness check
# - Returns: 200 if app process is running
# - Does NOT check dependencies
# - Safe to expose publicly (reveals nothing sensitive)
# - Use case: Load balancer health checks, uptime monitoring
#
# /api/health/ready (SEMI-PUBLIC - Readiness Probe)
# - Purpose: Kubernetes readiness check
# - Returns: 200 if app can serve requests (DB connected)
# - Checks: MongoDB (required), Firebase (optional)
# - Returns 503 if critical dependencies are down
# - Use case: K8s to know when to route traffic
# - Note: Exposes dependency status - consider restricting in production
#
# /api/health/detailed (ADMIN ONLY)
# - Purpose: Debugging and diagnostics
# - Returns: Full system stats, collection counts, metrics
# - Requires admin authentication
# - Never expose publicly
#

@api_router.get("/health")
async def health_check():
    """
    Liveness Probe (PUBLIC)
    
    Purpose: Confirm the application process is running.
    
    Usage:
    - Kubernetes livenessProbe
    - Load balancer health checks
    - Uptime monitoring services (Pingdom, UptimeRobot)
    
    This endpoint:
    - Does NOT check MongoDB, Firebase, or any dependency
    - Returns 200 as long as the Python process is alive
    - Is intentionally lightweight (no DB calls)
    
    Returns:
        200: {"status": "healthy", "timestamp": "..."}
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@api_router.get("/health/ready")
async def readiness_check():
    """
    Readiness Probe (SEMI-PUBLIC)
    
    Purpose: Confirm the application can serve requests.
    
    Usage:
    - Kubernetes readinessProbe
    - Deployment verification
    - CI/CD pipeline health checks
    
    This endpoint checks:
    - MongoDB: REQUIRED (503 if unavailable)
    - Firebase: OPTIONAL (warning only, doesn't affect status)
    
    Security Note:
    - Exposes dependency health status
    - Consider restricting to internal networks in production
    - Does NOT expose credentials or sensitive data
    
    Returns:
        200: All critical dependencies healthy
        503: One or more critical dependencies unavailable
    """
    checks = {
        "mongodb": {"status": "unknown", "latency_ms": None},
        "firebase": {"status": "unknown"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    overall_healthy = True

    # ---------- MongoDB (REQUIRED) ----------
    try:
        start = time.time()
        await db.command("ping")
        latency = (time.time() - start) * 1000

        checks["mongodb"] = {
            "status": "connected",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        checks["mongodb"] = {
            "status": "error",
            "error": str(e) if not IS_PRODUCTION else "Connection failed"
        }
        overall_healthy = False
        metrics.record_db_error("health_check", str(e))

    # ---------- Firebase (OPTIONAL) ----------
    if firebase_initialized:
        try:
            firebase_auth.list_users(max_results=1)
            checks["firebase"] = {
                "status": "initialized",
                "sdkReady": True
            }
        except Exception:
            # Firebase issues don't make the app unhealthy
            checks["firebase"] = {
                "status": "warning",
                "sdkReady": True,
                "note": "SDK initialized but may have issues"
            }
    else:
        checks["firebase"] = {
            "status": "disabled",
            "sdkReady": False,
            "note": "Firebase not configured"
        }

    checks["overall"] = "healthy" if overall_healthy else "degraded"
    status_code = 200 if overall_healthy else 503

    return JSONResponse(content=checks, status_code=status_code)


@api_router.get("/health/db-info")
async def db_info_check():
    """
    Database Information Endpoint (PUBLIC - for debugging)
    
    Returns database name, collections, and user count.
    Useful for verifying the correct database is connected.
    
    NOTE: Remove or restrict this endpoint in production after verification.
    """
    try:
        # Get database name
        db_name = db.name
        
        # List collections
        collections = await db.list_collection_names()
        
        # Count users
        user_count = await db.users.count_documents({})
        
        # Get sample firebaseUid (masked for privacy)
        sample_user = await db.users.find_one({}, {"firebaseUid": 1, "_id": 0})
        sample_uid = None
        if sample_user and sample_user.get("firebaseUid"):
            uid = sample_user["firebaseUid"]
            sample_uid = f"{uid[:8]}...{uid[-4:]}" if len(uid) > 12 else uid
        
        return {
            "status": "connected",
            "databaseName": db_name,
            "expectedDatabase": "b2b_marketplace",
            "databaseCorrect": db_name == "b2b_marketplace",
            "collections": sorted(collections),
            "collectionCount": len(collections),
            "userCount": user_count,
            "sample_firebaseUid_masked": sample_uid,
            "env_db_name": DB_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "env_db_name": DB_NAME
            },
            status_code=500
        )


@api_router.post("/admin/migrate/normalize-category-ids")
async def admin_migrate_category_ids(admin: dict = Depends(require_admin)):
    """
    One-time migration to normalize categoryId field in products collection.
    
    This fixes the issue where some products have:
    - category_id (string) 
    - categoryId (ObjectId)
    
    After this migration, all products will have both fields for backward compatibility.
    """
    fixed_count = 0
    errors = []
    
    # Find all products
    products = await db.products.find({}).to_list(1000)
    
    for prod in products:
        update_needed = {}
        
        # Case 1: Has category_id (string) but no categoryId (ObjectId)
        if "category_id" in prod and "categoryId" not in prod:
            try:
                update_needed["categoryId"] = ObjectId(prod["category_id"])
            except Exception as e:
                errors.append(f"Product {prod['_id']}: Invalid category_id format - {e}")
                continue
        
        # Case 2: Has categoryId (ObjectId) but no category_id (string)
        elif "categoryId" in prod and "category_id" not in prod:
            update_needed["category_id"] = str(prod["categoryId"])
        
        # Case 3: Has category_id as string but categoryId is also string (wrong type)
        elif "categoryId" in prod and isinstance(prod["categoryId"], str):
            try:
                update_needed["categoryId"] = ObjectId(prod["categoryId"])
            except Exception as e:
                errors.append(f"Product {prod['_id']}: Invalid categoryId format - {e}")
                continue
        
        if update_needed:
            await db.products.update_one(
                {"_id": prod["_id"]},
                {"$set": update_needed}
            )
            fixed_count += 1
    
    logger.info(f"Admin {admin['email']} ran category ID migration: {fixed_count} products fixed")
    
    return {
        "message": f"Migration complete. Fixed {fixed_count} products.",
        "fixedCount": fixed_count,
        "errors": errors,
        "totalProducts": len(products)
    }


# ================================================================
# MIGRATION ENDPOINT REMOVED - 2026-02-25
# The temporary populate-listing-locations-2024-temp endpoint
# has been removed for security. Never leave admin/migration
# endpoints publicly accessible.
# ================================================================

# @api_router.post("/admin/migrate/populate-listing-locations-2024-temp")
async def _REMOVED_admin_populate_listing_locations_temp(admin: dict = Depends(require_admin)):
    """
    TEMPORARY: One-time migration to populate city/state on sellerListings.
    
    SECURITY:
    - Admin-only access
    - Idempotent (only updates missing fields)
    - Must be removed immediately after execution
    
    DELETE THIS ENDPOINT AFTER RUNNING!
    """
    migration_start = datetime.now(timezone.utc)
    
    # Log migration attempt
    logger.warning(f"[MIGRATION] Admin {admin.get('email', 'unknown')} initiated listing location migration at {migration_start.isoformat()}")
    
    try:
        # Find only listings with missing city/state (idempotent)
        listings_to_update = await db.sellerListings.find({
            "$or": [
                {"city": {"$exists": False}},
                {"state": {"$exists": False}},
                {"city": None},
                {"state": None},
                {"city": ""},
                {"state": ""}
            ]
        }).to_list(None)
        
        total_listings = await db.sellerListings.count_documents({})
        
        logger.info(f"[MIGRATION] Found {len(listings_to_update)} listings needing update out of {total_listings} total")
        
        if not listings_to_update:
            return {
                "status": "success",
                "message": "No listings need updating. Migration already complete.",
                "processed": 0,
                "updated": 0,
                "skipped": total_listings,
                "timestamp": migration_start.isoformat()
            }
        
        # Collect unique seller IDs
        seller_ids = list(set(l.get("sellerId") for l in listings_to_update if l.get("sellerId")))
        
        # Batch fetch seller profiles
        seller_profiles = {}
        if seller_ids:
            sellers = await db.users.find(
                {"_id": {"$in": seller_ids}},
                {"profile.city": 1, "profile.state": 1}
            ).to_list(None)
            
            for s in sellers:
                profile = s.get("profile", {})
                seller_profiles[str(s["_id"])] = {
                    "city": profile.get("city"),
                    "state": profile.get("state")
                }
        
        # Build bulk operations
        from pymongo import UpdateOne
        operations = []
        updated_count = 0
        skipped_count = 0
        seller_not_found = 0
        
        for listing in listings_to_update:
            seller_id = str(listing.get("sellerId", ""))
            seller_info = seller_profiles.get(seller_id)
            
            if not seller_info:
                seller_not_found += 1
                continue
            
            # Only update if seller has location data
            if not seller_info.get("city") and not seller_info.get("state"):
                skipped_count += 1
                continue
            
            # Prepare update (only set non-empty values)
            update_fields = {"updatedAt": datetime.now(timezone.utc)}
            if seller_info.get("city"):
                update_fields["city"] = seller_info["city"]
            if seller_info.get("state"):
                update_fields["state"] = seller_info["state"]
            
            operations.append(UpdateOne(
                {"_id": listing["_id"]},
                {"$set": update_fields}
            ))
            updated_count += 1
        
        # Execute bulk write
        if operations:
            result = await db.sellerListings.bulk_write(operations, ordered=False)
            actual_modified = result.modified_count
        else:
            actual_modified = 0
        
        migration_end = datetime.now(timezone.utc)
        duration_ms = int((migration_end - migration_start).total_seconds() * 1000)
        
        # Log success
        logger.warning(f"[MIGRATION] COMPLETE - Admin: {admin.get('email')}, Updated: {actual_modified}, Skipped: {skipped_count}, SellerNotFound: {seller_not_found}, Duration: {duration_ms}ms")
        
        return {
            "status": "success",
            "message": f"Migration complete. Updated {actual_modified} listings.",
            "processed": len(listings_to_update),
            "updated": actual_modified,
            "skipped": skipped_count,
            "sellerNotFound": seller_not_found,
            "totalListings": total_listings,
            "durationMs": duration_ms,
            "timestamp": migration_start.isoformat(),
            "adminEmail": admin.get("email"),
            "reminder": "DELETE THIS ENDPOINT IMMEDIATELY AFTER VERIFYING SUCCESS"
        }
        
    except Exception as e:
        logger.error(f"[MIGRATION] FAILED - Admin: {admin.get('email')}, Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


# ================== MIGRATION ENDPOINT REMOVED ==================
# Endpoint was removed on 2026-02-25 for security
# ============================================================


# ================== ENTERPRISE MIGRATION ENDPOINTS ==================

@api_router.get("/admin/enterprise/status")
async def get_enterprise_migration_status(admin: dict = Depends(require_admin)):
    """Get current enterprise migration status."""
    from services.enterprise_migration import EnterpriseMigrationService
    
    migration_service = EnterpriseMigrationService(db)
    status = await migration_service.get_migration_status()
    
    return {
        "status": "ready" if status["migrationComplete"] else "pending",
        **status
    }


@api_router.post("/admin/enterprise/migrate")
async def run_enterprise_migration(admin: dict = Depends(require_admin)):
    """
    Run enterprise migration on all sellerListings.
    
    Creates:
    - productVariants for each unique attribute combination
    - searchableAttributes denormalized on listings
    - searchableText for full-text search
    """
    from services.enterprise_migration import EnterpriseMigrationService
    
    migration_service = EnterpriseMigrationService(db)
    results = await migration_service.run_full_migration()
    
    logger.info(f"Admin {admin['email']} ran enterprise migration: {results['migrated']} migrated, {results['skipped']} skipped")
    
    return {
        "message": "Enterprise migration complete",
        **results
    }


@api_router.post("/admin/enterprise/indexes")
async def create_enterprise_indexes(admin: dict = Depends(require_admin)):
    """Create enterprise indexes for optimized search."""
    from services.enterprise_migration import EnterpriseMigrationService
    
    migration_service = EnterpriseMigrationService(db)
    results = await migration_service.create_indexes()
    
    logger.info(f"Admin {admin['email']} created enterprise indexes: {results['created']}")
    
    return {
        "message": "Enterprise indexes created",
        **results
    }


# ================== MOUNT ROUTER ==================

# Include the api_router in the app
app.include_router(api_router)

# ================== ENTERPRISE PRODUCT ROUTER ==================
# Phase: Enterprise-grade product pages with structured search

from routers.enterprise_products import create_enterprise_product_router
enterprise_product_router = create_enterprise_product_router(db)
app.include_router(enterprise_product_router, prefix="/api")

# Phase: Subscription Payment Router
from routers.subscription_payment_router import create_subscription_payment_router
subscription_payment_router = create_subscription_payment_router(db, get_current_user)
app.include_router(subscription_payment_router, prefix="/api")

# ================== B2B ADMIN ROUTER ==================
# Phase 1: Admin Foundation - Dynamic dropdowns, category settings, spec templates

from b2b_admin import create_b2b_admin_router
b2b_admin_router = create_b2b_admin_router(db, require_admin)
app.include_router(b2b_admin_router, prefix="/api")

# ================== SELLER PRODUCT ROUTER ==================
# Phase 2: Seller-controlled product management

from seller_products import create_seller_router
seller_router = create_seller_router(db, require_auth, require_verified_seller)
app.include_router(seller_router, prefix="/api")

# ================== MANUFACTURER & REQUEST ROUTER ==================
# Product-Manufacturer-Seller model with admin-controlled data

from manufacturers import create_manufacturer_router
manufacturer_router = create_manufacturer_router(
    db, require_admin, require_auth, require_verified_seller, serialize_mongo_doc
)
app.include_router(manufacturer_router, prefix="/api")

# ================== QUOTATION ROUTER ==================
# Hybrid RFQ → Quote → WhatsApp → Acceptance System
from routers.quotation_router import create_quotation_router
quotation_router = create_quotation_router(db, get_current_user)
app.include_router(quotation_router, prefix="/api")

# ================== ADMIN ANALYTICS ROUTER ==================
# Marketplace Control Center - Admin only
from routers.admin_analytics_router import create_admin_analytics_router
admin_analytics_router = create_admin_analytics_router(db, require_admin)
app.include_router(admin_analytics_router, prefix="/api")

# ================== SELLER PERFORMANCE ROUTER ==================
# Seller Growth Optimization Console
from routers.seller_performance_router import create_seller_performance_router
seller_performance_router = create_seller_performance_router(db, get_current_user)
app.include_router(seller_performance_router, prefix="/api")

# ================== ADMIN GOVERNANCE ROUTER ==================
# Seller Governance & Abuse Monitoring
from routers.admin_governance_router import create_admin_governance_router
admin_governance_router = create_admin_governance_router(db, require_admin)
app.include_router(admin_governance_router, prefix="/api")

# ================== ENTERPRISE SEARCH ROUTER ==================
# Intelligent search with unit normalization, synonyms, geo-filtering
from routers.enterprise_search_router import create_enterprise_search_router
enterprise_search_router = create_enterprise_search_router(db)
app.include_router(enterprise_search_router, prefix="/api")

# ================== ROOT HEALTH CHECK (for Render/Cloud providers) ==================
# This responds at "/" for platforms that check root path for health
# @app.get("/")
# async def root_health():
#     """Root health check for cloud providers like Render"""
#     return {"status": "healthy", "service": "B2B Marketplace API"}

@app.get("/health")
async def root_health_alt():
    """Alternative root health check endpoint - Used by UptimeRobot/external monitors"""
    return {
        "status": "ok",
        "service": "midconnect-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "active"
    }

# ================== APP EVENTS ==================

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection on startup"""
    logger.info("Application starting up...")
    logger.info("✅ Application ready to receive requests")
    
    # IMPORTANT: Don't block startup waiting for MongoDB operations
    # These can run in the background after the server is accepting connections
    # This allows Render to detect the HTTP port quickly
    import asyncio
    
    async def run_enterprise_integrity_check():
        """Run enterprise data integrity check in background"""
        await asyncio.sleep(3)
        try:
            from utils.startup_integrity_check import run_startup_integrity_check
            results = await run_startup_integrity_check(db)
            if not results["passed"]:
                logger.error("🚨 ENTERPRISE DATA INTEGRITY CHECK FAILED - Review errors above")
        except Exception as e:
            logger.warning(f"⚠️ Could not run integrity check: {e}")
    
    # Start integrity check in background
    asyncio.create_task(run_enterprise_integrity_check())
    
    async def initialize_smart_search():
        """Initialize smart search cache in background"""
        await asyncio.sleep(2)
        try:
            from services.smart_search_service import initialize_smart_search_cache
            await initialize_smart_search_cache(db)
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize smart search cache: {e}")
    
    # Start smart search cache initialization in background
    asyncio.create_task(initialize_smart_search())
    
    async def create_indexes_in_background():
        """Create indexes in background to not block startup"""
        # Wait for server to be fully ready and detected by platform
        await asyncio.sleep(5)
        
        logger.info("Starting background index creation...")
        
        async def safe_create_index(collection, keys, index_name="", **kwargs):
            """Safely create an index, logging warnings on failure but not crashing"""
            try:
                await collection.create_index(keys, **kwargs)
                return True
            except Exception as e:
                logger.warning(f"⚠️ Index creation warning for {index_name or str(keys)}: {e}")
                return False
        
        async def safe_drop_index(collection, index_name):
            """Safely drop an index if it exists"""
            try:
                await collection.drop_index(index_name)
                logger.info(f"Dropped old index: {index_name}")
                return True
            except Exception as e:
                # Index doesn't exist or other error - that's fine
                return False
        
        await safe_create_index(db.sellerListings, [("status", 1), ("isActive", 1)], "sellerListings_status", background=True)
        await safe_create_index(db.sellerListings, [("productId", 1)], "sellerListings_productId", background=True)
        await safe_create_index(db.sellerListings, [("sellerId", 1)], "sellerListings_sellerId", background=True)
        await safe_create_index(db.sellerListings, [("productId", 1), ("status", 1), ("isActive", 1)], "sellerListings_compound", background=True)
        
        # products indexes
        await safe_create_index(db.products, [("categoryId", 1)], "products_categoryId", background=True)
        await safe_create_index(db.products, [("slug", 1)], "products_slug", unique=True, sparse=True, background=True)
        await safe_create_index(db.products, [("name", "text")], "products_name_text", background=True)
        
        # users indexes - FIXED: Use partialFilterExpression for firebaseUid
        # This allows multiple users with null firebaseUid while enforcing uniqueness for valid values
        # First, drop the old problematic index if it exists
        await safe_drop_index(db.users, "firebaseUid_1")
        await safe_create_index(
            db.users, 
            [("firebaseUid", 1)], 
            "firebaseUid_1",
            unique=True, 
            background=True,
            partialFilterExpression={
                "firebaseUid": {"$type": "string"}
            }
        )
        await safe_create_index(db.users, [("email", 1)], "users_email", background=True)
        await safe_create_index(db.users, [("isSeller", 1), ("sellerStatus", 1)], "users_seller", background=True)
        
        # categories indexes
        await safe_create_index(db.categories, [("slug", 1)], "categories_slug", unique=True, sparse=True, background=True)
        
        # inquiries indexes
        await safe_create_index(db.inquiries, [("sellerId", 1)], "inquiries_sellerId", background=True)
        await safe_create_index(db.inquiries, [("buyerId", 1)], "inquiries_buyerId", background=True)
        await safe_create_index(db.inquiries, [("createdAt", -1)], "inquiries_created_at", background=True)
        
        # NEW ARCHITECTURE: Index for unverified user cleanup
        await safe_create_index(
            db.users, 
            [("isEmailVerified", 1), ("verificationDeadline", 1)], 
            "users_verification_cleanup",
            background=True
        )
        
        # ARCHITECTURAL FIX: Indexes for Product ↔ SpecTemplate relationship
        await safe_create_index(
            db.products,
            [("specTemplateIds", 1)],
            "products_specTemplateIds",
            background=True
        )
        await safe_create_index(
            db.specTemplates,
            [("categoryId", 1)],
            "specTemplates_categoryId",
            background=True
        )
        await safe_create_index(
            db.specTemplates,
            [("categoryId", 1), ("isActive", 1)],
            "specTemplates_category_active",
            background=True
        )
        
        logger.info("✅ Database indexes creation completed")
    
    async def cleanup_unverified_users_task():
        """
        STEP 5 - AUTO CLEANUP UNVERIFIED USERS
        
        Background task that runs every hour to clean up:
        - MongoDB users with isEmailVerified=false and past verificationDeadline
        - Corresponding Firebase users
        
        This ensures:
        - No orphan Firebase accounts
        - No Mongo-Firebase mismatch
        - Clean re-registration
        """
        while True:
            try:
                # Wait 1 hour between runs
                await asyncio.sleep(3600)  # 3600 seconds = 1 hour
                
                logger.info("🧹 Starting cleanup of unverified users...")
                
                now = datetime.now(timezone.utc)
                
                # Find expired unverified users
                expired_users = db.users.find({
                    "isEmailVerified": False,
                    "verificationDeadline": {"$lt": now}
                })
                
                deleted_count = 0
                
                async for user in expired_users:
                    try:
                        firebase_uid = user.get("firebaseUid")
                        email = user.get("email", "unknown")
                        
                        # Delete from Firebase first
                        if firebase_uid and firebase_initialized:
                            try:
                                firebase_auth.delete_user(firebase_uid)
                                logger.info(f"🧹 Deleted Firebase user: {email}")
                            except Exception as fb_err:
                                # Firebase user might not exist
                                logger.warning(f"⚠️ Could not delete Firebase user {email}: {fb_err}")
                        
                        # Delete from MongoDB
                        await db.users.delete_one({"_id": user["_id"]})
                        logger.info(f"🧹 Deleted expired unverified user: {email}")
                        deleted_count += 1
                        
                    except Exception as user_err:
                        logger.error(f"Error cleaning up user {user.get('email', 'unknown')}: {user_err}")
                
                if deleted_count > 0:
                    logger.info(f"🧹 Cleanup complete: {deleted_count} unverified users removed")
                    
            except Exception as e:
                logger.error(f"Error in cleanup_unverified_users_task: {e}")
    
    # Schedule index creation to run in background, don't await it
    asyncio.create_task(create_indexes_in_background())
    
    # Schedule cleanup task to run in background
    asyncio.create_task(cleanup_unverified_users_task())

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection on shutdown"""
    client.close()
    logger.info("Application shut down")
