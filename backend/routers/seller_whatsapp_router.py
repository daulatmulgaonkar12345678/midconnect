"""
Seller WhatsApp Contacts Router
===============================

Manages multiple WhatsApp numbers for sellers with primary contact selection.
This is an extension layer that does NOT modify existing inquiry system.

Features:
- Add/edit/delete WhatsApp contacts
- Set primary contact (only one allowed per seller)
- Auto WhatsApp connect setting
- Phone number validation (E.164 format)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from bson import ObjectId
from datetime import datetime, timezone
import re
import logging

logger = logging.getLogger(__name__)


# ==================== MODELS ====================

class WhatsAppContactCreate(BaseModel):
    """Create a new WhatsApp contact"""
    phoneNumber: str = Field(..., description="Phone number in E.164 format (e.g., +919876543210)")
    label: Optional[str] = Field(None, max_length=50, description="Contact label (e.g., Sales, Support)")
    isPrimary: bool = Field(False, description="Set as primary contact")
    
    @validator('phoneNumber')
    def validate_phone(cls, v):
        # Remove spaces and special characters except +
        cleaned = re.sub(r'[^+\d]', '', v)
        
        # Validate E.164 format: + followed by 7-15 digits
        if not re.match(r'^\+\d{7,15}$', cleaned):
            raise ValueError('Phone number must be in E.164 format (e.g., +919876543210)')
        
        return cleaned
    
    @validator('label')
    def clean_label(cls, v):
        if v:
            return v.strip()
        return v


class WhatsAppContactUpdate(BaseModel):
    """Update an existing WhatsApp contact"""
    phoneNumber: Optional[str] = Field(None, description="Phone number in E.164 format")
    label: Optional[str] = Field(None, max_length=50)
    isPrimary: Optional[bool] = None
    
    @validator('phoneNumber')
    def validate_phone(cls, v):
        if v is None:
            return v
        # Remove spaces and special characters except +
        cleaned = re.sub(r'[^+\d]', '', v)
        
        # Validate E.164 format
        if not re.match(r'^\+\d{7,15}$', cleaned):
            raise ValueError('Phone number must be in E.164 format (e.g., +919876543210)')
        
        return cleaned


class WhatsAppSettingsUpdate(BaseModel):
    """Update seller WhatsApp settings"""
    autoWhatsappConnect: bool = Field(..., description="Auto connect buyer via WhatsApp after inquiry")


class WhatsAppContact(BaseModel):
    """WhatsApp contact response model"""
    id: str
    phoneNumber: str
    label: Optional[str]
    isPrimary: bool
    createdAt: datetime


# ==================== ROUTER FACTORY ====================

def create_seller_whatsapp_router(db, require_verified_seller):
    """
    Factory function to create seller WhatsApp router.
    
    Args:
        db: MongoDB database instance
        require_verified_seller: Dependency for seller authentication
    """
    router = APIRouter(prefix="/seller/whatsapp", tags=["Seller WhatsApp"])
    
    # ==================== GET CONTACTS ====================
    
    @router.get("/contacts")
    async def get_whatsapp_contacts(
        user: dict = Depends(require_verified_seller)
    ):
        """
        Get all WhatsApp contacts for the current seller.
        
        Returns list of contacts with primary contact first.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        contacts = await db.sellerWhatsappContacts.find(
            {"sellerId": seller_id}
        ).sort([("isPrimary", -1), ("createdAt", 1)]).to_list(100)
        
        return {
            "contacts": [
                {
                    "id": str(c["_id"]),
                    "phoneNumber": c.get("phoneNumber"),
                    "label": c.get("label"),
                    "isPrimary": c.get("isPrimary", False),
                    "createdAt": c.get("createdAt").isoformat() if c.get("createdAt") else None
                }
                for c in contacts
            ]
        }
    
    # ==================== ADD CONTACT ====================
    
    @router.post("/contacts")
    async def add_whatsapp_contact(
        contact: WhatsAppContactCreate,
        user: dict = Depends(require_verified_seller)
    ):
        """
        Add a new WhatsApp contact.
        
        If isPrimary=True, all other contacts will be set to isPrimary=False.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        # Check if phone number already exists for this seller
        existing = await db.sellerWhatsappContacts.find_one({
            "sellerId": seller_id,
            "phoneNumber": contact.phoneNumber
        })
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This phone number is already added"
            )
        
        now = datetime.now(timezone.utc)
        
        # If this is the first contact, make it primary automatically
        contact_count = await db.sellerWhatsappContacts.count_documents({"sellerId": seller_id})
        is_primary = contact.isPrimary or contact_count == 0
        
        # If setting as primary, unset other primaries
        if is_primary:
            await db.sellerWhatsappContacts.update_many(
                {"sellerId": seller_id, "isPrimary": True},
                {"$set": {"isPrimary": False}}
            )
        
        contact_doc = {
            "_id": ObjectId(),
            "sellerId": seller_id,
            "phoneNumber": contact.phoneNumber,
            "label": contact.label,
            "isPrimary": is_primary,
            "createdAt": now,
            "updatedAt": now
        }
        
        await db.sellerWhatsappContacts.insert_one(contact_doc)
        
        logger.info(f"WhatsApp contact added: seller={str(seller_id)}, phone={contact.phoneNumber[:6]}...")
        
        return {
            "success": True,
            "message": "WhatsApp contact added successfully",
            "contact": {
                "id": str(contact_doc["_id"]),
                "phoneNumber": contact_doc["phoneNumber"],
                "label": contact_doc["label"],
                "isPrimary": contact_doc["isPrimary"],
                "createdAt": contact_doc["createdAt"].isoformat()
            }
        }
    
    # ==================== UPDATE CONTACT ====================
    
    @router.patch("/contacts/{contact_id}")
    async def update_whatsapp_contact(
        contact_id: str,
        contact: WhatsAppContactUpdate,
        user: dict = Depends(require_verified_seller)
    ):
        """
        Update an existing WhatsApp contact.
        
        If isPrimary=True, all other contacts will be set to isPrimary=False.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        try:
            contact_oid = ObjectId(contact_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid contact ID")
        
        # Verify contact belongs to seller
        existing = await db.sellerWhatsappContacts.find_one({
            "_id": contact_oid,
            "sellerId": seller_id
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Build update fields
        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        
        if contact.phoneNumber is not None:
            # Check for duplicate phone number
            duplicate = await db.sellerWhatsappContacts.find_one({
                "sellerId": seller_id,
                "phoneNumber": contact.phoneNumber,
                "_id": {"$ne": contact_oid}
            })
            if duplicate:
                raise HTTPException(status_code=400, detail="This phone number is already added")
            update_fields["phoneNumber"] = contact.phoneNumber
        
        if contact.label is not None:
            update_fields["label"] = contact.label
        
        if contact.isPrimary is not None:
            # If setting as primary, unset other primaries first
            if contact.isPrimary:
                await db.sellerWhatsappContacts.update_many(
                    {"sellerId": seller_id, "isPrimary": True},
                    {"$set": {"isPrimary": False}}
                )
            update_fields["isPrimary"] = contact.isPrimary
        
        await db.sellerWhatsappContacts.update_one(
            {"_id": contact_oid},
            {"$set": update_fields}
        )
        
        # Get updated contact
        updated = await db.sellerWhatsappContacts.find_one({"_id": contact_oid})
        
        return {
            "success": True,
            "message": "Contact updated successfully",
            "contact": {
                "id": str(updated["_id"]),
                "phoneNumber": updated.get("phoneNumber"),
                "label": updated.get("label"),
                "isPrimary": updated.get("isPrimary", False),
                "createdAt": updated.get("createdAt").isoformat() if updated.get("createdAt") else None
            }
        }
    
    # ==================== DELETE CONTACT ====================
    
    @router.delete("/contacts/{contact_id}")
    async def delete_whatsapp_contact(
        contact_id: str,
        user: dict = Depends(require_verified_seller)
    ):
        """
        Delete a WhatsApp contact.
        
        If deleting the primary contact and other contacts exist,
        the oldest contact becomes the new primary.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        try:
            contact_oid = ObjectId(contact_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid contact ID")
        
        # Verify contact belongs to seller
        existing = await db.sellerWhatsappContacts.find_one({
            "_id": contact_oid,
            "sellerId": seller_id
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        was_primary = existing.get("isPrimary", False)
        
        # Delete the contact
        await db.sellerWhatsappContacts.delete_one({"_id": contact_oid})
        
        # If deleted contact was primary, set the oldest remaining contact as primary
        if was_primary:
            oldest_contact = await db.sellerWhatsappContacts.find_one(
                {"sellerId": seller_id},
                sort=[("createdAt", 1)]
            )
            if oldest_contact:
                await db.sellerWhatsappContacts.update_one(
                    {"_id": oldest_contact["_id"]},
                    {"$set": {"isPrimary": True}}
                )
        
        logger.info(f"WhatsApp contact deleted: seller={str(seller_id)}, contact={contact_id}")
        
        return {
            "success": True,
            "message": "Contact deleted successfully"
        }
    
    # ==================== SET PRIMARY ====================
    
    @router.post("/contacts/{contact_id}/set-primary")
    async def set_primary_contact(
        contact_id: str,
        user: dict = Depends(require_verified_seller)
    ):
        """
        Set a contact as the primary WhatsApp contact.
        
        Only one contact can be primary per seller.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        try:
            contact_oid = ObjectId(contact_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid contact ID")
        
        # Verify contact belongs to seller
        existing = await db.sellerWhatsappContacts.find_one({
            "_id": contact_oid,
            "sellerId": seller_id
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Unset all other primaries
        await db.sellerWhatsappContacts.update_many(
            {"sellerId": seller_id, "isPrimary": True},
            {"$set": {"isPrimary": False}}
        )
        
        # Set this contact as primary
        await db.sellerWhatsappContacts.update_one(
            {"_id": contact_oid},
            {"$set": {"isPrimary": True, "updatedAt": datetime.now(timezone.utc)}}
        )
        
        return {
            "success": True,
            "message": "Primary contact updated"
        }
    
    # ==================== GET/UPDATE SETTINGS ====================
    
    @router.get("/settings")
    async def get_whatsapp_settings(
        user: dict = Depends(require_verified_seller)
    ):
        """
        Get seller's WhatsApp settings.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        # Get settings from seller's user document or dedicated settings collection
        seller = await db.users.find_one({"_id": seller_id})
        
        # Default to enabled if not set
        auto_connect = seller.get("whatsappSettings", {}).get("autoWhatsappConnect", True)
        
        # Get primary contact
        primary_contact = await db.sellerWhatsappContacts.find_one({
            "sellerId": seller_id,
            "isPrimary": True
        })
        
        return {
            "autoWhatsappConnect": auto_connect,
            "primaryContact": {
                "id": str(primary_contact["_id"]),
                "phoneNumber": primary_contact.get("phoneNumber"),
                "label": primary_contact.get("label")
            } if primary_contact else None
        }
    
    @router.patch("/settings")
    async def update_whatsapp_settings(
        settings: WhatsAppSettingsUpdate,
        user: dict = Depends(require_verified_seller)
    ):
        """
        Update seller's WhatsApp settings.
        """
        seller_id = ObjectId(user["_id"]) if isinstance(user["_id"], str) else user["_id"]
        
        await db.users.update_one(
            {"_id": seller_id},
            {"$set": {
                "whatsappSettings.autoWhatsappConnect": settings.autoWhatsappConnect,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        
        return {
            "success": True,
            "message": "Settings updated successfully",
            "autoWhatsappConnect": settings.autoWhatsappConnect
        }
    
    # ==================== PUBLIC: GET SELLER PRIMARY CONTACT ====================
    
    @router.get("/seller/{seller_id}/primary")
    async def get_seller_primary_contact(
        seller_id: str
    ):
        """
        Get a seller's primary WhatsApp contact (for buyer inquiry flow).
        
        This is a public endpoint used after inquiry submission.
        Returns None if seller has no WhatsApp contacts or auto-connect is disabled.
        """
        try:
            seller_oid = ObjectId(seller_id)
        except:
            return {"contact": None, "autoConnect": False}
        
        # Check seller's auto-connect setting
        seller = await db.users.find_one({"_id": seller_oid})
        if not seller:
            return {"contact": None, "autoConnect": False}
        
        auto_connect = seller.get("whatsappSettings", {}).get("autoWhatsappConnect", True)
        
        if not auto_connect:
            return {"contact": None, "autoConnect": False}
        
        # Get primary contact
        primary_contact = await db.sellerWhatsappContacts.find_one({
            "sellerId": seller_oid,
            "isPrimary": True
        })
        
        if not primary_contact:
            return {"contact": None, "autoConnect": True}
        
        return {
            "contact": {
                "phoneNumber": primary_contact.get("phoneNumber"),
                "label": primary_contact.get("label")
            },
            "autoConnect": True
        }
    
    return router
