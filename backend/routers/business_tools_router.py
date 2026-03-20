"""
Business Tools Router - RBAC, Employees, Buyers, Suppliers
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Body
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
import logging
import firebase_admin
from firebase_admin import auth as firebase_auth

from models.business_tools import (
    RoleCreate, RoleUpdate, RoleResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    BuyerCreate, BuyerUpdate, BuyerResponse,
    SupplierCreate, SupplierUpdate, SupplierResponse,
    InventoryUpdate, InventoryLogCreate, InventoryLogResponse,
    Permission, ALL_PERMISSIONS, AccountType,
    LowStockAlertStatusUpdate
)
from utils.permissions import (
    authenticate_user, resolve_seller_id, check_user_permission,
    require_user_permission, is_platform_admin
)
from utils.gst import INDIAN_STATES, GST_RATES, calculate_gst

logger = logging.getLogger(__name__)


def init_business_tools_router(db, verify_token_func, activity_log_service=None):
    """Initialize the business tools router with database and auth dependencies."""
    
    router = APIRouter(tags=["Business Tools"])
    
    # ===========================================
    # HELPER FUNCTIONS
    # ===========================================
    
    def serialize_doc(doc):
        """Convert MongoDB document to JSON-serializable dict."""
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
    
    async def get_current_user(authorization: str = Header(...)):
        """Get current user from Firebase token."""
        return await authenticate_user(db, verify_token_func, authorization)
    
    async def get_seller_id(user: dict) -> str:
        """Get seller ID for current user (seller or employee)."""
        return resolve_seller_id(user)
    
    async def check_permission(user: dict, permission: str) -> bool:
        """Check if user has a specific permission."""
        return await check_user_permission(db, user, permission)
    
    async def require_permission(user: dict, permission: str):
        """Require a specific permission or raise 403."""
        return await require_user_permission(db, user, permission)
    
    # ===========================================
    # ROLE ENDPOINTS
    # ===========================================
    
    @router.get("/roles")
    async def list_roles(authorization: str = Header(...)):
        """List all roles for seller."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        
        roles = await db.roles.find({
            "sellerId": ObjectId(seller_id)
        }).sort("createdAt", -1).to_list(100)
        
        return {"roles": serialize_doc(roles)}
    
    @router.post("/roles")
    async def create_role(data: RoleCreate, authorization: str = Header(...)):
        """Create a new role. Only seller admin can create roles."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_ROLES.value)
        seller_id = await get_seller_id(user)
        
        # Validate permissions
        invalid_perms = [p for p in data.permissions if p not in ALL_PERMISSIONS]
        if invalid_perms:
            raise HTTPException(status_code=400, detail=f"Invalid permissions: {invalid_perms}")
        
        # Check for duplicate name
        existing = await db.roles.find_one({
            "sellerId": ObjectId(seller_id),
            "name": {"$regex": f"^{data.name}$", "$options": "i"}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Role with this name already exists")
        
        now = datetime.now(timezone.utc)
        role_doc = {
            "sellerId": ObjectId(seller_id),
            "name": data.name,
            "description": data.description,
            "permissions": data.permissions,
            "isActive": True,
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await db.roles.insert_one(role_doc)
        role_doc["_id"] = result.inserted_id
        
        logger.info(f"Role created: {data.name} by seller {seller_id}")
        if activity_log_service:
            await activity_log_service.log(seller_id, str(user["_id"]), "role_created", "roles", str(result.inserted_id), data.name)
        return {"message": "Role created", "role": serialize_doc(role_doc)}
    
    @router.put("/roles/{role_id}")
    async def update_role(role_id: str, data: RoleUpdate, authorization: str = Header(...)):
        """Update a role."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_ROLES.value)
        seller_id = await get_seller_id(user)
        
        try:
            role_oid = ObjectId(role_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid role ID")
        
        # Check role exists and belongs to seller
        role = await db.roles.find_one({
            "_id": role_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        # Validate permissions if provided
        if data.permissions:
            invalid_perms = [p for p in data.permissions if p not in ALL_PERMISSIONS]
            if invalid_perms:
                raise HTTPException(status_code=400, detail=f"Invalid permissions: {invalid_perms}")
        
        # Build update
        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        if data.name is not None:
            update_fields["name"] = data.name
        if data.description is not None:
            update_fields["description"] = data.description
        if data.permissions is not None:
            update_fields["permissions"] = data.permissions
        if data.isActive is not None:
            update_fields["isActive"] = data.isActive
        
        await db.roles.update_one({"_id": role_oid}, {"$set": update_fields})
        
        updated_role = await db.roles.find_one({"_id": role_oid})
        return {"message": "Role updated", "role": serialize_doc(updated_role)}
    
    @router.delete("/roles/{role_id}")
    async def delete_role(role_id: str, authorization: str = Header(...)):
        """Delete a role. Cannot delete if employees are assigned."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_ROLES.value)
        seller_id = await get_seller_id(user)
        
        try:
            role_oid = ObjectId(role_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid role ID")
        
        # Check role exists
        role = await db.roles.find_one({
            "_id": role_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        # Check if any employees use this role
        employee_count = await db.users.count_documents({
            "roleId": role_oid,
            "accountType": "employee"
        })
        if employee_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete role: {employee_count} employees are assigned to this role"
            )
        
        await db.roles.delete_one({"_id": role_oid})
        logger.info(f"Role deleted: {role['name']} by seller {seller_id}")
        
        return {"message": "Role deleted"}
    
    @router.get("/permissions")
    async def list_permissions(authorization: str = Header(...)):
        """List all available permissions."""
        await get_current_user(authorization)
        
        permission_info = {
            "manage_listings": "Create, edit, delete product listings",
            "manage_inventory": "Update stock levels and inventory",
            "view_enquiries": "View buyer enquiries",
            "manage_buyers": "Add, edit, delete buyer records",
            "manage_suppliers": "Add, edit, delete supplier records",
            "create_invoice": "Create and manage invoices",
            "view_reports": "View sales and inventory reports",
            "manage_employees": "Add, edit, deactivate employees",
            "manage_roles": "Create and manage roles & permissions"
        }
        
        return {
            "permissions": [
                {"key": p, "label": p.replace("_", " ").title(), "description": permission_info.get(p, "")}
                for p in ALL_PERMISSIONS
            ]
        }
    
    # ===========================================
    # EMPLOYEE ENDPOINTS
    # ===========================================
    
    @router.get("/employees")
    async def list_employees(authorization: str = Header(...)):
        """List all employees for seller."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_EMPLOYEES.value)
        seller_id = await get_seller_id(user)
        
        employees = await db.users.find({
            "sellerId": ObjectId(seller_id),
            "accountType": "employee"
        }).sort("createdAt", -1).to_list(100)
        
        # Get role names
        role_ids = [e.get("roleId") for e in employees if e.get("roleId")]
        roles = {}
        if role_ids:
            role_docs = await db.roles.find({"_id": {"$in": role_ids}}).to_list(100)
            roles = {str(r["_id"]): r["name"] for r in role_docs}
        
        # Add role names to employees
        for emp in employees:
            role_id = emp.get("roleId")
            emp["roleName"] = roles.get(str(role_id), "No Role") if role_id else "No Role"
        
        return {"employees": serialize_doc(employees)}
    
    @router.post("/employees")
    async def create_employee(data: EmployeeCreate, authorization: str = Header(...)):
        """Create a new employee with Firebase auth."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_EMPLOYEES.value)
        seller_id = await get_seller_id(user)
        
        # Validate role exists
        try:
            role_oid = ObjectId(data.roleId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid role ID")
        
        role = await db.roles.find_one({
            "_id": role_oid,
            "sellerId": ObjectId(seller_id),
            "isActive": True
        })
        if not role:
            raise HTTPException(status_code=400, detail="Role not found or inactive")
        
        # Check email not already used
        existing = await db.users.find_one({"email": data.email.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create Firebase user
        try:
            # Check if Firebase is initialized
            firebase_app = firebase_admin.get_app()
            firebase_user = firebase_auth.create_user(
                email=data.email.lower(),
                password=data.password,
                display_name=data.name
            )
            firebase_uid = firebase_user.uid
        except ValueError:
            # Firebase not initialized (dev mode) - generate a placeholder UID
            import uuid
            firebase_uid = f"dev-emp-{uuid.uuid4().hex[:16]}"
            logger.warning(f"Firebase not initialized - using dev UID: {firebase_uid}")
        except firebase_admin.exceptions.FirebaseError as e:
            logger.error(f"Firebase error creating employee: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to create account: {str(e)}")
        
        now = datetime.now(timezone.utc)
        employee_doc = {
            "firebaseUid": firebase_uid,
            "email": data.email.lower(),
            "name": data.name,
            "phone": data.phone,
            "accountType": "employee",
            "sellerId": ObjectId(seller_id),
            "roleId": role_oid,
            "roles": ["employee"],
            "status": "active",
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await db.users.insert_one(employee_doc)
        employee_doc["_id"] = result.inserted_id
        employee_doc["roleName"] = role["name"]
        
        logger.info(f"Employee created: {data.email} for seller {seller_id}")
        if activity_log_service:
            await activity_log_service.log(seller_id, str(user["_id"]), "employee_created", "employees", str(result.inserted_id), data.name)
        return {"message": "Employee created", "employee": serialize_doc(employee_doc)}
    
    @router.put("/employees/{employee_id}")
    async def update_employee(employee_id: str, data: EmployeeUpdate, authorization: str = Header(...)):
        """Update an employee."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_EMPLOYEES.value)
        seller_id = await get_seller_id(user)
        
        try:
            emp_oid = ObjectId(employee_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid employee ID")
        
        # Check employee exists and belongs to seller
        employee = await db.users.find_one({
            "_id": emp_oid,
            "sellerId": ObjectId(seller_id),
            "accountType": "employee"
        })
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Build update
        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        
        if data.name is not None:
            update_fields["name"] = data.name
        if data.phone is not None:
            update_fields["phone"] = data.phone
        if data.status is not None:
            if data.status not in ["active", "inactive"]:
                raise HTTPException(status_code=400, detail="Invalid status")
            update_fields["status"] = data.status
        
        if data.roleId is not None:
            try:
                role_oid = ObjectId(data.roleId)
                role = await db.roles.find_one({
                    "_id": role_oid,
                    "sellerId": ObjectId(seller_id),
                    "isActive": True
                })
                if not role:
                    raise HTTPException(status_code=400, detail="Role not found or inactive")
                update_fields["roleId"] = role_oid
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid role ID")
        
        await db.users.update_one({"_id": emp_oid}, {"$set": update_fields})
        
        updated = await db.users.find_one({"_id": emp_oid})
        
        # Get role name
        if updated.get("roleId"):
            role = await db.roles.find_one({"_id": updated["roleId"]})
            updated["roleName"] = role["name"] if role else "No Role"
        
        return {"message": "Employee updated", "employee": serialize_doc(updated)}
    
    @router.delete("/employees/{employee_id}")
    async def deactivate_employee(employee_id: str, authorization: str = Header(...)):
        """Deactivate an employee (soft delete)."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_EMPLOYEES.value)
        seller_id = await get_seller_id(user)
        
        try:
            emp_oid = ObjectId(employee_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid employee ID")
        
        employee = await db.users.find_one({
            "_id": emp_oid,
            "sellerId": ObjectId(seller_id),
            "accountType": "employee"
        })
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Soft delete - set status to inactive
        await db.users.update_one(
            {"_id": emp_oid},
            {"$set": {"status": "inactive", "updatedAt": datetime.now(timezone.utc)}}
        )
        
        logger.info(f"Employee deactivated: {employee['email']} by seller {seller_id}")
        return {"message": "Employee deactivated"}
    
    # ===========================================
    # BUYER ENDPOINTS (Seller's CRM)
    # ===========================================
    
    @router.get("/buyers")
    async def list_buyers(
        authorization: str = Header(...),
        search: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """List all buyers for seller."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        
        query = {"sellerId": ObjectId(seller_id)}
        
        if search:
            query["$or"] = [
                {"buyerName": {"$regex": search, "$options": "i"}},
                {"company": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}}
            ]
        
        total = await db.seller_buyers.count_documents(query)
        buyers = await db.seller_buyers.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        
        return {
            "buyers": serialize_doc(buyers),
            "total": total,
            "limit": limit,
            "skip": skip
        }
    
    @router.post("/buyers")
    async def create_buyer(data: BuyerCreate, authorization: str = Header(...)):
        """Create a new buyer record."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        
        now = datetime.now(timezone.utc)
        buyer_doc = {
            "sellerId": ObjectId(seller_id),
            "buyerName": data.buyerName,
            "company": data.company,
            "phone": data.phone,
            "email": data.email.lower() if data.email else None,
            "gstNumber": data.gstNumber,
            "state": data.state,
            "address": data.address,
            "notes": data.notes,
            "totalOrders": 0,
            "totalSpent": 0,
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await db.seller_buyers.insert_one(buyer_doc)
        buyer_doc["_id"] = result.inserted_id
        
        if activity_log_service:
            await activity_log_service.log(seller_id, str(user["_id"]), "buyer_created", "buyers", str(result.inserted_id), data.buyerName)
        return {"message": "Buyer created", "buyer": serialize_doc(buyer_doc)}

    @router.post("/buyers/sync-offline")
    async def sync_offline_buyer(data: BuyerCreate, authorization: str = Header(...)):
        """Sync an offline-created buyer. Deduplicates by phone then name."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)

        # Deduplicate: check by normalized phone first
        phone = (data.phone or "").strip().replace(" ", "").replace("+91", "").replace("-", "")
        if phone:
            existing = await db.seller_buyers.find_one({
                "sellerId": ObjectId(seller_id),
                "phone": {"$regex": phone[-10:] + "$"}
            })
            if existing:
                return {"message": "Buyer already exists (phone match)", "buyer": serialize_doc(existing), "deduplicated": True}

        # Deduplicate: check by name (case-insensitive)
        name_lower = (data.buyerName or "").strip().lower()
        if name_lower:
            existing = await db.seller_buyers.find_one({
                "sellerId": ObjectId(seller_id),
                "buyerName": {"$regex": f"^{name_lower}$", "$options": "i"}
            })
            if existing:
                return {"message": "Buyer already exists (name match)", "buyer": serialize_doc(existing), "deduplicated": True}

        # No duplicate — create new
        now = datetime.now(timezone.utc)
        buyer_doc = {
            "sellerId": ObjectId(seller_id),
            "buyerName": data.buyerName,
            "company": data.company,
            "phone": data.phone,
            "email": data.email.lower() if data.email else None,
            "gstNumber": data.gstNumber,
            "state": data.state,
            "address": data.address,
            "notes": data.notes,
            "totalOrders": 0,
            "totalSpent": 0,
            "offlineSynced": True,
            "createdAt": now,
            "updatedAt": now
        }
        result = await db.seller_buyers.insert_one(buyer_doc)
        buyer_doc["_id"] = result.inserted_id
        return {"message": "Buyer synced", "buyer": serialize_doc(buyer_doc), "deduplicated": False}


    
    @router.get("/buyers/{buyer_id}")
    async def get_buyer(buyer_id: str, authorization: str = Header(...)):
        """Get a specific buyer."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        
        buyer = await db.seller_buyers.find_one({
            "_id": buyer_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        return {"buyer": serialize_doc(buyer)}
    
    @router.put("/buyers/{buyer_id}")
    async def update_buyer(buyer_id: str, data: BuyerUpdate, authorization: str = Header(...)):
        """Update a buyer record."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        
        buyer = await db.seller_buyers.find_one({
            "_id": buyer_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        for field in ["buyerName", "company", "phone", "email", "gstNumber", "state", "address", "notes"]:
            value = getattr(data, field, None)
            if value is not None:
                if field == "email":
                    update_fields[field] = value.lower()
                else:
                    update_fields[field] = value
        
        await db.seller_buyers.update_one({"_id": buyer_oid}, {"$set": update_fields})
        
        updated = await db.seller_buyers.find_one({"_id": buyer_oid})
        return {"message": "Buyer updated", "buyer": serialize_doc(updated)}
    
    @router.delete("/buyers/{buyer_id}")
    async def delete_buyer(buyer_id: str, authorization: str = Header(...)):
        """Delete a buyer record."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        
        result = await db.seller_buyers.delete_one({
            "_id": buyer_oid,
            "sellerId": ObjectId(seller_id)
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        return {"message": "Buyer deleted"}
    
    # ── Shipping Address CRUD ──

    @router.get("/buyers/{buyer_id}/shipping-addresses")
    async def list_shipping_addresses(buyer_id: str, authorization: str = Header(...)):
        """List all shipping addresses for a buyer."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        buyer = await db.seller_buyers.find_one({"_id": buyer_oid, "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")
        return {"addresses": buyer.get("shippingAddresses", [])}

    @router.post("/buyers/{buyer_id}/shipping-addresses")
    async def add_shipping_address(buyer_id: str, data: dict = Body(...), authorization: str = Header(...)):
        """Add a new shipping address to a buyer."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        buyer = await db.seller_buyers.find_one({"_id": buyer_oid, "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        import uuid
        addr = {
            "id": str(uuid.uuid4())[:8],
            "addressLine1": data.get("addressLine1", ""),
            "addressLine2": data.get("addressLine2", ""),
            "city": data.get("city", ""),
            "state": data.get("state", ""),
            "pincode": data.get("pincode", ""),
            "country": data.get("country", "India"),
            "contactPerson": data.get("contactPerson", ""),
            "phone": data.get("phone", ""),
            "isDefault": bool(data.get("isDefault", False)),
        }
        # If default, unset other defaults
        if addr["isDefault"]:
            existing = buyer.get("shippingAddresses", [])
            for a in existing:
                a["isDefault"] = False
            await db.seller_buyers.update_one({"_id": buyer_oid}, {"$set": {"shippingAddresses": existing}})

        await db.seller_buyers.update_one(
            {"_id": buyer_oid},
            {"$push": {"shippingAddresses": addr}, "$set": {"updatedAt": datetime.now(timezone.utc)}}
        )
        updated = await db.seller_buyers.find_one({"_id": buyer_oid})
        return {"message": "Address added", "address": addr, "addresses": updated.get("shippingAddresses", [])}

    @router.put("/buyers/{buyer_id}/shipping-addresses/{addr_id}")
    async def update_shipping_address(buyer_id: str, addr_id: str, data: dict = Body(...), authorization: str = Header(...)):
        """Update a shipping address."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        buyer = await db.seller_buyers.find_one({"_id": buyer_oid, "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        addresses = buyer.get("shippingAddresses", [])
        found = False
        is_default = bool(data.get("isDefault", False))
        for i, a in enumerate(addresses):
            if a["id"] == addr_id:
                addresses[i] = {
                    "id": addr_id,
                    "addressLine1": data.get("addressLine1", a.get("addressLine1", "")),
                    "addressLine2": data.get("addressLine2", a.get("addressLine2", "")),
                    "city": data.get("city", a.get("city", "")),
                    "state": data.get("state", a.get("state", "")),
                    "pincode": data.get("pincode", a.get("pincode", "")),
                    "country": data.get("country", a.get("country", "India")),
                    "contactPerson": data.get("contactPerson", a.get("contactPerson", "")),
                    "phone": data.get("phone", a.get("phone", "")),
                    "isDefault": is_default,
                }
                found = True
            elif is_default:
                addresses[i]["isDefault"] = False
        if not found:
            raise HTTPException(status_code=404, detail="Address not found")

        await db.seller_buyers.update_one(
            {"_id": buyer_oid},
            {"$set": {"shippingAddresses": addresses, "updatedAt": datetime.now(timezone.utc)}}
        )
        return {"message": "Address updated", "addresses": addresses}

    @router.delete("/buyers/{buyer_id}/shipping-addresses/{addr_id}")
    async def delete_shipping_address(buyer_id: str, addr_id: str, authorization: str = Header(...)):
        """Delete a shipping address."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        buyer = await db.seller_buyers.find_one({"_id": buyer_oid, "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")

        addresses = buyer.get("shippingAddresses", [])
        new_addresses = [a for a in addresses if a["id"] != addr_id]
        if len(new_addresses) == len(addresses):
            raise HTTPException(status_code=404, detail="Address not found")

        await db.seller_buyers.update_one(
            {"_id": buyer_oid},
            {"$set": {"shippingAddresses": new_addresses, "updatedAt": datetime.now(timezone.utc)}}
        )
        return {"message": "Address deleted", "addresses": new_addresses}

    # ── Sales Push (WhatsApp) ──

    @router.post("/buyers/{buyer_id}/sales-push")
    async def send_sales_push(buyer_id: str, data: dict = Body(...), authorization: str = Header(...)):
        """Generate WhatsApp sales push link for a buyer with catalog + optional invoice."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_BUYERS.value)
        seller_id = await get_seller_id(user)
        try:
            buyer_oid = ObjectId(buyer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid buyer ID")
        buyer = await db.seller_buyers.find_one({"_id": buyer_oid, "sellerId": ObjectId(seller_id)})
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")
        if not buyer.get("phone"):
            raise HTTPException(status_code=400, detail="Buyer phone number not available")

        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
        profile = (seller_user.get("profile") or {}) if seller_user else {}
        business_name = profile.get("businessName", "Seller")

        from utils.whatsapp_messages import catalog_marketing_message, BASE_URL
        import urllib.parse
        catalog_url = data.get("catalogUrl", BASE_URL)
        invoice_url = data.get("invoiceUrl", "")

        msg = catalog_marketing_message(
            catalog_url=catalog_url,
            business_name=business_name,
            buyer_name=buyer.get("buyerName", ""),
            invoice_url=invoice_url,
        )

        phone = buyer["phone"].replace(" ", "").replace("-", "").replace("+", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone

        wa_link = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
        return {"whatsappLink": wa_link, "message": msg, "buyerPhone": buyer["phone"]}

    # ===========================================
    # SUPPLIER ENDPOINTS
    # ===========================================
    
    @router.get("/suppliers")
    async def list_suppliers(
        authorization: str = Header(...),
        search: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """List all suppliers for seller."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_SUPPLIERS.value)
        seller_id = await get_seller_id(user)
        
        query = {"sellerId": ObjectId(seller_id)}
        
        if search:
            query["$or"] = [
                {"supplierName": {"$regex": search, "$options": "i"}},
                {"contact": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]
        
        total = await db.seller_suppliers.count_documents(query)
        suppliers = await db.seller_suppliers.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        
        return {
            "suppliers": serialize_doc(suppliers),
            "total": total,
            "limit": limit,
            "skip": skip
        }
    
    @router.post("/suppliers")
    async def create_supplier(data: SupplierCreate, authorization: str = Header(...)):
        """Create a new supplier record."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_SUPPLIERS.value)
        seller_id = await get_seller_id(user)
        
        now = datetime.now(timezone.utc)
        supplier_doc = {
            "sellerId": ObjectId(seller_id),
            "supplierName": data.supplierName,
            "contact": data.contact,
            "phone": data.phone,
            "email": data.email.lower() if data.email else None,
            "gstNumber": data.gstNumber,
            "address": data.address,
            "notes": data.notes,
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await db.seller_suppliers.insert_one(supplier_doc)
        supplier_doc["_id"] = result.inserted_id
        
        # Save supplier-product mappings
        if data.products:
            sp_docs = []
            for p in data.products:
                sp_docs.append({
                    "sellerId": ObjectId(seller_id),
                    "supplierId": result.inserted_id,
                    "listingId": ObjectId(p.listingId),
                    "rate": p.rate,
                    "createdAt": now,
                    "updatedAt": now
                })
            if sp_docs:
                await db.supplier_products.insert_many(sp_docs)
        
        if activity_log_service:
            await activity_log_service.log(seller_id, str(user["_id"]), "supplier_created", "suppliers", str(result.inserted_id), data.supplierName)
        return {"message": "Supplier created", "supplier": serialize_doc(supplier_doc)}
    
    @router.get("/suppliers/{supplier_id}")
    async def get_supplier(supplier_id: str, authorization: str = Header(...)):
        """Get a specific supplier with its product mappings."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_SUPPLIERS.value)
        seller_id = await get_seller_id(user)
        
        try:
            supplier_oid = ObjectId(supplier_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid supplier ID")
        
        supplier = await db.seller_suppliers.find_one({
            "_id": supplier_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Get product mappings
        sp_items = await db.supplier_products.find({"supplierId": supplier_oid}).to_list(200)
        products = []
        for sp in sp_items:
            listing = await db.sellerListings.find_one({"_id": sp["listingId"]})
            if listing:
                product = await db.products.find_one({"_id": listing["productId"]})
                products.append({
                    "id": str(sp["_id"]),
                    "listingId": str(sp["listingId"]),
                    "productName": product["name"] if product else "Unknown",
                    "description": product.get("description", "") if product else "",
                    "sku": listing.get("sku", ""),
                    "rate": sp["rate"],
                })
        
        result = serialize_doc(supplier)
        result["products"] = products
        return {"supplier": result}
    
    @router.put("/suppliers/{supplier_id}")
    async def update_supplier(supplier_id: str, data: SupplierUpdate, authorization: str = Header(...)):
        """Update a supplier record and its product mappings."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_SUPPLIERS.value)
        seller_id = await get_seller_id(user)
        
        try:
            supplier_oid = ObjectId(supplier_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid supplier ID")
        
        supplier = await db.seller_suppliers.find_one({
            "_id": supplier_oid,
            "sellerId": ObjectId(seller_id)
        })
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        now = datetime.now(timezone.utc)
        update_fields = {"updatedAt": now}
        for field in ["supplierName", "contact", "phone", "email", "gstNumber", "address", "notes"]:
            value = getattr(data, field, None)
            if value is not None:
                if field == "email":
                    update_fields[field] = value.lower()
                else:
                    update_fields[field] = value
        
        await db.seller_suppliers.update_one({"_id": supplier_oid}, {"$set": update_fields})
        
        # Update product mappings if provided
        if data.products is not None:
            await db.supplier_products.delete_many({"supplierId": supplier_oid})
            if data.products:
                sp_docs = []
                for p in data.products:
                    sp_docs.append({
                        "sellerId": ObjectId(seller_id),
                        "supplierId": supplier_oid,
                        "listingId": ObjectId(p.listingId),
                        "rate": p.rate,
                        "createdAt": now,
                        "updatedAt": now
                    })
                await db.supplier_products.insert_many(sp_docs)
        
        updated = await db.seller_suppliers.find_one({"_id": supplier_oid})
        return {"message": "Supplier updated", "supplier": serialize_doc(updated)}
    
    @router.delete("/suppliers/{supplier_id}")
    async def delete_supplier(supplier_id: str, authorization: str = Header(...)):
        """Delete a supplier record and its product mappings."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_SUPPLIERS.value)
        seller_id = await get_seller_id(user)
        
        try:
            supplier_oid = ObjectId(supplier_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid supplier ID")
        
        result = await db.seller_suppliers.delete_one({
            "_id": supplier_oid,
            "sellerId": ObjectId(seller_id)
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Clean up product mappings
        await db.supplier_products.delete_many({"supplierId": supplier_oid})
        
        return {"message": "Supplier deleted"}
    
    # ===========================================
    # USER PERMISSIONS ENDPOINT
    # ===========================================
    
    @router.get("/my-permissions")
    async def get_my_permissions(authorization: str = Header(...)):
        """Get current user's permissions."""
        user = await get_current_user(authorization)
        
        # Platform admin has all permissions
        if is_platform_admin(user):
            return {
                "accountType": "admin",
                "isAdmin": True,
                "permissions": ALL_PERMISSIONS,
                "role": None
            }
        
        account_type = user.get("accountType", "seller")
        
        if account_type == "seller":
            # Seller Admin has all permissions
            return {
                "accountType": "seller",
                "isAdmin": True,
                "permissions": ALL_PERMISSIONS,
                "role": None
            }
        
        # Employee - get role permissions
        role_id = user.get("roleId")
        role = None
        permissions = []
        
        if role_id:
            role = await db.roles.find_one({"_id": role_id, "isActive": True})
            if role:
                permissions = role.get("permissions", [])
        
        return {
            "accountType": "employee",
            "isAdmin": False,
            "permissions": permissions,
            "role": serialize_doc(role) if role else None
        }
    
    # ===========================================
    # SUPPLIER PRODUCTS LOOKUP
    # ===========================================
    
    @router.get("/suppliers-for-listing/{listing_id}")
    async def get_suppliers_for_listing(listing_id: str, authorization: str = Header(...)):
        """Get all suppliers who supply a specific product/listing."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        
        try:
            listing_oid = ObjectId(listing_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid listing ID")
        
        sp_items = await db.supplier_products.find({
            "sellerId": ObjectId(seller_id),
            "listingId": listing_oid
        }).to_list(100)
        
        suppliers = []
        for sp in sp_items:
            supplier = await db.seller_suppliers.find_one({"_id": sp["supplierId"]})
            if supplier:
                suppliers.append({
                    "supplierId": str(supplier["_id"]),
                    "supplierName": supplier.get("supplierName", ""),
                    "phone": supplier.get("phone", ""),
                    "rate": sp["rate"],
                })
        
        # Sort by rate ascending (best price first)
        suppliers.sort(key=lambda x: x["rate"])
        return {"suppliers": suppliers}
    
    # ===========================================
    # LOW STOCK ALERTS
    # ===========================================
    
    @router.get("/low-stock-alerts")
    async def get_low_stock_alerts(
        authorization: str = Header(...),
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ):
        """Get low stock alerts for the seller or all sellers (admin)."""
        user = await get_current_user(authorization)
        await require_permission(user, Permission.MANAGE_INVENTORY.value)
        
        is_admin = is_platform_admin(user)
        
        if is_admin:
            query = {}
        else:
            seller_id = await get_seller_id(user)
            query = {"sellerId": ObjectId(seller_id)}
        
        if status:
            query["status"] = status
        
        total = await db.low_stock_alerts.count_documents(query)
        alerts = await db.low_stock_alerts.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        
        # Cache seller names for admin view
        seller_cache = {}
        
        # Enrich with product data
        enriched = []
        for alert in alerts:
            listing = await db.sellerListings.find_one({"_id": alert.get("listingId")})
            product = None
            if listing:
                product = await db.products.find_one({"_id": listing.get("productId")})
            
            item = serialize_doc(alert)
            item["productName"] = product["name"] if product else alert.get("productName", "Unknown")
            item["sku"] = listing.get("sku", "") if listing else ""
            item["description"] = product.get("description", "") if product else ""
            item["currentStock"] = listing.get("stock", 0) if listing else alert.get("currentStock", 0)
            # Get specifications from listing attributes
            if listing:
                attrs = listing.get("searchableAttributes", {})
                labels = listing.get("attributeLabels", {})
                specs = []
                for k, v in attrs.items():
                    label = labels.get(k, k)
                    specs.append(f"{label}: {v}")
                item["specification"] = "\n".join(specs) if specs else ""
            else:
                item["specification"] = ""
            
            # For admin view: enrich with seller name
            if is_admin:
                alert_seller_id = str(alert.get("sellerId", ""))
                if alert_seller_id and alert_seller_id not in seller_cache:
                    try:
                        seller_user = await db.users.find_one({"_id": ObjectId(alert_seller_id)})
                        if seller_user:
                            profile = seller_user.get("profile", {}) or {}
                            seller_cache[alert_seller_id] = profile.get("businessName") or seller_user.get("name") or seller_user.get("email", "Unknown Seller")
                        else:
                            seller_cache[alert_seller_id] = "Unknown Seller"
                    except Exception:
                        seller_cache[alert_seller_id] = "Unknown Seller"
                item["sellerName"] = seller_cache.get(alert_seller_id, "Unknown Seller")
            
            enriched.append(item)
        
        # Pending count: scoped to seller or all
        if is_admin:
            pending_count = await db.low_stock_alerts.count_documents({"status": "pending"})
        else:
            pending_count = await db.low_stock_alerts.count_documents({"sellerId": ObjectId(seller_id), "status": "pending"})
        
        return {
            "alerts": enriched,
            "total": total,
            "pendingCount": pending_count,
            "isAdminView": is_admin,
            "limit": limit,
            "skip": skip
        }
    
    @router.get("/low-stock-alerts/{alert_id}/order-details")
    async def get_order_details(alert_id: str, authorization: str = Header(...)):
        """Get full product details and suppliers for the order form."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        
        try:
            alert_oid = ObjectId(alert_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid alert ID")
        
        alert = await db.low_stock_alerts.find_one({"_id": alert_oid, "sellerId": ObjectId(seller_id)})
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        listing_id = alert.get("listingId")
        listing = await db.sellerListings.find_one({"_id": listing_id})
        product = None
        if listing:
            product = await db.products.find_one({"_id": listing.get("productId")})
        
        # Get specifications
        specs = ""
        if listing:
            attrs = listing.get("searchableAttributes", {})
            labels = listing.get("attributeLabels", {})
            parts = []
            for k, v in attrs.items():
                label = labels.get(k, k)
                parts.append(f"{label}: {v}")
            specs = "\n".join(parts)
        
        # Get suppliers for this listing
        sp_items = await db.supplier_products.find({
            "sellerId": ObjectId(seller_id),
            "listingId": listing_id
        }).to_list(100)
        
        suppliers = []
        for sp in sp_items:
            supplier = await db.seller_suppliers.find_one({"_id": sp["supplierId"]})
            if supplier:
                suppliers.append({
                    "supplierId": str(supplier["_id"]),
                    "supplierName": supplier.get("supplierName", ""),
                    "phone": supplier.get("phone", ""),
                    "rate": sp["rate"],
                })
        suppliers.sort(key=lambda x: x["rate"])
        
        # Get seller profile for message footer
        profile = user.get("profile") or {}
        
        return {
            "alert": serialize_doc(alert),
            "product": {
                "productName": product["name"] if product else "Unknown",
                "sku": listing.get("sku", "") if listing else "",
                "description": product.get("description", "") if product else "",
                "specification": specs,
                "currentStock": listing.get("stock", 0) if listing else 0,
                "minStock": alert.get("minStock", 0),
            },
            "suppliers": suppliers,
            "sellerProfile": {
                "businessName": profile.get("businessName", ""),
                "phone": profile.get("phone", ""),
            }
        }
    
    @router.put("/low-stock-alerts/{alert_id}/status")
    async def update_alert_status(alert_id: str, data: LowStockAlertStatusUpdate, authorization: str = Header(...)):
        """Update a low stock alert status to ordered or ignored."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)
        
        try:
            alert_oid = ObjectId(alert_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid alert ID")
        
        alert = await db.low_stock_alerts.find_one({"_id": alert_oid, "sellerId": ObjectId(seller_id)})
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        await db.low_stock_alerts.update_one(
            {"_id": alert_oid},
            {"$set": {"status": data.status, "updatedAt": datetime.now(timezone.utc)}}
        )
        
        return {"message": f"Alert marked as {data.status}"}

    # ─── GST CONFIG ENDPOINTS ───

    @router.get("/gst-config")
    async def get_gst_config():
        """Get Indian states list and GST rates for frontend dropdowns."""
        return {"states": INDIAN_STATES, "gstRates": GST_RATES}

    @router.post("/gst-calculate")
    async def calculate_gst_preview(authorization: str = Header(...), buyerId: str = "", gstPercent: float = 0, taxableAmount: float = 0):
        """Preview GST calculation for given buyer and seller states."""
        user = await get_current_user(authorization)
        seller_id = await get_seller_id(user)

        seller_user = await db.users.find_one({"_id": ObjectId(seller_id)}) if seller_id else None
        seller_state = (seller_user or {}).get("profile", {}).get("state", "")

        buyer_state = ""
        if buyerId:
            try:
                buyer = await db.seller_buyers.find_one({"_id": ObjectId(buyerId)})
                buyer_state = (buyer or {}).get("state", "")
            except Exception:
                pass

        gst_enabled = (seller_user or {}).get("gst", {}).get("status") != "disabled"
        result = calculate_gst(taxableAmount, gstPercent, seller_state, buyer_state, gst_enabled)
        result["sellerState"] = seller_state
        result["buyerState"] = buyer_state
        result["taxType"] = "intra" if seller_state and buyer_state and seller_state.strip().lower() == buyer_state.strip().lower() else "inter"
        return result

    return router
