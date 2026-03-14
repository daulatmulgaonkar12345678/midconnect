"""
Business Tools Router - RBAC, Employees, Buyers, Suppliers
"""

from fastapi import APIRouter, HTTPException, Depends, Header
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
    Permission, ALL_PERMISSIONS, AccountType
)

logger = logging.getLogger(__name__)


def init_business_tools_router(db, verify_token_func):
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
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        
        try:
            decoded_token = await verify_token_func(token)
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        if not decoded_token:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get user from database
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user = await db.users.find_one({"firebaseUid": firebase_uid})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check account status
        if user.get("accountStatus") == "deleted":
            raise HTTPException(status_code=403, detail="Account has been deactivated")
        
        # For employees, check if status is active
        if user.get("accountType") == "employee" and user.get("status") != "active":
            raise HTTPException(status_code=403, detail="Employee account is inactive")
        
        return user
    
    async def get_seller_id(user: dict) -> str:
        """Get seller ID for current user (seller or employee)."""
        account_type = user.get("accountType", "seller")
        
        if account_type == "employee":
            # Employee - return their linked sellerId
            seller_id = user.get("sellerId")
            if not seller_id:
                raise HTTPException(status_code=403, detail="Employee not linked to seller")
            return str(seller_id)
        else:
            # Seller - return their own ID
            return str(user.get("_id"))
    
    async def check_permission(user: dict, permission: str) -> bool:
        """Check if user has a specific permission."""
        account_type = user.get("accountType", "seller")
        
        # Seller Admin has all permissions
        if account_type == "seller":
            return True
        
        # Employee - check role permissions
        role_id = user.get("roleId")
        if not role_id:
            return False
        
        try:
            role = await db.roles.find_one({"_id": ObjectId(role_id), "isActive": True})
            if role and permission in role.get("permissions", []):
                return True
        except Exception:
            pass
        
        return False
    
    async def require_permission(user: dict, permission: str):
        """Require a specific permission or raise 403."""
        has_perm = await check_permission(user, permission)
        if not has_perm:
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied: {permission} required"
            )
    
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
            "address": data.address,
            "notes": data.notes,
            "totalOrders": 0,
            "totalSpent": 0,
            "createdAt": now,
            "updatedAt": now
        }
        
        result = await db.seller_buyers.insert_one(buyer_doc)
        buyer_doc["_id"] = result.inserted_id
        
        return {"message": "Buyer created", "buyer": serialize_doc(buyer_doc)}
    
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
        for field in ["buyerName", "company", "phone", "email", "gstNumber", "address", "notes"]:
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
        
        return {"message": "Supplier created", "supplier": serialize_doc(supplier_doc)}
    
    @router.get("/suppliers/{supplier_id}")
    async def get_supplier(supplier_id: str, authorization: str = Header(...)):
        """Get a specific supplier."""
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
        
        return {"supplier": serialize_doc(supplier)}
    
    @router.put("/suppliers/{supplier_id}")
    async def update_supplier(supplier_id: str, data: SupplierUpdate, authorization: str = Header(...)):
        """Update a supplier record."""
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
        
        update_fields = {"updatedAt": datetime.now(timezone.utc)}
        for field in ["supplierName", "contact", "phone", "email", "gstNumber", "address", "notes"]:
            value = getattr(data, field, None)
            if value is not None:
                if field == "email":
                    update_fields[field] = value.lower()
                else:
                    update_fields[field] = value
        
        await db.seller_suppliers.update_one({"_id": supplier_oid}, {"$set": update_fields})
        
        updated = await db.seller_suppliers.find_one({"_id": supplier_oid})
        return {"message": "Supplier updated", "supplier": serialize_doc(updated)}
    
    @router.delete("/suppliers/{supplier_id}")
    async def delete_supplier(supplier_id: str, authorization: str = Header(...)):
        """Delete a supplier record."""
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
        
        return {"message": "Supplier deleted"}
    
    # ===========================================
    # USER PERMISSIONS ENDPOINT
    # ===========================================
    
    @router.get("/my-permissions")
    async def get_my_permissions(authorization: str = Header(...)):
        """Get current user's permissions."""
        user = await get_current_user(authorization)
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
    
    return router
