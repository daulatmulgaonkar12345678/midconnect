"""
OTP Service for Registration Verification
==========================================

OTP-based email verification that replaces the clickable link system.
This acts as a verification layer BEFORE the existing registration flow.

Security Features:
- 6-digit OTP
- 10-minute expiry
- Max 5 verification attempts per OTP
- Max 5 OTP requests per email per hour
- 30-second resend cooldown
- SHA256 hashed storage

Flow:
1. User enters name + email + password
2. System sends OTP
3. User enters OTP
4. OTP verified → Continue with existing registration flow
"""

import os
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from bson import ObjectId

logger = logging.getLogger(__name__)

# OTP Configuration
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6
MAX_ATTEMPTS = 5
MAX_REQUESTS_PER_HOUR = 5
RESEND_COOLDOWN_SECONDS = 30


class RegistrationOTPService:
    """
    OTP service for new user registration verification.
    
    This replaces the email verification link system.
    After OTP verification, the existing registration flow continues.
    """
    
    def __init__(self, db):
        self.db = db
        self.collection = db.registration_otps
    
    async def _check_rate_limit(self, email: str) -> Dict[str, Any]:
        """
        Check rate limiting for OTP requests.
        
        Returns:
            {
                "allowed": bool,
                "reason": str (if not allowed),
                "cooldown_remaining": int (seconds, if in cooldown)
            }
        """
        email = email.lower().strip()
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        # Count OTPs requested in the last hour
        recent_count = await self.collection.count_documents({
            "email": email,
            "createdAt": {"$gte": one_hour_ago}
        })
        
        if recent_count >= MAX_REQUESTS_PER_HOUR:
            return {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "message": "Too many OTP requests. Please try again after an hour."
            }
        
        # Check resend cooldown - find the most recent OTP
        last_otp = await self.collection.find_one(
            {"email": email},
            sort=[("createdAt", -1)]
        )
        
        if last_otp:
            created_at = last_otp.get("createdAt")
            if created_at:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
                time_since_last = (now - created_at).total_seconds()
                if time_since_last < RESEND_COOLDOWN_SECONDS:
                    cooldown_remaining = int(RESEND_COOLDOWN_SECONDS - time_since_last)
                    return {
                        "allowed": False,
                        "reason": "cooldown",
                        "cooldown_remaining": cooldown_remaining,
                        "message": f"Please wait {cooldown_remaining} seconds before requesting a new OTP."
                    }
        
        return {"allowed": True}
    
    async def request_otp(self, email: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate and send OTP for registration.
        
        Args:
            email: User's email address
            name: User's name (optional, for personalized email)
            
        Returns:
            {
                "success": bool,
                "message": str,
                "expires_at": str (ISO format),
                "cooldown_until": str (ISO format, for resend)
            }
        """
        email = email.lower().strip()
        
        # Check rate limiting
        rate_check = await self._check_rate_limit(email)
        if not rate_check["allowed"]:
            return {
                "success": False,
                "error_code": rate_check["reason"],
                "message": rate_check["message"],
                "cooldown_remaining": rate_check.get("cooldown_remaining")
            }
        
        # Check if email is already registered and verified
        existing_user = await self.db.users.find_one({
            "email": email,
            "isEmailVerified": True,
            "profileComplete": True
        })
        
        if existing_user:
            return {
                "success": False,
                "error_code": "email_already_registered",
                "message": "This email is already registered. Please login instead."
            }
        
        # Generate 6-digit OTP
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
        cooldown_until = now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
        
        # Invalidate any existing unused OTPs for this email
        await self.collection.update_many(
            {"email": email, "isUsed": False, "isVerified": False},
            {"$set": {"isUsed": True, "invalidatedAt": now}}
        )
        
        # Create new OTP record
        otp_record = {
            "email": email,
            "name": name,
            "otpHash": otp_hash,
            "attempts": 0,
            "isUsed": False,
            "isVerified": False,
            "expiresAt": expires_at,
            "createdAt": now
        }
        
        await self.collection.insert_one(otp_record)
        
        # Send OTP email
        email_result = await self._send_otp_email(email, otp, name or "User")
        
        if email_result.get("success"):
            logger.info(f"OTP sent to {email}")
            
            response = {
                "success": True,
                "message": f"OTP sent to {email}. Valid for {OTP_EXPIRY_MINUTES} minutes.",
                "expires_at": expires_at.isoformat(),
                "cooldown_until": cooldown_until.isoformat()
            }
            
            # In mock mode, include OTP in response for testing
            if email_result.get("_mock"):
                logger.info(f"[MOCK] OTP for {email}: {otp}")
                response["_mock"] = True
                response["_otp"] = otp
            
            return response
        else:
            # If email failed, still return success but log warning
            # The OTP exists in DB, they can try to resend
            logger.warning(f"Failed to send OTP email to {email}: {email_result}")
            
            # Check if in mock mode
            if email_result.get("_mock"):
                logger.info(f"[MOCK] OTP for {email}: {otp}")
                return {
                    "success": True,
                    "message": f"OTP sent to {email}. Valid for {OTP_EXPIRY_MINUTES} minutes.",
                    "expires_at": expires_at.isoformat(),
                    "cooldown_until": cooldown_until.isoformat(),
                    "_mock": True,
                    "_otp": otp  # Only in mock mode for testing
                }
            
            return {
                "success": False,
                "error_code": "email_send_failed",
                "message": "Failed to send OTP. Please try again."
            }
    
    async def verify_otp(self, email: str, otp: str) -> Dict[str, Any]:
        """
        Verify OTP for registration.
        
        Args:
            email: User's email address
            otp: 6-digit OTP entered by user
            
        Returns:
            {
                "success": bool,
                "message": str,
                "verified": bool,
                "attempts_remaining": int (if failed)
            }
        """
        email = email.lower().strip()
        otp = otp.strip()
        
        # Validate OTP format
        if not otp or len(otp) != OTP_LENGTH or not otp.isdigit():
            return {
                "success": False,
                "error_code": "invalid_otp_format",
                "message": "Please enter a valid 6-digit OTP."
            }
        
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        
        # Find valid OTP for this email
        otp_record = await self.collection.find_one({
            "email": email,
            "isUsed": False,
            "isVerified": False,
            "expiresAt": {"$gt": now}
        })
        
        if not otp_record:
            # Check if there's an expired OTP
            expired_otp = await self.collection.find_one({
                "email": email,
                "isUsed": False,
                "isVerified": False
            })
            
            if expired_otp:
                return {
                    "success": False,
                    "error_code": "otp_expired",
                    "message": "OTP has expired. Please request a new one."
                }
            
            return {
                "success": False,
                "error_code": "no_otp_found",
                "message": "No OTP found. Please request a new one."
            }
        
        # Check max attempts
        if otp_record["attempts"] >= MAX_ATTEMPTS:
            # Mark as used (exhausted)
            await self.collection.update_one(
                {"_id": otp_record["_id"]},
                {"$set": {"isUsed": True, "exhaustedAt": now}}
            )
            return {
                "success": False,
                "error_code": "max_attempts_exceeded",
                "message": "Too many failed attempts. Please request a new OTP."
            }
        
        # Verify OTP hash
        if otp_record["otpHash"] != otp_hash:
            # Increment attempts
            new_attempts = otp_record["attempts"] + 1
            await self.collection.update_one(
                {"_id": otp_record["_id"]},
                {"$inc": {"attempts": 1}}
            )
            
            attempts_remaining = MAX_ATTEMPTS - new_attempts
            
            if attempts_remaining <= 0:
                return {
                    "success": False,
                    "error_code": "max_attempts_exceeded",
                    "message": "Too many failed attempts. Please request a new OTP."
                }
            
            return {
                "success": False,
                "error_code": "invalid_otp",
                "message": f"Invalid OTP. {attempts_remaining} attempt{'s' if attempts_remaining > 1 else ''} remaining.",
                "attempts_remaining": attempts_remaining
            }
        
        # OTP is valid - mark as verified
        await self.collection.update_one(
            {"_id": otp_record["_id"]},
            {"$set": {
                "isVerified": True,
                "verifiedAt": now
            }}
        )
        
        logger.info(f"OTP verified for {email}")
        
        return {
            "success": True,
            "message": "Email verified successfully.",
            "verified": True,
            "email": email
        }
    
    async def is_email_verified_via_otp(self, email: str) -> bool:
        """
        Check if email has been verified via OTP recently.
        
        This is used to check if the user can proceed with registration.
        OTP verification is valid for 30 minutes after verification.
        """
        email = email.lower().strip()
        verification_valid_until = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        verified_otp = await self.collection.find_one({
            "email": email,
            "isVerified": True,
            "verifiedAt": {"$gte": verification_valid_until}
        })
        
        return verified_otp is not None
    
    async def _send_otp_email(self, email: str, otp: str, name: str) -> Dict[str, Any]:
        """Send OTP email using Resend."""
        from services.email_service import send_email, _get_email_wrapper
        
        # Format OTP with spaces for readability
        formatted_otp = ' '.join(otp)
        
        content = f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Verify Your Email</h2>
        
        <p>Dear {name},</p>
        
        <p>Welcome to Udyog Connect! Please use the following OTP to verify your email address:</p>
        
        <div style="background: linear-gradient(135deg, #0B3C5D 0%, #1a5f8a 100%); padding: 30px; border-radius: 12px; margin: 30px 0; text-align: center;">
            <span style="font-size: 42px; font-weight: bold; color: #ffffff; letter-spacing: 12px; font-family: 'Courier New', monospace;">{formatted_otp}</span>
        </div>
        
        <div style="background: #fff8e1; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <p style="margin: 0; color: #856404;">
                <strong>This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.</strong><br>
                Do not share this code with anyone.
            </p>
        </div>
        
        <p style="color: #666;">If you didn't create an account on Udyog Connect, please ignore this email.</p>
        
        <p>Best Regards,<br>Udyog Connect Team</p>
        """
        
        html = _get_email_wrapper(content, "Verify Your Email - Udyog Connect")
        
        # Plain text fallback
        text = f"""
Welcome to Udyog Connect!

Your verification OTP is: {otp}

This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.
Do not share this code with anyone.

If you didn't create an account on Udyog Connect, please ignore this email.

Best Regards,
Udyog Connect Team
        """
        
        return await send_email(
            to_email=email,
            subject="Your Verification OTP - Udyog Connect",
            html_content=html,
            text_content=text
        )


# Factory function
def get_registration_otp_service(db) -> RegistrationOTPService:
    """Get registration OTP service instance."""
    return RegistrationOTPService(db)
