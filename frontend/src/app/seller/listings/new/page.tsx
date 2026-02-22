'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getAllCategories,
  getProductsByCategory,
  getCategorySpecTemplate,
  createSellerListing,
  uploadProductImages,
  uploadProductDatasheet,
  requestProduct,
  requestCategory,
  requestSpecField,
  Category,
  AdminProduct,
  B2BSpecTemplate,
  ListingCreatePayload,
  PricingTierCreate
} from '@/lib/api';
import { 
  ArrowLeft, 
  ChevronRight, 
  Loader2, 
  AlertCircle, 
  Check, 
  Package,
  Plus,
  Info,
  Upload,
  X,
  DollarSign,
  Layers,
  FileText,
  Clock,
  HelpCircle,
  Send
} from 'lucide-react';
import Link from 'next/link';
import {
  getProductById,
  getSpecTemplateById
} from '@/lib/api';


// ==================== Types (FINAL ARCHITECTURE - camelCase, flat) ====================

interface AttributeValue {
  value: string | number | boolean;
  touched: boolean;
}

interface FormState {
  // Step 1: Product Selection
  categoryId: string;
  productId: string;
  sellerRole: string;
  
  // Step 2: Attributes (NOT specifications)
  attributes: Record<string, AttributeValue>;
  description: string;
  
  // Step 3: Commercial Terms (FLAT - NOT nested in availability/pricing)
  moq: number;
  stock: number;
  maxCapacity: number | null;
  leadTime: number | null;
  currency: string;
  
  // Pricing Tiers (NOT pricing.slabs)
  pricingTiers: PricingTierCreate[];
  
  // Images
  images: string[];
  datasheetUrl: string;
}

const initialFormState: FormState = {
  categoryId: '',
  productId: '',
  sellerRole: 'distributor',
  attributes: {},
  description: '',
  moq: 1,
  stock: 0,
  maxCapacity: null,
  leadTime: null,
  currency: 'INR',
  pricingTiers: [{ minQty: 1, maxQty: null, pricePerUnit: 0 }],
  images: [],
  datasheetUrl: ''
};

// ==================== Request Modals ====================

function RequestProductModal({ 
  categoryId, 
  categoryName,
  onClose, 
  onSuccess, 
  token 
}: { 
  categoryId: string;
  categoryName: string;
  onClose: () => void;
  onSuccess: () => void;
  token: string;
}) {
  const [productName, setProductName] = useState('');
  const [description, setDescription] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) {
      setError('Product name is required');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await requestProduct(token, {
        productName: productName.trim(),
        suggestedCategoryId: categoryId,
        description: description.trim() || undefined,
        reason: reason.trim() || undefined
      });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl">
        <div className="p-6 border-b flex items-center justify-between">
          <h3 className="text-lg font-semibold">Request New Product</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
            <Info className="h-4 w-4 inline mr-2" />
            Requesting for category: <strong>{categoryName}</strong>
          </div>
          
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Product Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g., Industrial AC Motor 3HP"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="request-product-name"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the product"
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Why do you need this product?
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Help us understand your need"
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              data-testid="submit-product-request"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Submit Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RequestCategoryModal({ 
  onClose, 
  onSuccess, 
  token 
}: { 
  onClose: () => void;
  onSuccess: () => void;
  token: string;
}) {
  const [categoryName, setCategoryName] = useState('');
  const [description, setDescription] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryName.trim()) {
      setError('Category name is required');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await requestCategory(token, {
        categoryName: categoryName.trim(),
        description: description.trim() || undefined,
        reason: reason.trim() || undefined
      });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl">
        <div className="p-6 border-b flex items-center justify-between">
          <h3 className="text-lg font-semibold">Request New Category</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={categoryName}
              onChange={(e) => setCategoryName(e.target.value)}
              placeholder="e.g., Industrial Automation"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="request-category-name"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What products would this category contain?"
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Why do you need this category?
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Help us understand your need"
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              data-testid="submit-category-request"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Submit Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RequestSpecFieldModal({ 
  categoryId,
  categoryName,
  onClose, 
  onSuccess, 
  token 
}: { 
  categoryId: string;
  categoryName: string;
  onClose: () => void;
  onSuccess: () => void;
  token: string;
}) {
  const [fieldName, setFieldName] = useState('');
  const [fieldType, setFieldType] = useState<'text' | 'number' | 'dropdown' | 'boolean'>('text');
  const [unit, setUnit] = useState('');
  const [options, setOptions] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fieldName.trim()) {
      setError('Field name is required');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await requestSpecField(token, {
        categoryId: categoryId,
        fieldName: fieldName.trim(),
        fieldType: fieldType,
        unit: unit.trim() || undefined,
        suggestedOptions: fieldType === 'dropdown' ? options.split(',').map(o => o.trim()).filter(Boolean) : undefined,
        reason: reason.trim() || undefined
      });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl">
        <div className="p-6 border-b flex items-center justify-between">
          <h3 className="text-lg font-semibold">Request New Attribute Field</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
            <Info className="h-4 w-4 inline mr-2" />
            Adding field to category: <strong>{categoryName}</strong>
          </div>
          
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Field Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              placeholder="e.g., Rated Voltage"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="request-field-name"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Field Type
              </label>
              <select
                value={fieldType}
                onChange={(e) => setFieldType(e.target.value as typeof fieldType)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="text">Text</option>
                <option value="number">Number</option>
                <option value="dropdown">Dropdown</option>
                <option value="boolean">Yes/No</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Unit (optional)
              </label>
              <input
                type="text"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                placeholder="e.g., V, HP, kW"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          
          {fieldType === 'dropdown' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Options (comma-separated)
              </label>
              <input
                type="text"
                value={options}
                onChange={(e) => setOptions(e.target.value)}
                placeholder="e.g., 220V, 380V, 440V"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Why do you need this field?
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Help us understand your need"
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              data-testid="submit-spec-field-request"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Submit Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==================== Success Toast ====================

function SuccessToast({ message, onClose }: { message: string; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="fixed top-4 right-4 z-50 animate-in fade-in slide-in-from-top-2">
      <div className="bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3">
        <Check className="h-5 w-5" />
        <span>{message}</span>
        <button onClick={onClose} className="p-1 hover:bg-green-700 rounded">
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ==================== Main Component ====================

export default function NewSellerListingPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  // Data states
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [specTemplate, setSpecTemplate] = useState<B2BSpecTemplate | null>(null);
  const [categorySettings, setCategorySettings] = useState<{ allowedSellerTypes?: string[] } | null>(null);
  
  // Loading states
  const [loading, setLoading] = useState(true);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [loadingSpecs, setLoadingSpecs] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingImages, setUploadingImages] = useState(false);
  const [uploadingDatasheet, setUploadingDatasheet] = useState(false);
  
  // UI states
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  
  // Form state (FINAL ARCHITECTURE)
  const [form, setForm] = useState<FormState>(initialFormState);
  
  // Modal states
  const [showRequestProduct, setShowRequestProduct] = useState(false);
  const [showRequestCategory, setShowRequestCategory] = useState(false);
  const [showRequestSpecField, setShowRequestSpecField] = useState(false);

  // Token ref
  const [token, setToken] = useState<string | null>(null);

  // Load categories on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const authToken = await getIdToken();
        if (!authToken) {
          router.push('/login');
          return;
        }
        setToken(authToken);
        
        const cats = await getAllCategories();
        setCategories(cats.filter(c => c.isActive !== false));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadData();
      }
    }
  }, [user, authLoading, getIdToken, router]);

  // Load products when category changes
  const loadProducts = useCallback(async (categoryId: string) => {
    if (!categoryId || !token) return;
    
    setLoadingProducts(true);
    setProducts([]);
    setForm(prev => ({ ...prev, productId: '' }));
    
    try {
      const prods = await getProductsByCategory(categoryId);
      setProducts(prods || []);
      
      // Load category settings
      const templateData = await getCategorySpecTemplate(token, categoryId);
      setCategorySettings(templateData.category?.settings || null);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setLoadingProducts(false);
    }
  }, [token]);

  // Load spec template when product changes
  const loadSpecTemplateByProduct = useCallback(
  async (productId: string) => {
    if (!productId || !token) return;

    setLoadingSpecs(true);

    try {
      // 1️⃣ Fetch product
      const product = await getProductById(productId);

      // 2️⃣ Get template ID (first one for now)
      const templateId =
        product.specTemplateId ||
        (product.specTemplateIds && product.specTemplateIds[0]);

      if (!templateId) {
        setSpecTemplate(null);
        return;
      }

      // 3️⃣ Fetch template
      const template = await getSpecTemplateById(token, templateId);

      setSpecTemplate(template);

      // 4️⃣ Initialize attributes
      if (template?.fields) {
        const attrs: Record<string, { value: any; touched: boolean }> = {};

        template.fields.forEach((field: any) => {
          attrs[field.key] = {
            value:
              field.fieldType === 'boolean'
                ? false
                : '',
            touched: false
          };
        });

        setForm(prev => ({
          ...prev,
          attributes: attrs
        }));
      }
    } catch (err) {
      console.error('Failed to load spec template:', err);
      setSpecTemplate(null);
    } finally {
      setLoadingSpecs(false);
    }
  },
  [token]
);


  // Handle category change
  const handleCategoryChange = (categoryId: string) => {
    setForm(prev => ({ 
      ...prev, 
      categoryId, 
      productId: '',
      attributes: {} 
    }));
    setSpecTemplate(null);
    if (categoryId) {
      loadProducts(categoryId);
    }
  };

  // Handle product selection
 const handleProductSelect = (productId: string) => {
  setForm(prev => ({
    ...prev,
    productId,
    attributes: {}
  }));

  setSpecTemplate(null);

  if (productId) {
    loadSpecTemplateByProduct(productId);
  }
};


  // Handle attribute change (NOT specification)
  const handleAttributeChange = (key: string, value: string | number | boolean) => {
    setForm(prev => ({
      ...prev,
      attributes: {
        ...prev.attributes,
        [key]: { value, touched: true }
      }
    }));
  };

  // Handle image upload
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !token) return;
    
    if (form.images.length + files.length > 5) {
      setError('Maximum 5 images allowed');
      return;
    }
    
    setUploadingImages(true);
    setError(null);
    
    try {
      const result = await uploadProductImages(token, Array.from(files));
      setForm(prev => ({
        ...prev,
        images: [...prev.images, ...result.images]
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload images');
    } finally {
      setUploadingImages(false);
    }
  };

  // Remove image
  const removeImage = (index: number) => {
    setForm(prev => ({
      ...prev,
      images: prev.images.filter((_, i) => i !== index)
    }));
  };

  // Handle datasheet upload
  const handleDatasheetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed for datasheets');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      setError('Datasheet file must be less than 10MB');
      return;
    }
    
    setUploadingDatasheet(true);
    setError(null);
    
    try {
      const result = await uploadProductDatasheet(token, file);
      setForm(prev => ({
        ...prev,
        datasheetUrl: result.url
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload datasheet');
    } finally {
      setUploadingDatasheet(false);
    }
  };

  // Remove datasheet
  const removeDatasheet = () => {
    setForm(prev => ({ ...prev, datasheetUrl: '' }));
  };

  // Add pricing tier (TypeScript-safe)
const addPricingTier = () => {
  // Safety: ensure array exists and has at least one tier
  if (!form.pricingTiers || form.pricingTiers.length === 0) {
    setForm(prev => ({
      ...prev,
      pricingTiers: [{ minQty: 1, maxQty: null, pricePerUnit: 0 }]
    }));
    return;
  }

  // Max 10 tiers
  if (form.pricingTiers.length >= 10) return;

  const lastTier = form.pricingTiers[form.pricingTiers.length - 1];
  if (!lastTier) return;

  // Use nullish coalescing for safety (enterprise correct)
  const baseQty: number = 
  (lastTier.maxQty ?? lastTier.minQty) ?? 1;

  const newMinQty = baseQty + 1;

  setForm(prev => ({
    ...prev,
    pricingTiers: [
      ...prev.pricingTiers.slice(0, -1),
      { ...lastTier, maxQty: newMinQty - 1 },
      { minQty: newMinQty, maxQty: null, pricePerUnit: 0 }
    ]
  }));
};

  // Remove pricing tier
  const removePricingTier = (index: number) => {
    if (form.pricingTiers.length <= 1) return;
    setForm(prev => ({
      ...prev,
      pricingTiers: prev.pricingTiers.filter((_, i) => i !== index)
    }));
  };

  // Update pricing tier (camelCase fields)
  const updatePricingTier = (index: number, field: keyof PricingTierCreate, value: number | null) => {
    setForm(prev => ({
      ...prev,
      pricingTiers: prev.pricingTiers.map((tier, i) => 
        i === index ? { ...tier, [field]: value } : tier
      )
    }));
  };

  // Validate form
  const validateForm = (): string | null => {
    if (!form.categoryId) return 'Please select a category';
    if (!form.productId) return 'Please select a product';
    if (!form.sellerRole) return 'Please select your seller role';
    if (form.moq < 1) return 'MOQ must be at least 1';
    
    if (form.images.length === 0) {
      return 'Please upload at least 1 product image';
    }
    
    if (form.images.length > 5) {
      return 'Maximum 5 images allowed';
    }
    
    // Check mandatory attribute fields
    if (specTemplate?.fields) {
      for (const field of specTemplate.fields) {
        const isMandatory = field.isMandatory === true;
        if (isMandatory) {
          const attr = form.attributes[field.key];
          if (!attr || attr.value === '' || attr.value === null || attr.value === undefined) {
            return `${field.label} is required`;
          }
        }
      }
    }
    
    // Validate pricing tiers
    for (const tier of form.pricingTiers) {
      if (tier.pricePerUnit <= 0) {
        return 'All pricing tiers must have a price greater than 0';
      }
    }
    
    return null;
  };

  // Submit form - FINAL ARCHITECTURE PAYLOAD
  const handleSubmit = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }
    
    if (!token) return;
    
    setSubmitting(true);
    setError(null);
    
    try {
      // Build attributes object (values only, NOT specifications)
      const attributes: Record<string, string | number | boolean> = {};
      Object.entries(form.attributes).forEach(([key, val]) => {
        if (val.value !== '' && val.value !== null && val.value !== undefined) {
          attributes[key] = val.value;
        }
      });
      
      // Build FINAL ARCHITECTURE payload - camelCase, flat structure
      const payload: ListingCreatePayload = {
        productId: form.productId,
        attributes: attributes,
        sellerRole: form.sellerRole,
        description: form.description || undefined,
        images: form.images,
        moq: form.moq,
        stock: form.stock,
        maxCapacity: form.maxCapacity || undefined,
        leadTime: form.leadTime || undefined,
        currency: form.currency,
        pricingTiers: form.pricingTiers,
        datasheetUrl: form.datasheetUrl || undefined
      };
      
      await createSellerListing(token, payload);
      
      // Success - redirect to listings
      router.push('/seller/listings?created=true');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create listing');
    } finally {
      setSubmitting(false);
    }
  };

  // Get selected category name
  const selectedCategory = categories.find(c => c._id === form.categoryId);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Success Toast */}
      {successToast && (
        <SuccessToast message={successToast} onClose={() => setSuccessToast(null)} />
      )}
      
      {/* Request Modals */}
      {showRequestProduct && token && form.categoryId && selectedCategory && (
        <RequestProductModal
          categoryId={form.categoryId}
          categoryName={selectedCategory.name}
          token={token}
          onClose={() => setShowRequestProduct(false)}
          onSuccess={() => {
            setShowRequestProduct(false);
            setSuccessToast('Product request submitted! Admin will review it soon.');
          }}
        />
      )}
      
      {showRequestCategory && token && (
        <RequestCategoryModal
          token={token}
          onClose={() => setShowRequestCategory(false)}
          onSuccess={() => {
            setShowRequestCategory(false);
            setSuccessToast('Category request submitted! Admin will review it soon.');
          }}
        />
      )}
      
      {showRequestSpecField && token && form.categoryId && selectedCategory && (
        <RequestSpecFieldModal
          categoryId={form.categoryId}
          categoryName={selectedCategory.name}
          token={token}
          onClose={() => setShowRequestSpecField(false)}
          onSuccess={() => {
            setShowRequestSpecField(false);
            setSuccessToast('Attribute field request submitted!');
          }}
        />
      )}

      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/seller/listings" className="p-2 hover:bg-gray-100 rounded-lg">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">New Listing</h1>
              <p className="text-sm text-gray-500">Create a new product listing</p>
            </div>
          </div>
          
          {/* Progress Steps */}
          <div className="flex items-center gap-2 mt-4">
            {[
              { num: 1, label: 'Product' },
              { num: 2, label: 'Attributes' },
              { num: 3, label: 'Commercial' }
            ].map((step, idx) => (
              <div key={step.num} className="flex items-center">
                <button
                  onClick={() => setCurrentStep(step.num)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition ${
                    currentStep === step.num
                      ? 'bg-blue-600 text-white'
                      : currentStep > step.num
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                  data-testid={`step-${step.num}`}
                >
                  {currentStep > step.num ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span className="w-5 h-5 flex items-center justify-center">{step.num}</span>
                  )}
                  {step.label}
                </button>
                {idx < 2 && <ChevronRight className="h-4 w-4 text-gray-400 mx-1" />}
              </div>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-700">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Step 1: Product Selection */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Package className="h-5 w-5 text-blue-600" />
                Select Product
              </h2>
              
              {/* Category Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <select
                    value={form.categoryId}
                    onChange={(e) => handleCategoryChange(e.target.value)}
                    className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    data-testid="category-select"
                  >
                    <option value="">Select a category</option>
                    {categories.map(cat => (
                      <option key={cat._id} value={cat._id}>{cat.name}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setShowRequestCategory(true)}
                    className="px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg whitespace-nowrap"
                    data-testid="request-category-btn"
                  >
                    + Request New
                  </button>
                </div>
              </div>
              
              {/* Product Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Product <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <select
                      value={form.productId}
                      onChange={(e) => handleProductSelect(e.target.value)}
                      disabled={!form.categoryId || loadingProducts}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white disabled:bg-gray-100"
                      data-testid="product-select"
                    >
                      <option value="">
                        {!form.categoryId 
                          ? 'Select a category first'
                          : loadingProducts 
                          ? 'Loading products...'
                          : products.length === 0
                          ? 'No products in this category'
                          : 'Select a product'}
                      </option>
                      {products.map(prod => (
                        <option key={prod._id} value={prod._id}>{prod.name}</option>
                      ))}
                    </select>
                    {loadingProducts && (
                      <Loader2 className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-gray-400" />
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowRequestProduct(true)}
                    disabled={!form.categoryId}
                    className="px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg whitespace-nowrap disabled:opacity-50"
                    data-testid="request-product-btn"
                  >
                    + Request New
                  </button>
                </div>
                {form.productId && (
                  <p className="mt-2 text-sm text-gray-500 flex items-center gap-1">
                    <Info className="h-4 w-4" />
                    Product selection is locked after creation
                  </p>
                )}
              </div>
              
              {/* Seller Role (camelCase) */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Seller Role <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.sellerRole}
                  onChange={(e) => setForm(prev => ({ ...prev, sellerRole: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                  data-testid="seller-role-select"
                >
                  {(categorySettings?.allowedSellerTypes || ['manufacturer', 'distributor', 'dealer', 'trader']).map(type => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Navigation */}
            <div className="flex justify-end">
              <button
                onClick={() => setCurrentStep(2)}
                disabled={!form.productId}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                data-testid="next-step-1"
              >
                Continue to Attributes
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Attributes (NOT Specifications) */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Layers className="h-5 w-5 text-purple-600" />
                  Product Attributes
                </h2>
                <button
                  type="button"
                  onClick={() => setShowRequestSpecField(true)}
                  disabled={!form.categoryId}
                  className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-lg"
                  data-testid="request-spec-field-btn"
                >
                  + Request Field
                </button>
              </div>
              
              {loadingSpecs ? (
                <div className="py-12 text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto" />
                  <p className="text-gray-500 mt-2">Loading attributes...</p>
                </div>
              ) : specTemplate?.fields && specTemplate.fields.length > 0 ? (
                <div className="space-y-4">
                  {specTemplate.fields.map(field => {
                    const isMandatory = field.isMandatory === true;
                    
                    return (
                    <div key={field.key}>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {field.label}
                        {isMandatory && <span className="text-red-500 ml-1">*</span>}
                        {field.unit && <span className="text-gray-400 font-normal ml-1">({field.unit})</span>}
                      </label>
                      
                      {field.fieldType === 'dropdown' && field.options ? (
                        <select
                          value={String(form.attributes[field.key]?.value || '')}
                          onChange={(e) => handleAttributeChange(field.key, e.target.value)}
                          className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 bg-white border-gray-300"
                          data-testid={`attr-${field.key}`}
                          required={isMandatory}
                        >
                          <option value="">Select {field.label}{isMandatory ? ' (Required)' : ''}</option>
                          {field.options.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : field.fieldType === 'boolean' ? (
                        <div className="flex gap-4">
                          <label className="flex items-center gap-2">
                            <input
                              type="radio"
                              checked={form.attributes[field.key]?.value === true}
                              onChange={() => handleAttributeChange(field.key, true)}
                              className="h-4 w-4 text-blue-600"
                            />
                            Yes
                          </label>
                          <label className="flex items-center gap-2">
                            <input
                              type="radio"
                              checked={form.attributes[field.key]?.value === false}
                              onChange={() => handleAttributeChange(field.key, false)}
                              className="h-4 w-4 text-blue-600"
                            />
                            No
                          </label>
                        </div>
                      ) : field.fieldType === 'number' ? (
                        <input
                          type="number"
                          value={form.attributes[field.key]?.value as number || ''}
                          onChange={(e) => handleAttributeChange(field.key, parseFloat(e.target.value) || 0)}
                          placeholder={field.placeholder || `Enter ${field.label}`}
                          min={field.minValue}
                          max={field.maxValue}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          data-testid={`attr-${field.key}`}
                        />
                      ) : (
                        <input
                          type="text"
                          value={String(form.attributes[field.key]?.value || '')}
                          onChange={(e) => handleAttributeChange(field.key, e.target.value)}
                          placeholder={field.placeholder || `Enter ${field.label}`}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          data-testid={`attr-${field.key}`}
                        />
                      )}
                      
                      {field.helpText && (
                        <p className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                          <HelpCircle className="h-3 w-3" />
                          {field.helpText}
                        </p>
                      )}
                    </div>
                  );
                  })}
                </div>
              ) : (
                <div className="py-8 text-center text-gray-500">
                  <FileText className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                  <p>No attribute template for this category.</p>
                  <p className="text-sm">You can add a description below.</p>
                </div>
              )}
              
              {/* Description */}
              <div className="mt-6 pt-6 border-t">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Additional Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Add any additional details about your product..."
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  data-testid="description-input"
                />
              </div>
            </div>
            
            {/* Navigation */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(1)}
                className="px-6 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                onClick={() => setCurrentStep(3)}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                data-testid="next-step-2"
              >
                Continue to Commercial Terms
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Commercial Terms (FLAT fields) */}
        {currentStep === 3 && (
          <div className="space-y-6">
            {/* Images */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Upload className="h-5 w-5 text-green-600" />
                Product Images <span className="text-red-500">*</span>
              </h2>
              <p className="text-sm text-gray-500 mb-4">Upload at least 1 image (maximum 5). First image will be the main product image.</p>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 mb-4">
                {form.images.map((img, idx) => (
                  <div key={idx} className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 group">
                    <img src={img} alt={`Product ${idx + 1}`} className="w-full h-full object-cover" />
                    {idx === 0 && (
                      <span className="absolute top-2 left-2 px-2 py-0.5 bg-blue-600 text-white text-xs rounded">Main</span>
                    )}
                    <button
                      type="button"
                      onClick={() => removeImage(idx)}
                      className="absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
                
                {form.images.length < 5 && (
                  <label className={`aspect-square rounded-lg border-2 border-dashed cursor-pointer flex flex-col items-center justify-center transition ${
                    form.images.length === 0 ? 'border-red-300 hover:border-red-500 bg-red-50' : 'border-gray-300 hover:border-blue-500'
                  }`}>
                    {uploadingImages ? (
                      <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                    ) : (
                      <>
                        <Plus className={`h-8 w-8 ${form.images.length === 0 ? 'text-red-400' : 'text-gray-400'}`} />
                        <span className={`text-xs mt-1 ${form.images.length === 0 ? 'text-red-500' : 'text-gray-500'}`}>
                          {form.images.length === 0 ? 'Required' : 'Add Image'}
                        </span>
                      </>
                    )}
                    <input
                      type="file"
                      accept="image/jpeg,image/jpg,image/png,image/webp,image/heic,image/heif"
                      multiple
                      onChange={handleImageUpload}
                      className="hidden"
                      data-testid="image-upload"
                    />
                  </label>
                )}
              </div>
              
              <p className={`text-sm ${form.images.length === 0 ? 'text-red-500' : 'text-gray-500'}`}>
                {form.images.length}/5 images uploaded {form.images.length === 0 && '(minimum 1 required)'}
              </p>
            </div>

            {/* Availability - FLAT fields */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Clock className="h-5 w-5 text-orange-600" />
                Availability & Lead Time
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Minimum Order Quantity (MOQ) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={form.moq}
                    onChange={(e) => setForm(prev => ({ ...prev, moq: parseInt(e.target.value) || 1 }))}
                    min={1}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="moq-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stock Quantity
                  </label>
                  <input
                    type="number"
                    value={form.stock}
                    onChange={(e) => setForm(prev => ({ ...prev, stock: parseInt(e.target.value) || 0 }))}
                    min={0}
                    placeholder="0"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="stock-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Maximum Capacity (per order)
                  </label>
                  <input
                    type="number"
                    value={form.maxCapacity || ''}
                    onChange={(e) => setForm(prev => ({ ...prev, maxCapacity: parseInt(e.target.value) || null }))}
                    min={1}
                    placeholder="Unlimited"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="max-capacity-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Lead Time (Days)
                  </label>
                  <input
                    type="number"
                    value={form.leadTime || ''}
                    onChange={(e) => setForm(prev => ({ ...prev, leadTime: parseInt(e.target.value) || null }))}
                    min={0}
                    placeholder="e.g., 7"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="lead-time-input"
                  />
                </div>
              </div>
            </div>

            {/* Pricing Tiers (NOT pricing.slabs) */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-emerald-600" />
                Pricing Tiers <span className="text-red-500">*</span>
              </h2>
              
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-gray-700">
                    Quantity-based Pricing
                  </label>
                  {form.pricingTiers.length < 10 && (
                    <button
                      type="button"
                      onClick={addPricingTier}
                      className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1 rounded-lg"
                      data-testid="add-pricing-tier"
                    >
                      + Add Tier
                    </button>
                  )}
                </div>
                
                <div className="space-y-3">
                  {form.pricingTiers.map((tier, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1 grid grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Min Qty</label>
                          <input
                            type="number"
                            value={tier.minQty}
                            onChange={(e) => updatePricingTier(idx, 'minQty', parseInt(e.target.value) || 1)}
                            min={1}
                            className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                            data-testid={`tier-min-qty-${idx}`}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Max Qty</label>
                          <input
                            type="number"
                            value={tier.maxQty || ''}
                            onChange={(e) => updatePricingTier(idx, 'maxQty', parseInt(e.target.value) || null)}
                            placeholder="∞"
                            className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                            data-testid={`tier-max-qty-${idx}`}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Price/Unit (₹)</label>
                          <input
                            type="number"
                            value={tier.pricePerUnit || ''}
                            onChange={(e) => updatePricingTier(idx, 'pricePerUnit', parseFloat(e.target.value) || 0)}
                            min={0}
                            step={0.01}
                            className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                            data-testid={`tier-price-${idx}`}
                          />
                        </div>
                      </div>
                      {form.pricingTiers.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removePricingTier(idx)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                          data-testid={`remove-tier-${idx}`}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Datasheet */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5 text-gray-600" />
                Datasheet (Optional)
              </h2>
              
              {form.datasheetUrl ? (
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                  <FileText className="h-8 w-8 text-blue-600" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">Datasheet uploaded</p>
                    <a 
                      href={form.datasheetUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      View file
                    </a>
                  </div>
                  <button
                    type="button"
                    onClick={removeDatasheet}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 transition">
                  {uploadingDatasheet ? (
                    <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-gray-400 mb-2" />
                      <p className="text-sm text-gray-500">Click to upload datasheet (PDF)</p>
                      <p className="text-xs text-gray-400 mt-1">Max 10MB</p>
                    </>
                  )}
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={handleDatasheetUpload}
                    className="hidden"
                    data-testid="datasheet-upload"
                  />
                </label>
              )}
            </div>
            
            {/* Navigation */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(2)}
                className="px-6 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-8 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                data-testid="submit-listing"
              >
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Create Listing
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
