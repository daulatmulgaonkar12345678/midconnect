"""
RESEND EMAIL SERVICE - Single Source of Truth
==============================================

This is the ONLY email service for the entire application.
All transactional emails are sent via Resend.

Supported Email Types:
1. Email Verification (mandatory for signup)
2. Subscription Emails (activated, expiring, expired, upgraded, renewed)
3. Inquiry Emails (buyer confirmation, seller notification, quote sent)
4. Order Emails (placed, payment, tracking, completed)

Architecture:
- All emails are triggered from backend only
- HTML templates are branded (Udyog Connect design)
- Logging for all email success/failure
- Async non-blocking via asyncio.to_thread

Environment Variables:
- RESEND_API_KEY: Your Resend API key (required)
- SENDER_EMAIL: Sender email (default: noreply@udyogconnect.in)
- FRONTEND_URL: Frontend URL for links (default: https://udyogconnect.in)
"""

import os
import asyncio
import logging
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from bson import ObjectId

# Resend SDK
import resend

logger = logging.getLogger(__name__)

# Configuration from environment
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@udyogconnect.in")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://udyogconnect.in")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "admin@udyogconnect.in")

# Token settings
TOKEN_EXPIRY_HOURS = 1  # As per user requirements

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend API key configured")
else:
    logger.warning("RESEND_API_KEY not configured - emails will be in MOCK mode")


# ============================================================================
# EMAIL TEMPLATES - BRANDED UDYOG CONNECT DESIGN
# ============================================================================

def _get_email_wrapper(content: str, title: str = "Udyog Connect") -> str:
    """
    Base email template wrapper with Udyog Connect branding.
    Uses inline CSS for maximum email client compatibility.
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 0; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto;">
        <!-- Header -->
        <tr>
            <td style="background: linear-gradient(135deg, #0B3C5D 0%, #1a5f8a 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: bold;">Udyog Connect</h1>
                <p style="color: #e0e0e0; margin: 10px 0 0 0; font-size: 14px;">India's B2B Industrial Marketplace</p>
            </td>
        </tr>
        
        <!-- Content -->
        <tr>
            <td style="background: #ffffff; padding: 40px 30px;">
                {content}
            </td>
        </tr>
        
        <!-- Footer -->
        <tr>
            <td style="background: #f5f5f5; padding: 20px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="color: #666; font-size: 12px; margin: 0 0 10px 0;">
                    Need help? Contact us at <a href="mailto:{SUPPORT_EMAIL}" style="color: #0B3C5D;">{SUPPORT_EMAIL}</a>
                </p>
                <p style="color: #999; font-size: 11px; margin: 0;">
                    © {datetime.now().year} Udyog Connect. All rights reserved.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def _get_button_html(text: str, url: str, color: str = "#0B3C5D") -> str:
    return f"""
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" align="center" style="margin: 30px auto;">
        <tr>
            <td align="center" bgcolor="{color}" style="border-radius: 6px;">
                <a href="{url}" 
                   target="_blank"
                   style="
                        display: inline-block;
                        padding: 14px 40px;
                        font-size: 16px;
                        font-weight: bold;
                        color: #ffffff;
                        text-decoration: none;
                        border-radius: 6px;
                        background-color: {color};
                   ">
                    {text}
                </a>
            </td>
        </tr>
    </table>
    """


# ============================================================================
# CORE EMAIL SENDING FUNCTION
# ============================================================================

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email via Resend (non-blocking).
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content (wrapped in brand template)
        text_content: Optional plain text fallback
    
    Returns:
        dict with success status and email_id or error
    """
    if not RESEND_API_KEY:
        logger.warning(f"[MOCK EMAIL] Would send to {to_email}: {subject}")
        return {
            "success": True,
            "message": "Email sent (mock mode)",
            "_mock": True,
            "_to": to_email,
            "_subject": subject
        }
    
    params = {
        "from": f"Udyog Connect <{SENDER_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }
    
    if text_content:
        params["text"] = text_content
    
    try:
        # Run sync Resend SDK in thread to keep FastAPI non-blocking
        email_result = await asyncio.to_thread(resend.Emails.send, params)
        
        email_id = email_result.get("id") if isinstance(email_result, dict) else str(email_result)
        logger.info(f"Email sent to {to_email}: {subject} (ID: {email_id})")
        
        return {
            "success": True,
            "message": "Email sent successfully",
            "email_id": email_id
        }
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to send email. Please try again later."
        }


# ============================================================================
# 1. EMAIL VERIFICATION EMAILS
# ============================================================================

class EmailVerificationService:
    """
    Handles email verification flow using Resend.
    
    Flow:
    1. User signs up → generate secure token (hashed before storage)
    2. Send verification email via Resend
    3. User clicks link → verify token → mark verified
    4. Token expires after 1 hour
    """
    
    def __init__(self, db):
        self.db = db
    
    async def generate_verification_token(self, email: str) -> str:
        """
        Generate a secure verification token.
        
        Security:
        - Token is hashed (SHA256) before storing in DB
        - Original token is sent in email
        - 1-hour expiry
        """
        # Generate random token
        token = secrets.token_urlsafe(32)
        
        # Hash for storage (security best practice)
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # Calculate expiry
        expiry = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
        
        # Store hashed token in user document
        await self.db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "verificationToken": hashed_token,
                    "verificationTokenExpiry": expiry,
                    "isEmailVerified": False,
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Generated verification token for {email}")
        return token  # Return unhashed token for email
    
    async def send_verification_email(self, email: str) -> Dict[str, Any]:
        """
        Generate token and send verification email.
        """
        try:
            # Generate token
            token = await self.generate_verification_token(email)
            
            # Build verification link
            verify_link = f"{FRONTEND_URL}/verify-email?token={token}"
            
            # Build email content
            content = f"""
            <h2 style="color: #0B3C5D; margin-top: 0;">Verify Your Email</h2>
            
            <p>Welcome to Udyog Connect!</p>
            
            <p>Please click the button below to verify your email address and activate your account:</p>
            
            {_get_button_html("Verify Email Address", verify_link)}
            
            <p style="color: #666; font-size: 14px;">
                This link will expire in <strong>{TOKEN_EXPIRY_HOURS} hour</strong>.
            </p>
            
            <p style="color: #666; font-size: 14px;">
                If the button doesn't work, copy and paste this link into your browser:
                <br>
                <a href="{verify_link}" style="color: #0B3C5D; word-break: break-all;">{verify_link}</a>
            </p>
            
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
            
            <p style="color: #999; font-size: 12px;">
                If you didn't create an account on Udyog Connect, please ignore this email.
            </p>
            """
            
            html = _get_email_wrapper(content, "Verify Your Email - Udyog Connect")
            
            # Plain text fallback
            text = f"""
Welcome to Udyog Connect!

Please verify your email by clicking the link below:
{verify_link}

This link will expire in {TOKEN_EXPIRY_HOURS} hour.

If you didn't create an account on Udyog Connect, please ignore this email.

Best Regards,
Udyog Connect Team
            """
            
            result = await send_email(
                to_email=email,
                subject="Verify Your Email - Udyog Connect",
                html_content=html,
                text_content=text
            )
            
            if result.get("_mock"):
                # In mock mode, include the link for testing
                result["_verify_link"] = verify_link
                logger.info(f"[MOCK] Verification link for {email}: {verify_link}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {e}")
            return {
                "success": False,
                "error": "Failed to send verification email. Please try again."
            }
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a token and mark user's email as verified.
        """
        if not token:
            return {"success": False, "error": "Invalid verification token"}
        
        # Hash the provided token to match stored hash
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # Find user with this token
        user = await self.db.users.find_one({"verificationToken": hashed_token})
        
        if not user:
            return {
                "success": False,
                "error": "Invalid or expired verification link"
            }
        
        # Check expiry
        expiry = user.get("verificationTokenExpiry")
        if expiry:
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
                    "verificationTokenExpiry": ""
                }
            }
        )
        
        logger.info(f"Email verified for user {user.get('email')}")
        
        return {
            "success": True,
            "message": "Email verified successfully!",
            "redirectUrl": f"{FRONTEND_URL}/login?verified=true"
        }
    
    async def resend_verification(self, email: str) -> Dict[str, Any]:
        """
        Resend verification email to a user.
        """
        user = await self.db.users.find_one({"email": email})
        
        if not user:
            # Security: Don't reveal if user exists
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


# ============================================================================
# 2. SUBSCRIPTION EMAILS
# ============================================================================

class SubscriptionEmailService:
    """
    Handles all subscription-related emails.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def send_subscription_activated(
        self,
        to_email: str,
        plan_name: str,
        expiry_date: datetime,
        business_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send subscription activated email.
        """
        expiry_str = expiry_date.strftime("%B %d, %Y") if expiry_date else "N/A"
        dashboard_link = f"{FRONTEND_URL}/seller/subscription"
        
        content = f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Subscription Activated!</h2>
        
        <p>Dear {business_name or 'Seller'},</p>
        
        <p>Great news! Your <strong>{plan_name.upper()}</strong> subscription has been activated.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #f9f9f9;"><strong>Plan</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{plan_name.capitalize()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #f9f9f9;"><strong>Valid Until</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{expiry_str}</td>
            </tr>
        </table>
        
        {_get_button_html("View Subscription", dashboard_link, "#28a745")}
        
        <p>Thank you for choosing Udyog Connect!</p>
        """
        
        html = _get_email_wrapper(content, "Subscription Activated - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Subscription Activated: {plan_name.capitalize()} Plan - Udyog Connect",
            html_content=html
        )
    
    async def send_subscription_expiring_soon(
        self,
        to_email: str,
        plan_name: str,
        expiry_date: datetime,
        days_remaining: int,
        business_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send subscription expiring soon email (3 days before expiry).
        """
        expiry_str = expiry_date.strftime("%B %d, %Y")
        renewal_link = f"{FRONTEND_URL}/seller/subscription?action=renew"
        
        content = f"""
        <h2 style="color: #f59e0b; margin-top: 0;">Subscription Expiring Soon</h2>
        
        <p>Dear {business_name or 'Seller'},</p>
        
        <p>Your <strong>{plan_name.upper()}</strong> subscription will expire in <strong>{days_remaining} days</strong>.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #fef3c7;"><strong>Plan</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{plan_name.capitalize()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #fef3c7;"><strong>Expires On</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{expiry_str}</td>
            </tr>
        </table>
        
        <p>Renew now to continue enjoying unlimited leads and premium features.</p>
        
        {_get_button_html("Renew Subscription", renewal_link, "#f59e0b")}
        
        <p style="color: #666; font-size: 14px;">
            After expiry, you'll be moved to the Free plan with limited features.
        </p>
        """
        
        html = _get_email_wrapper(content, "Subscription Expiring Soon - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Action Required: Your Subscription Expires in {days_remaining} Days",
            html_content=html
        )
    
    async def send_subscription_expired(
        self,
        to_email: str,
        plan_name: str,
        business_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send subscription expired email.
        """
        renewal_link = f"{FRONTEND_URL}/seller/subscription?action=renew"
        
        content = f"""
        <h2 style="color: #ef4444; margin-top: 0;">Subscription Expired</h2>
        
        <p>Dear {business_name or 'Seller'},</p>
        
        <p>Your <strong>{plan_name.upper()}</strong> subscription has expired.</p>
        
        <p>You've been moved to the <strong>Free Plan</strong> with the following limitations:</p>
        
        <ul style="color: #666;">
            <li>5 leads per month</li>
            <li>Basic listing features</li>
            <li>No verified seller badge</li>
        </ul>
        
        <p>Renew your subscription to regain unlimited access!</p>
        
        {_get_button_html("Renew Now", renewal_link, "#ef4444")}
        
        <p style="color: #666; font-size: 14px;">
            Need help? Contact us at <a href="mailto:{SUPPORT_EMAIL}" style="color: #0B3C5D;">{SUPPORT_EMAIL}</a>
        </p>
        """
        
        html = _get_email_wrapper(content, "Subscription Expired - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject="Your Subscription Has Expired - Udyog Connect",
            html_content=html
        )
    
    async def send_plan_upgraded(
        self,
        to_email: str,
        old_plan: str,
        new_plan: str,
        expiry_date: datetime,
        business_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send plan upgraded email.
        """
        expiry_str = expiry_date.strftime("%B %d, %Y") if expiry_date else "N/A"
        dashboard_link = f"{FRONTEND_URL}/seller/subscription"
        
        content = f"""
        <h2 style="color: #28a745; margin-top: 0;">Plan Upgraded Successfully!</h2>
        
        <p>Dear {business_name or 'Seller'},</p>
        
        <p>Congratulations! Your subscription has been upgraded.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #f9f9f9;"><strong>Previous Plan</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{old_plan.capitalize()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #d1fae5;"><strong>New Plan</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #d1fae5; color: #28a745; font-weight: bold;">{new_plan.capitalize()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #f9f9f9;"><strong>Valid Until</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{expiry_str}</td>
            </tr>
        </table>
        
        {_get_button_html("View Dashboard", dashboard_link, "#28a745")}
        
        <p>Thank you for upgrading!</p>
        """
        
        html = _get_email_wrapper(content, "Plan Upgraded - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Plan Upgraded to {new_plan.capitalize()} - Udyog Connect",
            html_content=html
        )
    
    async def send_plan_renewed(
        self,
        to_email: str,
        plan_name: str,
        new_expiry_date: datetime,
        business_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send plan renewed email.
        """
        expiry_str = new_expiry_date.strftime("%B %d, %Y")
        dashboard_link = f"{FRONTEND_URL}/seller/subscription"
        
        content = f"""
        <h2 style="color: #28a745; margin-top: 0;">Subscription Renewed!</h2>
        
        <p>Dear {business_name or 'Seller'},</p>
        
        <p>Your <strong>{plan_name.upper()}</strong> subscription has been successfully renewed.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #f9f9f9;"><strong>Plan</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0;">{plan_name.capitalize()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e0e0e0; background: #f9f9f9;"><strong>New Expiry Date</strong></td>
                <td style="padding: 10px; border: 1px solid #e0e0e0; color: #28a745; font-weight: bold;">{expiry_str}</td>
            </tr>
        </table>
        
        {_get_button_html("View Dashboard", dashboard_link, "#28a745")}
        
        <p>Thank you for continuing with Udyog Connect!</p>
        """
        
        html = _get_email_wrapper(content, "Subscription Renewed - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject="Subscription Renewed Successfully - Udyog Connect",
            html_content=html
        )


# ============================================================================
# 3. INQUIRY EMAILS
# ============================================================================

class InquiryEmailService:
    """
    Handles all inquiry-related emails.
    Different formats for buyers and sellers.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def send_buyer_inquiry_confirmation(
        self,
        to_email: str,
        buyer_name: str,
        product_name: str,
        seller_name: str,
        quantity: int,
        inquiry_id: str
    ) -> Dict[str, Any]:
        """
        Send confirmation email to buyer after inquiry submission.
        """
        inquiries_link = f"{FRONTEND_URL}/buyer/inquiries"
        
        content = f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Inquiry Sent Successfully!</h2>
        
        <p>Dear {buyer_name},</p>
        
        <p>Your inquiry has been sent to the seller. They will respond shortly.</p>
        
        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #0B3C5D; margin-top: 0;">Inquiry Details</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Product:</strong></td>
                    <td style="padding: 8px 0;">{product_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Seller:</strong></td>
                    <td style="padding: 8px 0;">{seller_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Quantity:</strong></td>
                    <td style="padding: 8px 0;">{quantity:,} units</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Inquiry ID:</strong></td>
                    <td style="padding: 8px 0; font-family: monospace;">{inquiry_id}</td>
                </tr>
            </table>
        </div>
        
        <p style="color: #666;">The seller will review your inquiry and respond with a quote.</p>
        
        {_get_button_html("Track Your Inquiries", inquiries_link)}
        """
        
        html = _get_email_wrapper(content, "Inquiry Sent - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Inquiry Sent: {product_name} - Udyog Connect",
            html_content=html
        )
    
    async def send_seller_new_inquiry_notification(
        self,
        to_email: str,
        seller_name: str,
        buyer_name: str,
        buyer_company: Optional[str],
        product_name: str,
        quantity: int,
        inquiry_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send new inquiry notification to seller.
        """
        dashboard_link = f"{FRONTEND_URL}/seller/inquiries"
        
        message_html = ""
        if message:
            message_html = f"""
            <tr>
                <td style="padding: 8px 0; color: #666; vertical-align: top;"><strong>Message:</strong></td>
                <td style="padding: 8px 0;">{message}</td>
            </tr>
            """
        
        content = f"""
        <h2 style="color: #28a745; margin-top: 0;">New Inquiry Received!</h2>
        
        <p>Dear {seller_name},</p>
        
        <p>You have received a new inquiry for your product.</p>
        
        <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
            <h3 style="color: #28a745; margin-top: 0;">Inquiry Details</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Buyer:</strong></td>
                    <td style="padding: 8px 0;">{buyer_name}{f' ({buyer_company})' if buyer_company else ''}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Product:</strong></td>
                    <td style="padding: 8px 0;">{product_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Quantity:</strong></td>
                    <td style="padding: 8px 0; font-weight: bold; color: #0B3C5D;">{quantity:,} units</td>
                </tr>
                {message_html}
            </table>
        </div>
        
        <p><strong>Respond quickly to increase your chances of closing this deal!</strong></p>
        
        {_get_button_html("View & Respond", dashboard_link, "#28a745")}
        """
        
        html = _get_email_wrapper(content, "New Inquiry - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"New Inquiry: {product_name} ({quantity:,} units)",
            html_content=html
        )
    
    async def send_buyer_quote_received(
        self,
        to_email: str,
        buyer_name: str,
        seller_name: str,
        product_name: str,
        quoted_price: float,
        moq: int,
        lead_time_days: int,
        validity_days: int,
        quote_id: str
    ) -> Dict[str, Any]:
        """
        Send quote received notification to buyer.
        """
        quote_link = f"{FRONTEND_URL}/buyer/quotes/{quote_id}"
        
        content = f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Quote Received!</h2>
        
        <p>Dear {buyer_name},</p>
        
        <p><strong>{seller_name}</strong> has responded to your inquiry with a quote.</p>
        
        <div style="background: #eff6ff; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #0B3C5D;">
            <h3 style="color: #0B3C5D; margin-top: 0;">Quote Details</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Product:</strong></td>
                    <td style="padding: 8px 0;">{product_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Price:</strong></td>
                    <td style="padding: 8px 0; font-size: 18px; font-weight: bold; color: #28a745;">₹{quoted_price:,.2f}/unit</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>MOQ:</strong></td>
                    <td style="padding: 8px 0;">{moq:,} units</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Lead Time:</strong></td>
                    <td style="padding: 8px 0;">{lead_time_days} days</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Valid For:</strong></td>
                    <td style="padding: 8px 0;">{validity_days} days</td>
                </tr>
            </table>
        </div>
        
        {_get_button_html("View Quote", quote_link)}
        
        <p style="color: #666; font-size: 14px;">
            This quote is valid for {validity_days} days. Review and respond to proceed with the order.
        </p>
        """
        
        html = _get_email_wrapper(content, "Quote Received - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Quote Received: {product_name} - ₹{quoted_price:,.2f}/unit",
            html_content=html
        )


# ============================================================================
# 4. ORDER EMAILS
# ============================================================================

class OrderEmailService:
    """
    Handles all order-related emails.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def send_order_placed_confirmation(
        self,
        to_email: str,
        buyer_name: str,
        order_id: str,
        product_name: str,
        quantity: int,
        total_amount: float,
        seller_name: str
    ) -> Dict[str, Any]:
        """
        Send order placed confirmation to buyer.
        """
        orders_link = f"{FRONTEND_URL}/buyer/orders/{order_id}"
        
        content = f"""
        <h2 style="color: #28a745; margin-top: 0;">Order Placed Successfully!</h2>
        
        <p>Dear {buyer_name},</p>
        
        <p>Your order has been placed successfully.</p>
        
        <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #28a745; margin-top: 0;">Order Summary</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Order ID:</strong></td>
                    <td style="padding: 8px 0; font-family: monospace;">{order_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Product:</strong></td>
                    <td style="padding: 8px 0;">{product_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Quantity:</strong></td>
                    <td style="padding: 8px 0;">{quantity:,} units</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Seller:</strong></td>
                    <td style="padding: 8px 0;">{seller_name}</td>
                </tr>
                <tr style="border-top: 2px solid #28a745;">
                    <td style="padding: 12px 0; color: #666;"><strong>Total Amount:</strong></td>
                    <td style="padding: 12px 0; font-size: 20px; font-weight: bold; color: #28a745;">₹{total_amount:,.2f}</td>
                </tr>
            </table>
        </div>
        
        {_get_button_html("View Order", orders_link, "#28a745")}
        """
        
        html = _get_email_wrapper(content, "Order Placed - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Order Confirmed: {order_id} - Udyog Connect",
            html_content=html
        )
    
    async def send_payment_successful(
        self,
        to_email: str,
        buyer_name: str,
        order_id: str,
        amount: float,
        payment_method: str = "Online"
    ) -> Dict[str, Any]:
        """
        Send payment successful email.
        """
        orders_link = f"{FRONTEND_URL}/buyer/orders/{order_id}"
        
        content = f"""
        <h2 style="color: #28a745; margin-top: 0;">Payment Successful!</h2>
        
        <p>Dear {buyer_name},</p>
        
        <p>Your payment has been processed successfully.</p>
        
        <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 48px; color: #28a745;">✓</div>
            <p style="font-size: 24px; font-weight: bold; color: #28a745; margin: 10px 0;">₹{amount:,.2f}</p>
            <p style="color: #666; margin: 0;">Payment Method: {payment_method}</p>
            <p style="color: #666; margin: 5px 0 0 0;">Order ID: {order_id}</p>
        </div>
        
        {_get_button_html("View Order", orders_link, "#28a745")}
        """
        
        html = _get_email_wrapper(content, "Payment Successful - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Payment Confirmed: ₹{amount:,.2f} - Order {order_id}",
            html_content=html
        )
    
    async def send_tracking_link(
        self,
        to_email: str,
        buyer_name: str,
        order_id: str,
        product_name: str,
        tracking_number: str,
        courier_name: str,
        tracking_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send tracking link to buyer.
        """
        orders_link = f"{FRONTEND_URL}/buyer/orders/{order_id}"
        
        tracking_button = ""
        if tracking_url:
            tracking_button = _get_button_html("Track Shipment", tracking_url, "#0B3C5D")
        
        content = f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Your Order Has Been Shipped!</h2>
        
        <p>Dear {buyer_name},</p>
        
        <p>Great news! Your order is on its way.</p>
        
        <div style="background: #eff6ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #0B3C5D; margin-top: 0;">Shipping Details</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Order ID:</strong></td>
                    <td style="padding: 8px 0;">{order_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Product:</strong></td>
                    <td style="padding: 8px 0;">{product_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Courier:</strong></td>
                    <td style="padding: 8px 0;">{courier_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;"><strong>Tracking Number:</strong></td>
                    <td style="padding: 8px 0; font-family: monospace; font-weight: bold;">{tracking_number}</td>
                </tr>
            </table>
        </div>
        
        {tracking_button}
        
        {_get_button_html("View Order Details", orders_link, "#6b7280")}
        """
        
        html = _get_email_wrapper(content, "Order Shipped - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Order Shipped: {product_name} - Track Your Delivery",
            html_content=html
        )
    
    async def send_order_completed(
        self,
        to_email: str,
        buyer_name: str,
        order_id: str,
        product_name: str,
        seller_name: str
    ) -> Dict[str, Any]:
        """
        Send order completed email.
        """
        review_link = f"{FRONTEND_URL}/buyer/orders/{order_id}/review"
        
        content = f"""
        <h2 style="color: #28a745; margin-top: 0;">Order Completed!</h2>
        
        <p>Dear {buyer_name},</p>
        
        <p>Your order has been delivered successfully.</p>
        
        <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 48px;">📦 ✓</div>
            <h3 style="color: #28a745; margin: 10px 0;">{product_name}</h3>
            <p style="color: #666; margin: 0;">Sold by: {seller_name}</p>
            <p style="color: #666; margin: 5px 0 0 0;">Order ID: {order_id}</p>
        </div>
        
        <p>We hope you're satisfied with your purchase!</p>
        
        {_get_button_html("Leave a Review", review_link, "#f59e0b")}
        
        <p style="color: #666; font-size: 14px;">
            Your feedback helps other buyers make informed decisions.
        </p>
        """
        
        html = _get_email_wrapper(content, "Order Completed - Udyog Connect")
        
        return await send_email(
            to_email=to_email,
            subject=f"Order Delivered: {product_name} - Leave a Review",
            html_content=html
        )


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def get_email_verification_service(db) -> EmailVerificationService:
    """Get email verification service instance."""
    return EmailVerificationService(db)


def get_subscription_email_service(db) -> SubscriptionEmailService:
    """Get subscription email service instance."""
    return SubscriptionEmailService(db)


def get_inquiry_email_service(db) -> InquiryEmailService:
    """Get inquiry email service instance."""
    return InquiryEmailService(db)


def get_order_email_service(db) -> OrderEmailService:
    """Get order email service instance."""
    return OrderEmailService(db)


# ============================================================================
# 5. CONTACT FORM EMAIL
# ============================================================================

async def send_contact_form_email(
    name: str,
    email: str,
    subject: str,
    message: str
) -> Dict[str, Any]:
    """
    Send contact form submission to admin.
    
    Args:
        name: Sender's name
        email: Sender's email
        subject: Subject category (general, support, seller, buyer, feedback)
        message: Message content
    
    Returns:
        dict with success status
    """
    # Map subject values to readable labels
    subject_labels = {
        "general": "General Inquiry",
        "support": "Technical Support",
        "seller": "Seller Support",
        "buyer": "Buyer Support",
        "feedback": "Feedback"
    }
    subject_label = subject_labels.get(subject, subject)
    
    # Build email content for admin
    content = f"""
    <h2 style="color: #0B3C5D; margin-top: 0;">New Contact Form Submission</h2>
    
    <p>You have received a new message from the contact form on UdyogConnect.</p>
    
    <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0B3C5D;">
        <table style="width: 100%;">
            <tr>
                <td style="padding: 8px 0; color: #666; width: 120px;"><strong>From:</strong></td>
                <td style="padding: 8px 0;">{name}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #666;"><strong>Email:</strong></td>
                <td style="padding: 8px 0;"><a href="mailto:{email}" style="color: #0B3C5D;">{email}</a></td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #666;"><strong>Subject:</strong></td>
                <td style="padding: 8px 0;">{subject_label}</td>
            </tr>
        </table>
    </div>
    
    <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3 style="color: #333; margin-top: 0;">Message:</h3>
        <p style="color: #333; white-space: pre-wrap;">{message}</p>
    </div>
    
    <p style="color: #666; font-size: 14px;">
        Reply directly to this email to respond to {name}.
    </p>
    """
    
    html = _get_email_wrapper(content, f"Contact Form: {subject_label}")
    
    # Send to admin email
    admin_email = SUPPORT_EMAIL  # admin@udyogconnect.in
    
    result = await send_email(
        to_email=admin_email,
        subject=f"[Contact Form] {subject_label} from {name}",
        html_content=html
    )
    
    # Also send confirmation to the sender
    if result.get("success"):
        await _send_contact_confirmation(name, email, subject_label)
    
    return result


async def _send_contact_confirmation(name: str, email: str, subject: str) -> None:
    """Send confirmation email to the person who submitted the contact form."""
    content = f"""
    <h2 style="color: #0B3C5D; margin-top: 0;">We've Received Your Message</h2>
    
    <p>Dear {name},</p>
    
    <p>Thank you for contacting UdyogConnect. We have received your message regarding <strong>{subject}</strong>.</p>
    
    <p>Our team will review your inquiry and respond within <strong>24-48 hours</strong>.</p>
    
    <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
        <div style="font-size: 36px;">✓</div>
        <p style="color: #28a745; font-weight: bold; margin: 10px 0;">Message Received</p>
    </div>
    
    <p style="color: #666;">In the meantime, you can:</p>
    <ul style="color: #666;">
        <li>Browse our <a href="{FRONTEND_URL}/products" style="color: #0B3C5D;">product catalog</a></li>
        <li>Check our <a href="{FRONTEND_URL}/faq" style="color: #0B3C5D;">FAQ section</a></li>
        <li>Call us at <strong>+91 73878 21042</strong> for urgent queries</li>
    </ul>
    
    <p>Best Regards,<br>UdyogConnect Support Team</p>
    """
    
    html = _get_email_wrapper(content, "Message Received - UdyogConnect")
    
    try:
        await send_email(
            to_email=email,
            subject="We've Received Your Message - UdyogConnect",
            html_content=html
        )
    except Exception as e:
        logger.warning(f"Failed to send contact confirmation to {email}: {e}")



# ============================================================================
# 7. PASSWORD RESET OTP SERVICE
# ============================================================================

class PasswordResetOTPService:
    """
    OTP-based password reset service.
    
    Flow:
    1. User requests OTP via email
    2. 6-digit OTP sent to email (valid for 10 minutes)
    3. User enters OTP + new password
    4. Password changed in Firebase
    
    Security:
    - OTPs expire in 10 minutes
    - Max 5 attempts per OTP
    - Rate limiting: 3 OTPs per email per hour
    """
    
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 5
    RATE_LIMIT_PER_HOUR = 3
    
    def __init__(self, db):
        self.db = db
        self.collection = db.password_reset_otps
    
    async def generate_otp(self, email: str) -> Dict[str, Any]:
        """
        Generate and send 6-digit OTP for password reset.
        
        Args:
            email: User's email address
            
        Returns:
            {success: bool, message: str, expires_at: datetime}
        """
        email = email.lower().strip()
        
        # Check rate limiting
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_otps = await self.collection.count_documents({
            "email": email,
            "createdAt": {"$gte": one_hour_ago}
        })
        
        if recent_otps >= self.RATE_LIMIT_PER_HOUR:
            return {
                "success": False,
                "message": "Too many OTP requests. Please try again after an hour."
            }
        
        # Check if user exists
        user = await self.db.users.find_one({"email": email})
        if not user:
            # Don't reveal if email exists or not (security)
            return {
                "success": True,
                "message": "If this email is registered, you will receive an OTP shortly."
            }
        
        # Generate 6-digit OTP
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        # Invalidate any existing OTPs for this email
        await self.collection.update_many(
            {"email": email, "isUsed": False},
            {"$set": {"isUsed": True}}
        )
        
        # Store OTP
        await self.collection.insert_one({
            "email": email,
            "userId": str(user["_id"]),
            "otpHash": otp_hash,
            "attempts": 0,
            "isUsed": False,
            "expiresAt": expires_at,
            "createdAt": datetime.now(timezone.utc)
        })
        
        # Send OTP email
        email_result = await self._send_otp_email(email, otp, user.get("profile", {}).get("name", "User"))
        
        if email_result.get("success"):
            return {
                "success": True,
                "message": "OTP sent to your email. Valid for 10 minutes.",
                "expires_at": expires_at.isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Failed to send OTP. Please try again."
            }
    
    async def verify_otp(self, email: str, otp: str) -> Dict[str, Any]:
        """
        Verify OTP for password reset.
        
        Args:
            email: User's email address
            otp: 6-digit OTP entered by user
            
        Returns:
            {success: bool, message: str, reset_token: str (if success)}
        """
        email = email.lower().strip()
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        
        # Find valid OTP
        otp_record = await self.collection.find_one({
            "email": email,
            "isUsed": False,
            "expiresAt": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not otp_record:
            return {
                "success": False,
                "message": "Invalid or expired OTP. Please request a new one."
            }
        
        # Check attempts
        if otp_record["attempts"] >= self.MAX_ATTEMPTS:
            await self.collection.update_one(
                {"_id": otp_record["_id"]},
                {"$set": {"isUsed": True}}
            )
            return {
                "success": False,
                "message": "Too many failed attempts. Please request a new OTP."
            }
        
        # Verify OTP hash
        if otp_record["otpHash"] != otp_hash:
            await self.collection.update_one(
                {"_id": otp_record["_id"]},
                {"$inc": {"attempts": 1}}
            )
            remaining = self.MAX_ATTEMPTS - otp_record["attempts"] - 1
            return {
                "success": False,
                "message": f"Invalid OTP. {remaining} attempts remaining."
            }
        
        # OTP is valid - generate reset token
        reset_token = secrets.token_urlsafe(32)
        reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        
        # Mark OTP as used and store reset token
        await self.collection.update_one(
            {"_id": otp_record["_id"]},
            {"$set": {
                "isUsed": True,
                "verifiedAt": datetime.now(timezone.utc),
                "resetTokenHash": reset_token_hash,
                "resetTokenExpiresAt": datetime.now(timezone.utc) + timedelta(minutes=15)
            }}
        )
        
        return {
            "success": True,
            "message": "OTP verified successfully.",
            "reset_token": reset_token
        }
    
    async def _send_otp_email(self, email: str, otp: str, name: str) -> Dict[str, Any]:
        """Send OTP email with branded template."""
        content = f"""
        <h2 style="color: #0B3C5D; margin-top: 0;">Password Reset Request</h2>
        
        <p>Dear {name},</p>
        
        <p>We received a request to reset your password for your UdyogConnect account.</p>
        
        <p>Your One-Time Password (OTP) is:</p>
        
        <div style="background: linear-gradient(135deg, #0B3C5D 0%, #1a5f8a 100%); padding: 25px; border-radius: 10px; margin: 25px 0; text-align: center;">
            <span style="font-size: 36px; font-weight: bold; color: #ffffff; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp}</span>
        </div>
        
        <div style="background: #fff8e1; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <p style="margin: 0; color: #856404;">
                <strong>⏱️ This OTP is valid for 10 minutes.</strong><br>
                Do not share this code with anyone.
            </p>
        </div>
        
        <p style="color: #666;">If you didn't request this password reset, please ignore this email or contact support if you have concerns.</p>
        
        <p>Best Regards,<br>UdyogConnect Security Team</p>
        """
        
        html = _get_email_wrapper(content, "Password Reset OTP - UdyogConnect")
        
        return await send_email(
            to_email=email,
            subject="Your Password Reset OTP - UdyogConnect",
            html_content=html
        )


# ============================================================================
# CLEANUP FUNCTION FOR EXPIRED OTPS
# ============================================================================

async def cleanup_expired_otps(db) -> int:
    """
    Delete expired OTPs from database.
    Should be run periodically (e.g., daily via cron).
    
    Returns:
        Number of deleted records
    """
    result = await db.password_reset_otps.delete_many({
        "expiresAt": {"$lt": datetime.now(timezone.utc) - timedelta(days=1)}
    })
    logger.info(f"Cleaned up {result.deleted_count} expired OTPs")
    return result.deleted_count
