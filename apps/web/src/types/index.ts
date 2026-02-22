/**
 * Type definitions for MidConnect B2B Marketplace
 * SSOT: All types use strict camelCase to match backend API responses
 */

// Re-export API types
export * from './api';

// ==================== Core Types ====================

export interface Category {
  _id: string;
  name: string;
  description: string;
  icon?: string;
  image?: string;
  displayOrder?: number;
  isActive: boolean;
  productCount?: number;
  listingCount?: number;
}

export interface TechnicalSpec {
  name: string;
  key: string;
  type: string;
  options?: string[];
  unit?: string;
  required: boolean;
}

export interface Product {
  _id: string;
  categoryId: string;
  family: string;
  variant: string;
  name: string;
  description: string;
  unit: string;
  specSchema: TechnicalSpec[];
  specTemplateId?: string;
  specTemplateIds?: string[];
  isActive: boolean;
}

// ==================== Pricing Types ====================

/**
 * PricingTier - SSOT for pricing structure
 * Used across listings, quotes, and all pricing operations
 * minQty is REQUIRED - always initialized, never undefined at runtime
 */
export interface PricingTier {
  minQty: number;
  maxQty: number | null;
  pricePerUnit: number;
  currency?: string;
}

export interface PricingSlab extends PricingTier {
  minQuantity?: number;
  maxQuantity?: number | null;
  timeBasis?: 'day' | 'week' | 'month';
}

export type PricingTierCreate = PricingTier;

// ==================== Seller Types ====================

export interface Seller {
  listingId: string;
  sellerRole: string;
  sellerArea: string;
  sellerState: string;
  quantity: number;
  moq: number;
  maxCapacity: number;
  pricingTiers: PricingTier[];
  leadTime?: string;
  images: string[];
  updateStatus: string;
  locationClass?: 'LOCAL' | 'STATE' | 'NATIONAL';
}

export interface ProductWithSellers {
  productId: string;
  productName: string;
  productFamily: string;
  productVariant: string;
  productUnit: string;
  categoryName: string;
  specSchema: TechnicalSpec[];
  sellerCount: number;
  minPrice?: number;
  sellers: Seller[];
  badge?: string;
  badgeType?: string;
}

export interface ProductSeller {
  listingId: string;
  sellerId: string;
  companyName: string;
  location: string;
  moq: number;
  pricingTiers: PricingTier[];
  leadTimeDays?: number;
  stockStatus: string;
  images: string[];
}

export interface ProductWithAllSellers {
  productId: string;
  productName: string;
  slug: string;
  categoryId: string;
  categoryName: string;
  description?: string;
  specifications: Record<string, string | number>;
  images: string[];
  sellerCount: number;
  sellers: ProductSeller[];
}


export interface ProductWithAllSellers {
  productId: string;
  productName: string;
  slug: string;
  categoryId: string;
  categoryName: string;
  description?: string;
  specifications: Record<string, string | number>;
  images: string[];
  sellerCount: number;
  sellers: ProductSeller[];
}

// ==================== User Types ====================

export interface User {
  _id: string;
  firebaseUid: string;
  email: string;
  businessName: string;
  phone: string;
  city: string;
  state: string;
  pincode: string;
  address?: string;

  roles: UserRole[]; // ✅ ADDED

  isSeller: boolean;
  isAdmin: boolean;

  gstNumber?: string;
  gstStatus: 'PENDING' | 'VERIFIED' | 'REJECTED' | 'NOT_SUBMITTED';
  accountStatus: 'ACTIVE' | 'PENDING_DELETION' | 'SUSPENDED';
  emailVerified: boolean;
}

export interface UserProfile {
  _id: string;
  email: string;
  firebaseUid: string;
  businessName: string;
  phone: string;
  city: string;
  state: string;
  pincode: string;
  address?: string;

  roles: UserRole[]; // ✅ FIXES YOUR BUILD ERROR

  gstNumber?: string;
  gstStatus: 'PENDING' | 'VERIFIED' | 'REJECTED' | 'NOT_SUBMITTED';

  isSeller: boolean;
  isAdmin: boolean;

  emailVerified: boolean;
  accountStatus: 'ACTIVE' | 'PENDING_DELETION' | 'SUSPENDED';

  subscription?: {
    status: string;
    trialEndsAt?: string;
    enquiriesThisMonth: number;
  };
}

// ==================== Seller Listing Types ====================

export interface SellerListing {
  _id: string;
  sellerId: string;
  productId: string;
  variantId: string;
  categoryId: string;
  sellerRole: string;
  attributes: Record<string, string | number | boolean>;
  description?: string;
  images: string[];
  datasheetUrl?: string;
  moq: number;
  stock: number;
  maxCapacity?: number;
  leadTime?: number;
  currency: string;
  pricingTiers: PricingTier[];
  status: 'draft' | 'active' | 'paused' | 'archived';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  publishedAt?: string;
  productName?: string;
  categoryName?: string;
  product?: {
    _id: string;
    productName: string;
    categoryId?: string;
  };
  variant?: {
    _id: string;
    attributes: Record<string, string | number | boolean>;
  };
}

// ==================== Inquiry/Enquiry Types ====================

export interface InquiryQuote {
  price: number;
  moq?: number;
  leadTimeDays?: number;
  validTill: string;
  sellerNote?: string;
}

export interface BuyerInquiry {
  _id: string;
  productId?: string;
  productName?: string;
  listing?: {
    name: string;
    image?: string;
    category?: string;
  };
  seller: {
    businessName: string;
    city?: string;
    state?: string;
    phone?: string;
    email?: string;
    whatsapp?: string;
  };
  quantity: number;
  message?: string;
  status: 'pending' | 'accepted' | 'rejected' | 'reported';
  sellerResponse?: {
    quotedPrice?: number;
    message?: string;
  };
  createdAt: string;
  updatedAt?: string;
}

export interface SellerInquiry {
  _id: string;
  listingId: string;
  listingName?: string;
  listingImage?: string;
  quantity: number;
  requirementNote?: string;
  buyerType: string;
  status: 'pending' | 'accepted' | 'rejected' | 'reported';
  buyerMasked?: {
    city?: string;
    state?: string;
    buyerType?: string;
    companyInitial?: string;
  };
  buyerInfo?: {
    name?: string;
    companyName?: string;
    phone?: string;
    email?: string;
    city?: string;
    state?: string;
  };
  quote?: InquiryQuote;
  createdAt: string;
}

// ==================== Admin Types ====================

export interface AdminUser {
  id: string;
  email: string;
  profile: {
    businessName?: string;
    phone?: string;
    city?: string;
    state?: string;
    pincode?: string;
    address?: string;
  };
  gst?: {
    number?: string;
    status?: string;
    verified?: boolean;
  };
  roles: string[];
  isAdmin: boolean;
  isSeller: boolean;
  accountStatus: string;
  emailVerified: boolean;
  canLogin: boolean;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
  deletedAt?: string;
  listingCount?: number;
  subscriptionStatus?: string;
  subscriptionPlan?: string;
  subscriptionEnd?: string;
  daysRemaining?: number;
  isExpiringSoon?: boolean;
}

export interface AdminProduct {
  _id: string;
  name: string;
  categoryId?: string;
  categoryName?: string;
  categoryExists?: boolean;
  description?: string;
  family?: string;
  variant?: string;
  coverImageUrl?: string;
  specTemplateId?: string;
  specTemplateIds?: string[];
  isActive?: boolean;
  listingCount?: number;
}

export interface AdminSpecTemplate {
  _id: string;
  name: string;
  categoryId?: string;
  categoryName?: string;
  fields: Array<{
    key: string;
    label: string;
    fieldType?: string;
    displayOrder?: number;
    unit?: string;
    options?: string[];
    required?: boolean;
  }>;
  isActive?: boolean;
}

export interface AdminInquiry {
  _id: string;
  buyer: {
    id: string;
    name: string | null;
    email: string | null;
    city: string | null;
    state: string | null;
  };
  seller: {
    id: string;
    name: string | null;
    email: string | null;
    city: string | null;
    state: string | null;
  };
  product: {
    id: string | null;
    name: string | null;
    listingId: string | null;
  };
  category: string | null;
  quantity: number;
  message: string | null;
  status: 'pending' | 'accepted' | 'rejected' | 'reported';
  buyerType: string | null;
  createdAt: string;
  acceptedAt: string | null;
  quote?: {
    price: number;
    moq?: number;
    leadTimeDays?: number;
    validTill: string;
    sellerNote?: string;
  };
  rejection?: {
    reason: string;
    note?: string;
  };
  report?: {
    type: string;
    details?: string;
  };
  sellerSubscriptionPlan: string | null;
}

export interface AdminStats {
  users: {
    total: number;
    active: number;
    deleted: number;
    sellers: number;
    pendingGst: number;
  };
  catalog: {
    categories: number;
    products: number;
    manufacturers?: number;
    specTemplates: number;
  };
  listings: {
    total: number;
    active: number;
    drafts: number;
    paused?: number;
  };
  requests?: {
    pendingManufacturers: number;
    pendingProducts: number;
  };
  inquiries: {
    total: number;
    pending: number;
    accepted: number;
    rejected: number;
    reported: number;
    thisMonth: number;
    acceptedThisMonth: number;
  };
  subscriptions?: {
    free: number;
    trial: number;
    pro: number;
    noSubscription: number;
    expiringSoon: number;
  };
}

// ==================== Subscription Types ====================

export interface SubscriptionDetails {
  _id: string;
  userId: string;
  planName: 'free' | 'trial' | 'pro';
  durationDays: number;
  startDate: string;
  endDate: string | null;
  status: 'active' | 'expired' | 'suspended';
  daysRemaining: number;
  isExpiringSoon: boolean;
  lastUpdatedBy: string;
  updatedAt: string;
  notes: string;
}

export interface SellerSubscriptionStatus {
  subscription: {
    planName: 'free' | 'trial' | 'pro';
    status: 'active' | 'expired' | 'suspended';
    startDate: string | null;
    endDate: string | null;
    daysRemaining: number;
    isExpiringSoon: boolean;
    isActive: boolean;
  };
  usage: {
    acceptedThisMonth: number;
    monthlyLimit: number;
    remaining: number;
    limitReached: boolean;
    resetsOn: string;
  };
  features: {
    canAcceptInquiries: boolean;
    unlimitedInquiries: boolean;
    verifiedBadge: boolean;
    prioritySupport: boolean;
    analyticsAccess: boolean;
  };
  showExpiryWarning: boolean;
  showUpgradeCta: boolean;
}

// ==================== B2B Category Types ====================

export interface DropdownValue {
  value: string;
  label: string;
  displayOrder: number;
  isActive: boolean;
}

export interface GlobalDropdown {
  _id: string;
  key: string;
  name: string;
  description: string | null;
  values: DropdownValue[];
  isSystem: boolean;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface CategorySettings {
  allowedUnits: string[];
  defaultUnit: string;
  allowedSellerTypes: string[];
  dimensionsEnabled: boolean;
  dimensionUnits: string[];
  dimensionFormat: 'LxW' | 'LxWxH' | null;
  dropdownOverrides: Record<string, {
    enabled: boolean;
    values?: DropdownValue[];
    isMandatory: boolean;
    restrictToValues?: string[];
  }>;
}

export interface B2BCategory {
  _id: string;
  name: string;
  description: string | null;
  image: string | null;
  icon: string | null;
  displayOrder: number;
  settings?: CategorySettings;
  isActive: boolean;
  productCount?: number;
  specTemplateCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface SpecFieldDefinition {
  key: string;
  label: string;
  fieldType: 'text' | 'number' | 'dropdown' | 'boolean' | 'range';
  unit?: string;
  isMandatory: boolean;
  isSellerEditable: boolean;
  isLockedAfterCreate: boolean;
  displayOrder: number;
  dropdownKey?: string;
  options?: string[];
  minValue?: number;
  maxValue?: number;
  placeholder?: string;
  helpText?: string;
  resolvedOptions?: string[];
  resolvedValues?: string[];
}

export interface B2BSpecTemplate {
  _id: string;
  name: string;
  categoryId: string;
  categoryName?: string;
  description?: string;
  fields: SpecFieldDefinition[];
  version: number;
  isActive: boolean;
  productCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

// ==================== Manufacturer Types ====================

export interface Manufacturer {
  _id: string;
  brandName?: string;
  legalName?: string;
  logoUrl?: string;
  country?: string;
  categories?: string[];
  status: string;
}

// ==================== Seller Stats ====================

export interface SellerStats {
   totalListings: number;
  publishedListings: number;
  totalEnquiries: number;
  pendingEnquiries: number;
  thisMonthEnquiries: number;
  subscription?: {
    plan: string;
    isUnlimited: boolean;
    usageDisplay: string;
    remaining: number;
  };
}

// ==================== Analytics Types ====================

export interface AdminAnalytics {
  periodDays: number;
  leadsPerDay: Array<{
    date: string;
    total: number;
    accepted: number;
    rejected: number;
    pending: number;
  }>;
  rates: {
    totalInquiries: number;
    accepted: number;
    rejected: number;
    approvalRate: number;
    rejectionRate: number;
  };
  topProducts: Array<{
    productName: string;
    inquiryCount: number;
    acceptedCount: number;
    conversionRate: number;
  }>;
  topSellers: Array<{
    sellerId: string;
    sellerName: string;
    subscriptionPlan: string;
    inquiryCount: number;
    acceptedCount: number;
    rejectedCount: number;
    rejectionRatio: number;
  }>;
  fraudMonitoring: {
    highRejectionSellers: Array<{
      sellerId: string;
      seller: { name: string; email: string } | null;
      totalInquiries: number;
      rejectedCount: number;
      rejectionRatio: number;
    }>;
    potentialSpamBuyers: Array<{
      buyerId: string;
      buyer: { name: string; email: string } | null;
      date: string;
      inquiryCount: number;
    }>;
  };
}

export interface AdminKPIMetrics {
  sellerOverview: {
    totalSellers: number;
    proSellers: number;
    trialSellers: number;
    freeSellers: number;
    conversionRate: number;
  };
  subscriptionHealth: {
    renewalsThisQuarter: number;
    expiredSubscriptions: number;
    churnRate: number;
    expiringSoon: number;
  };
  monetizationSignals: {
    freeSellersAtLimit: number;
    limitExhaustionRate: number;
    freeMonthlyLimit: number;
  };
  revenue: {
    quarterlyPrice: number;
    estimatedQuarterlyRevenue: number;
    currency: string;
  };
  growthTrends: Array<{
    month: string;
    totalSellers: number;
    proSellers: number;
    freeSellers: number;
    inquiries: number;
    revenue: number;
  }>;
  insights: Array<{
    type: 'positive' | 'neutral' | 'warning';
    message: string;
  }>;
  generatedAt: string;
}

// ==================== Request Types ====================

export interface SellerRequest {
  _id: string;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
  updatedAt: string;
  reviewedAt?: string;
  adminNotes?: string;
}
