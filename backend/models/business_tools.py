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
    VIEW_PURCHASE_PRICE = "view_purchase_price"
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

class SupplierProductItem(BaseModel):
    listingId: str
    rate: float = Field(..., ge=0)


class SupplierCreate(BaseModel):
    supplierName: str = Field(..., min_length=1, max_length=100)
    contact: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    gstNumber: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    products: Optional[List[SupplierProductItem]] = None


class SupplierUpdate(BaseModel):
    supplierName: Optional[str] = Field(None, min_length=1, max_length=100)
    contact: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    gstNumber: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    products: Optional[List[SupplierProductItem]] = None


class LowStockAlertStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ordered|ignored)$")


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
    minStock: Optional[int] = Field(None, ge=0)
    reorderQuantity: Optional[int] = Field(None, ge=0)
    lowStockAlertEnabled: Optional[bool] = None
    warehouseLocation: Optional[str] = Field(None, max_length=100)
    purchase_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)


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


# ===========================================
# COMPOSITE PRODUCT MODELS
# ===========================================

class CompositeProductItemCreate(BaseModel):
    productId: str
    quantity: int = Field(..., ge=1)

class CompositeProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    items: List[CompositeProductItemCreate] = Field(..., min_length=1)

class CompositeProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    items: Optional[List[CompositeProductItemCreate]] = None

class CompositeProductSell(BaseModel):
    quantity: int = Field(1, ge=1)
    note: Optional[str] = Field(None, max_length=500)


# ===========================================
# INVOICE MODELS
# ===========================================

class InvoiceItemCreate(BaseModel):
    productId: Optional[str] = None
    productName: Optional[str] = None
    hsnCode: Optional[str] = Field(None, max_length=20, description="HSN/SAC code")
    quantity: int = Field(..., ge=1)
    price: float = Field(..., ge=0)
    discount: float = Field(0, ge=0, description="Discount amount on this line")
    gstPercent: float = Field(0, ge=0, le=100)
    selected_specifications: Optional[List[dict]] = Field(None, description="List of {key, value} specs")

class TransportDetails(BaseModel):
    transporterName: Optional[str] = Field(None, max_length=200)
    lrNumber: Optional[str] = Field(None, max_length=100, description="Lorry Receipt Number")
    vehicleNumber: Optional[str] = Field(None, max_length=50)
    bookingLocation: Optional[str] = Field(None, max_length=200)
    numberOfPackages: Optional[int] = Field(None, ge=0)

class InvoiceCreate(BaseModel):
    buyerId: str
    items: List[InvoiceItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=1000)
    deductStock: bool = True
    dueDays: int = Field(7, ge=1, le=365, description="Payment due in N days")
    poNumber: Optional[str] = Field(None, max_length=100, description="Purchase Order reference")
    challanNumber: Optional[str] = Field(None, max_length=100, description="Challan number")
    placeOfSupply: Optional[str] = Field(None, max_length=100, description="Place of supply for GST")
    transport: Optional[TransportDetails] = None
    termsAndConditions: Optional[str] = Field(None, max_length=2000)

class InvoiceStatusUpdate(BaseModel):
    status: str  # draft, sent, viewed, partially_paid, paid, overdue, cancelled


class PaymentEntryCreate(BaseModel):
    amount: float = Field(..., gt=0)
    paymentDate: Optional[str] = None
    paymentMethod: str = Field("cash")
    accountName: Optional[str] = Field(None, max_length=200)
    accountType: Optional[str] = Field(None)
    referenceNumber: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)
    receiptUrls: Optional[List[str]] = Field(None, description="Cloudinary URLs for payment receipts")


class ReminderSettingsUpdate(BaseModel):
    enabled: bool = True
    reminderDays: List[int] = Field(default=[3, 7, 15])
    customMessages: Optional[dict] = Field(None, description="Custom messages keyed by day number")


# ===========================================
# ACTIVITY LOG MODELS
# ===========================================

class ActivityLogAction(str, Enum):
    EMPLOYEE_CREATED = "employee_created"
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    STOCK_ADJUSTED = "stock_adjusted"
    BUYER_CREATED = "buyer_created"
    SUPPLIER_CREATED = "supplier_created"
    INVOICE_CREATED = "invoice_created"
    COMPOSITE_PRODUCT_CREATED = "composite_product_created"
    COMPOSITE_PRODUCT_SOLD = "composite_product_sold"
