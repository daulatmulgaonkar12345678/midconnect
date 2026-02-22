'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getAdminProducts, getAdminCategories, getAdminSpecTemplates, createAdminProduct, updateAdminProduct, deleteAdminProduct } from '@/lib/api';
import type { AdminProduct, Category } from '@/types';
import { uploadAdminProductImage, validateFile, formatBytes, CloudinaryError, UploadProgress } from '@/lib/cloudinary';
import { Plus, Edit2, Trash2, Loader2, X, Check, AlertTriangle, Eye, EyeOff, Search, ChevronLeft, ChevronRight, Info, Sparkles, ImagePlus, Upload } from 'lucide-react';
import Image from 'next/image';

interface SpecTemplate {
  _id: string;
  name: string;
  categoryId?: string;
  description?: string;
}

export default function ProductsPage() {
  const { getIdToken } = useAuth();
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [templates, setTemplates] = useState<SpecTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<AdminProduct | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    categoryId: '',  // SSOT: camelCase for backend
    description: '',
    family: '',
    variant: '',
    specTemplateIds: [] as string[], // SSOT: camelCase - ARRAY for multi-select
    coverImageUrl: '' // Firebase URL for cover image
  });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Cover image upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchProducts();
    fetchMeta();
  }, [page, showInactive, categoryFilter]);

  // Handle image file selection
  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      // Validate file (Cloudinary utility validates type and size)
      validateFile(file, 'adminProductImage');
      
      // Create local preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
      
      // Upload to Cloudinary
      setIsUploading(true);
      setUploadProgress(0);
      setError(null);
      
      const result = await uploadAdminProductImage(file, (progress: UploadProgress) => {
        setUploadProgress(Math.round(progress.progress));
      });
      
      // Set the Cloudinary URL (already optimized with f_auto,q_auto)
      setFormData(prev => ({ ...prev, coverImageUrl: result.url }));
      setIsUploading(false);
      setUploadProgress(100);
      
    } catch (err) {
      setIsUploading(false);
      setUploadProgress(0);
      
      if (err instanceof CloudinaryError) {
        setError(err.message);
      } else {
        setError('Failed to upload image. Please try again.');
      }
      console.error('Image upload error:', err);
    }
  };

  // Remove selected image
  const handleRemoveImage = () => {
    setFormData(prev => ({ ...prev, coverImageUrl: '' }));
    setImagePreview(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const fetchProducts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = await getIdToken();
      if (!token) {
        setError('Session expired. Please log in again.');
        setIsLoading(false);
        return;
      }
      
      const options: any = { page, limit: 20, include_inactive: showInactive };
      if (categoryFilter) options.categoryId = categoryFilter;
      if (search) options.search = search;
      
      const data = await getAdminProducts(token, options);
      setProducts(data?.products ?? []);
      setTotalPages(data?.pages ?? 1);
      setTotal(data?.total ?? 0);
    } catch (err: any) {
      if (err.status === 401) {
        setError('Session expired. Please log in again.');
      } else {
        setError(err.message || 'Failed to load products');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fetchMeta = async () => {
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const [categoriesData, templatesData] = await Promise.all([
        getAdminCategories(token),
        getAdminSpecTemplates(token)
      ]);
      
      setCategories(categoriesData.categories);
      setTemplates(templatesData.templates);
    } catch (err) {
      console.error('Failed to fetch meta:', err);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchProducts();
  };

  const openCreateModal = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      categoryId: categories[0]?._id || '',
      description: '',
      family: '',
      variant: '',
      specTemplateIds: [], // Empty array for new products
      coverImageUrl: ''
    });
    setImagePreview(null);
    setUploadProgress(0);
    setShowModal(true);
    setError(null);
  };

  const openEditModal = (product: AdminProduct) => {
    setEditingProduct(product);
    // Support both legacy single template and new array format
    // Read from camelCase or snake_case for backward compatibility
    const templateIds = product.specTemplateIds || product.specTemplateIds || 
      (product.specTemplateId ? [product.specTemplateId] : []);
    
    const existingCoverImage = product.coverImageUrl || '';
    
    setFormData({
      name: product.name,
      categoryId: product.categoryId || product.categoryId || '',
      description: product.description || '',
      family: product.family || '',
      variant: product.variant || '',
      specTemplateIds: templateIds,
      coverImageUrl: existingCoverImage
    });
    setImagePreview(existingCoverImage || null);
    setUploadProgress(existingCoverImage ? 100 : 0);
    setShowModal(true);
    setError(null);
  };

  // Toggle template selection (for multi-select)
  const toggleTemplateSelection = (templateId: string) => {
    setFormData(prev => {
      const currentIds = prev.specTemplateIds;
      if (currentIds.includes(templateId)) {
        return { ...prev, specTemplateIds: currentIds.filter(id => id !== templateId) };
      } else {
        return { ...prev, specTemplateIds: [...currentIds, templateId] };
      }
    });
  };

  // Get templates filtered by selected category
  const filteredTemplates = templates.filter(
    t => !formData.categoryId || (t.categoryId || t.categoryId) === formData.categoryId
  );

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError('Product name is required');
      return;
    }
    if (!formData.categoryId) {
      setError('Please select a category');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      if (editingProduct) {
        await updateAdminProduct(token, editingProduct._id, formData);
      } else {
        await createAdminProduct(token, formData);
      }

      setShowModal(false);
      fetchProducts();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (product: AdminProduct) => {
    try {
      const token = await getIdToken();
      if (!token) return;
      await updateAdminProduct(token, product._id, { isActive: !product.isActive });
      fetchProducts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async (product: AdminProduct) => {
    const listingCount = product.listingCount ?? 0;
    if (listingCount > 0) {
      if (!confirm(`This product has ${listingCount} active listings. Soft-delete anyway?`)) {
        return;
      }
    } else if (!confirm(`Delete product "${product.name}"?`)) {
      return;
    }

    try {
      const token = await getIdToken();
      if (!token) return;
      await deleteAdminProduct(token, product._id, true);
      fetchProducts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Products</h1>
          <p className="text-gray-500">Master product catalog</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="h-5 w-5" /> Add Product
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search products..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </form>
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat._id} value={cat._id}>{cat.name}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => { setShowInactive(e.target.checked); setPage(1); }}
              className="rounded"
            />
            Show inactive
          </label>
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">Image</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Family / Variant</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Listings</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {products.map((product) => (
                  <tr key={product._id} className={!product.isActive ? 'bg-gray-50 opacity-60' : ''} data-testid={`product-row-${product._id}`}>
                    <td className="px-4 py-3">
                      <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                        {product.coverImageUrl ? (
                          <Image
                            src={product.coverImageUrl}
                            alt={product.name}
                            width={48}
                            height={48}
                            className="object-cover w-full h-full"
                          />
                        ) : (
                          <ImagePlus className="h-5 w-5 text-gray-300" />
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-900">{product.name}</p>
                        {product.description && (
                          <p className="text-sm text-gray-500 truncate max-w-xs">{product.description}</p>
                        )}
                      </div>
                    </td>
                    <td className={`px-4 py-3 text-sm ${
                      product.categoryName?.includes('[Deleted') || product.categoryName?.includes('[No ') || product.categoryName?.includes('[Invalid')
                        ? 'text-red-600 font-medium'
                        : 'text-gray-600'
                    }`}>{product.categoryName}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {product.family && <span className="text-gray-900">{product.family}</span>}
                      {product.variant && <span className="text-gray-400"> / {product.variant}</span>}
                      {!product.family && !product.variant && '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{product.listingCount}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${product.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                        {product.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleToggleActive(product)}
                          className="p-2 text-gray-400 hover:text-gray-600 transition"
                          title={product.isActive ? 'Deactivate' : 'Activate'}
                          data-testid={`toggle-active-${product._id}`}
                        >
                          {product.isActive ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                        <button
                          onClick={() => openEditModal(product)}
                          className="p-2 text-gray-400 hover:text-blue-600 transition"
                          data-testid={`edit-product-${product._id}`}
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(product)}
                          className="p-2 text-gray-400 hover:text-red-600 transition"
                          data-testid={`delete-product-${product._id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {products.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      No products found. Create your first product.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-4 border-t">
                <p className="text-sm text-gray-500">
                  Showing {products.length} of {total} products
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Create/Edit Modal - Standardized Layout */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            
            {/* 🧠 HEADER (Fixed) */}
            <div className="flex items-center justify-between p-6 border-b flex-shrink-0">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {editingProduct ? 'Edit Product' : 'Create Product'}
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Define product structure — sellers will fill values
                </p>
              </div>
              <button 
                onClick={() => setShowModal(false)} 
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>

            {/* 📋 BODY (Scrollable) */}
            <div className="flex-1 overflow-y-auto p-6">
              {error && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" /> {error}
                </div>
              )}

              <div className="space-y-5">
                {/* Product Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Product Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., Industrial AC Motor 3HP"
                  />
                </div>
                
                {/* Category */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Category <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.categoryId}
                    onChange={(e) => setFormData({ ...formData, categoryId: e.target.value, specTemplateIds: [] })}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={!!editingProduct}
                  >
                    <option value="">Select category</option>
                    {categories.map((cat) => (
                      <option key={cat._id} value={cat._id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
                
                {/* Cover Image Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cover Image
                    <span className="text-gray-400 font-normal ml-1">(max 2MB, PNG/JPG/WEBP)</span>
                  </label>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-blue-400 transition-colors">
                    {imagePreview || formData.coverImageUrl ? (
                      <div className="relative">
                        <div className="relative w-full h-48 mx-auto rounded-lg overflow-hidden bg-gray-100">
                          <Image
                            src={imagePreview || formData.coverImageUrl}
                            alt="Cover preview"
                            fill
                            className="object-contain"
                            sizes="(max-width: 400px) 100vw, 400px"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={handleRemoveImage}
                          className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition"
                          title="Remove image"
                        >
                          <X className="h-4 w-4" />
                        </button>
                        {uploadProgress === 100 && (
                          <div className="mt-2 flex items-center justify-center text-sm text-green-600">
                            <Check className="h-4 w-4 mr-1" />
                            Image uploaded
                          </div>
                        )}
                      </div>
                    ) : isUploading ? (
                      <div className="py-6">
                        <Loader2 className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-2" />
                        <p className="text-sm text-gray-600">Uploading... {uploadProgress}%</p>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2 max-w-xs mx-auto">
                          <div 
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${uploadProgress}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <label className="cursor-pointer block py-6">
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="image/jpeg,image/jpg,image/png,image/webp"
                          onChange={handleImageSelect}
                          className="hidden"
                          data-testid="cover-image-input"
                        />
                        <ImagePlus className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-600">
                          Click to upload cover image
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          Recommended: 1200px width, WEBP format
                        </p>
                      </label>
                    )}
                  </div>
                </div>
                
                {/* Family & Variant */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Family</label>
                    <input
                      type="text"
                      value={formData.family}
                      onChange={(e) => setFormData({ ...formData, family: e.target.value })}
                      className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., Motors"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Variant</label>
                    <input
                      type="text"
                      value={formData.variant}
                      onChange={(e) => setFormData({ ...formData, variant: e.target.value })}
                      className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., 3HP Single Phase"
                    />
                  </div>
                </div>
                
                {/* Specification Templates (Multi-select) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Specification Templates
                    <span className="text-gray-400 font-normal ml-1">(select multiple)</span>
                  </label>
                  
                  <div className="border border-gray-300 rounded-lg p-3 min-h-[80px] bg-gray-50">
                    {filteredTemplates.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {filteredTemplates.map((t) => {
                          const isSelected = formData.specTemplateIds.includes(t._id);
                          return (
                            <button
                              key={t._id}
                              type="button"
                              onClick={() => toggleTemplateSelection(t._id)}
                              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                                isSelected
                                  ? 'bg-blue-600 text-white shadow-sm'
                                  : 'bg-white border border-gray-300 text-gray-700 hover:border-blue-400 hover:text-blue-600'
                              }`}
                            >
                              {isSelected && <Check className="h-3 w-3 inline mr-1" />}
                              {t.name}
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 text-center py-2">
                        {formData.categoryId 
                          ? 'No templates available for this category' 
                          : 'Select a category first'}
                      </p>
                    )}
                  </div>
                  
                  {formData.specTemplateIds.length > 0 && (
                    <p className="text-xs text-blue-600 mt-1 flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      {formData.specTemplateIds.length} template(s) selected
                    </p>
                  )}
                  
                  {/* AI Smart Tip */}
                  <div className="mt-2 p-2.5 bg-amber-50 rounded-lg border border-amber-200">
                    <p className="text-xs text-amber-700 flex items-start gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                      <span>
                        <strong>Tip:</strong> Selecting multiple templates helps buyers compare products 
                        accurately and reduces back-and-forth queries.
                      </span>
                    </p>
                  </div>
                </div>
                
                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                    placeholder="Optional product description"
                  />
                </div>
              </div>
              
              {/* Scroll hint */}
              <p className="text-xs text-gray-400 mt-4 text-center flex items-center justify-center gap-1">
                <Info className="h-3 w-3" />
                Scroll to view all fields — action buttons always visible below
              </p>
            </div>

            {/* 🧾 FOOTER (Fixed) */}
            <div className="flex gap-3 p-6 border-t bg-gray-50 flex-shrink-0">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2 font-medium"
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {editingProduct ? 'Update Product' : 'Create Product'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
