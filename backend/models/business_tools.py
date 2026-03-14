"""
Business Tools Models for Seller Dashboard
- Roles & Permissions (RBAC)
- Employees
- Buyers
- Suppliers
- Inventory extensions
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ===========================================
# PERMISSIONS ENUM
# ===========================================

class Permission(str, Enum):
    MANAGE_LISTINGS = "manage_listings"
    MANAGE_INVENTORY = "manage_inventory"
    VIEW_ENQUIRIES = "view_enquiries"
    MANAGE_BUYERS = "manage_buyers"
    MANAGE_SUPPLIERS = "manage_suppliers"
    CREATE_INVOICE = "create_invoice"
    VIEW_REPORTS = "view_reports"
    MANAGE_EMPLOYEES = "manage_employees"
    MANAGE_ROLES = "manage_roles"


ALL_PERMISSIONS = [p.value for p in Permission]


# ===========================================
# ACCOUNT TYPE ENUM
# ===========================================

class AccountType(str, Enum):
    SELLER = "seller"
    EMPLOYEE = "employee"
    BUYER = "buyer"


# ===========================================
# ROLE MODELS
# ===========================================

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None
    isActive: Optional[bool] = None


class RoleResponse(BaseModel):
    id: str
    sellerId: str
    name: str
    description: Optional[str] = None
    permissions: List[str]
    isActive: bool = True
    createdAt: datetime
    updatedAt: datetime


# ===========================================
# EMPLOYEE MODELS
# ===========================================

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    roleId: str
    phone: Optional[str] = Field(None, max_length=20)


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    roleId: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = None  # active, inactive


class EmployeeResponse(BaseModel):
    id: str
    sellerId: str
    name: str
    email: str
    roleId: str
    roleName: Optional[str] = None
    phone: Optional[str] = None
    status: str = "active"
    accountType: str = "employee"
    createdAt: datetime
    lastLoginAt: Optional[datetime] = None


# ===========================================
# BUYER MODELS (Seller's CRM)
# ===========================================

class BuyerCreate(BaseModel):
    buyerName: str = Field(..., min_length=1, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    gstNumber: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class BuyerUpdate(BaseModel):
    buyerName: Optional[str] = Field(None, min_length=1, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    gstNumber: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class BuyerResponse(BaseModel):
    id: str
    sellerId: str
    buyerName: str
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstNumber: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    totalOrders: int = 0
    totalSpent: float = 0
    createdAt: datetime
    updatedAt: datetime


# ===========================================
# SUPPLIER MODELS
# ===========================================

class SupplierCreate(BaseModel):
    supplierName: str = Field(..., min_length=1, max_length=100)
    contact: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    gstNumber: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class SupplierUpdate(BaseModel):
    supplierName: Optional[str] = Field(None, min_length=1, max_length=100)
    contact: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    gstNumber: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class SupplierResponse(BaseModel):
    id: str
    sellerId: str
    supplierName: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstNumber: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


# ===========================================
# INVENTORY EXTENSION MODELS
# ===========================================

class InventoryUpdate(BaseModel):
    sku: Optional[str] = Field(None, max_length=50)
    stockQuantity: Optional[int] = Field(None, ge=0)
    lowStockAlert: Optional[int] = Field(None, ge=0)
    warehouseLocation: Optional[str] = Field(None, max_length=100)


class InventoryLogType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    DAMAGE = "damage"


class InventoryLogCreate(BaseModel):
    listingId: str
    changeType: InventoryLogType
    quantity: int
    note: Optional[str] = Field(None, max_length=500)


class InventoryLogResponse(BaseModel):
    id: str
    sellerId: str
    listingId: str
    productName: Optional[str] = None
    changeType: str
    quantity: int
    previousStock: int
    newStock: int
    note: Optional[str] = None
    createdBy: Optional[str] = None
    createdAt: datetime
