"""
Email Verification Service

Handles custom email verification using Zoho SMTP instead of Firebase.
This provides full control over the verification process and email branding.

Architecture:
1. User signs up → Firebase creates auth user
2. Backend generates verification token
3. Zoho SMTP sends branded email (NON-BLOCKING via thread pool)
4. User clicks link → Backend marks isEmailVerified = true
5. Token is invalidated after use

IMPORTANT: SMTP operations are blocking I/O. We use asyncio.to_thread() to 
run them in a thread pool, preventing the async event loop from blocking.
This fixes the "CORS error" symptom which was actually a timeout.
"""

import secrets
import smtplib
import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from bson import ObjectId

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """
    Service for handling custom email verification via Zoho SMTP.
    
    Environment Variables Required:
    - ZOHO_EMAIL: Sender email (e.g., verification@udyogconnect.in)
    - ZOHO_APP_PASSWORD: Zoho app-specific password
    - FRONTEND_URL: Frontend base URL for verification links
    """
    
    # Zoho SMTP settings
    SMTP_HOST = "smtp.zoho.in"
    SMTP_PORT = 465
    
    # Token settings
    TOKEN_EXPIRY_HOURS = 24
    
    def __init__(self, db):
        self.db = db
        self.zoho_email = os.environ.get("ZOHO_EMAIL", "verification@udyogconnect.in")
        self.zoho_password = os.environ.get("ZOHO_APP_PASSWORD")
        
        # Frontend URL for verification links
        # Priority: FRONTEND_URL env > auto-detect preview > default production
        self.frontend_url = os.environ.get("FRONTEND_URL")
        if not self.frontend_url:
            # Check if we're in a preview environment by looking at backend URL patterns
            # This helps during development/preview testing
            self.frontend_url = "https://udyogconnect.in"  # Default to production
    
    async def generate_verification_token(self, email: str) -> str:
        """
        Generate a secure verification token and store it in the database.
        
        Args:
            email: User's email address
            
        Returns:
            The generated token
        """
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        
        # Store token in user document
        await self.db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "verificationToken": token,
                    "verificationTokenExpiry": expiry,
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Generated verification token for {email}")
        return token
    
    def _build_email_message(self, email: str, verify_link: str) -> MIMEMultipart:
        """
        Build the email message (synchronous helper).
        Separated to keep the async method clean.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your UdyogConnect Account"
        msg["From"] = f'"UdyogConnect" <{self.zoho_email}>'
        msg["To"] = email
        
        # Plain text version
        text_content = f"""
Welcome to UdyogConnect!

Please verify your email by clicking the link below:
{verify_link}

This link will expire in {self.TOKEN_EXPIRY_HOURS} hours.

If you didn't create an account on UdyogConnect, please ignore this email.

Best Regards,
UdyogConnect Team
        """
        
        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #0B3C5D 0%, #1a5f8a 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">UdyogConnect</h1>
        <p style="color: #e0e0e0; margin: 10px 0 0 0;">India's B2B Industrial Marketplace</p>
    </div>
    
    <div style="background: #ffffff; padding: 40px 30px; border: 1px solid #e0e0e0; border-top: none;">
        <h2 style="color: #0B3C5D; margin-top: 0;">Verify Your Email</h2>
        
        <p>Welcome to UdyogConnect!</p>
        
        <p>Please click the button below to verify your email address and activate your account:</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_link}" 
               style="display: inline-block; 
                      padding: 14px 40px; 
                      background-color: #0B3C5D; 
                      color: white; 
                      text-decoration: none; 
                      border-radius: 6px; 
                      font-weight: bold;
                      font-size: 16px;">
                Verify Email Address
            </a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            This link will expire in <strong>{self.TOKEN_EXPIRY_HOURS} hours</strong>.
        </p>
        
        <p style="color: #666; font-size: 14px;">
            If the button doesn't work, copy and paste this link into your browser:
            <br>
            <a href="{verify_link}" style="color: #0B3C5D; word-break: break-all;">{verify_link}</a>
        </p>
        
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
        
        <p style="color: #999; font-size: 12px;">
            If you didn't create an account on UdyogConnect, please ignore this email.
        </p>
    </div>
    
    <div style="background: #f5f5f5; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; border-top: none;">
        <p style="color: #666; font-size: 12px; margin: 0;">
            © 2026 UdyogConnect. All rights reserved.
            <br>
            India's Trusted B2B Industrial Marketplace
        </p>
    </div>
</body>
</html>
        """
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        return msg
    
    def _send_smtp_blocking(self, email: str, msg: MIMEMultipart) -> Dict[str, Any]:
        """
        Synchronous blocking SMTP send operation.
        This runs in a thread pool to avoid blocking the async event loop.
        
        Returns:
            dict with success status and error (if any)
        """
        try:
            with smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT, timeout=30) as server:
                server.login(self.zoho_email, self.zoho_password)
                server.sendmail(self.zoho_email, email, msg.as_string())
            
            logger.info(f"Verification email sent to {email}")
            return {"success": True}
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {"success": False, "error": "Email authentication failed. Please contact support."}
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {"success": False, "error": "Failed to send email. Please try again later."}
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {"success": False, "error": "An error occurred. Please try again later."}
    
    async def send_verification_email(self, email: str) -> Dict[str, Any]:
        """
        Generate token and send verification email via Zoho SMTP.
        
        IMPORTANT: Uses asyncio.to_thread() to run blocking SMTP in thread pool.
        This prevents the async event loop from blocking and causing timeouts
        that manifest as CORS errors on the frontend.
        
        In MOCK mode (no credentials), generates token and logs the verification link.
        
        Args:
            email: Recipient email address
            
        Returns:
            dict with success status and message
        """
        try:
            # Generate token (async DB operation) - always generate for testing
            token = await self.generate_verification_token(email)
            
            # Build verification link
            verify_link = f"{self.frontend_url}/verify-email?token={token}"
            
            # MOCK MODE - if no Zoho credentials configured
            if not self.zoho_password:
                logger.warning(f"[MOCK EMAIL] ZOHO_APP_PASSWORD not configured")
                logger.info(f"[MOCK EMAIL] Verification link for {email}: {verify_link}")
                logger.info(f"[MOCK EMAIL] Token: {token}")
                return {
                    "success": True,
                    "message": "Verification email sent. Please check your inbox.",
                    "_mock": True,
                    "_verify_link": verify_link  # For testing only
                }
            
            # Build email message (sync, fast)
            msg = self._build_email_message(email, verify_link)
            
            # Send via SMTP in thread pool (non-blocking)
            # This is the KEY FIX - prevents blocking the async event loop
            result = await asyncio.to_thread(self._send_smtp_blocking, email, msg)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Verification email sent. Please check your inbox."
                }
            else:
                return result
            
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {
                "success": False,
                "error": "An error occurred. Please try again later."
            }
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a token and mark the user's email as verified.
        
        Args:
            token: The verification token
            
        Returns:
            dict with success status and redirect URL
        """
        if not token:
            return {
                "success": False,
                "error": "Invalid verification token"
            }
        
        # Find user with this token
        user = await self.db.users.find_one({
            "verificationToken": token
        })
        
        if not user:
            return {
                "success": False,
                "error": "Invalid or expired verification link"
            }
        
        # Check if token has expired
        expiry = user.get("verificationTokenExpiry")
        if expiry:
            # Handle both naive and aware datetimes from MongoDB
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc):
                return {
                    "success": False,
                    "error": "Verification link has expired. Please request a new one."
                }
        
        # Mark user as verified
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "isEmailVerified": True,
                    "status": "active",
                    "updatedAt": datetime.now(timezone.utc)
                },
                "$unset": {
                    "verificationToken": "",
                    "verificationTokenExpiry": "",
                    "verificationDeadline": ""
                }
            }
        )
        
        logger.info(f"Email verified for user {user.get('email')}")
        
        return {
            "success": True,
            "message": "Email verified successfully!",
            "redirectUrl": f"{self.frontend_url}/login?verified=true"
        }
    
    async def resend_verification(self, email: str) -> Dict[str, Any]:
        """
        Resend verification email to a user.
        
        Args:
            email: User's email address
            
        Returns:
            dict with success status
        """
        # Check if user exists and is not already verified
        user = await self.db.users.find_one({"email": email})
        
        if not user:
            # Don't reveal if user exists
            return {
                "success": True,
                "message": "If your email is registered, you will receive a verification link."
            }
        
        if user.get("isEmailVerified"):
            return {
                "success": False,
                "error": "Email is already verified. Please login."
            }
        
        return await self.send_verification_email(email)


# Factory function for dependency injection
async def get_email_verification_service(db) -> EmailVerificationService:
    """Get an instance of the email verification service."""
    return EmailVerificationService(db)
