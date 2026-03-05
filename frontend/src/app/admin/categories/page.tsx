'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import type { B2BCategory, CategorySettings, GlobalDropdown } from '@/types';
import { 
  getB2BCategories, 
  createB2BCategory, 
  updateB2BCategory,
  getGlobalDropdowns,
  uploadCategoryImage
} from '@/lib/api';
import ImageUpload from '@/components/ImageUpload';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  Loader2, 
  X, 
  Check, 
  AlertTriangle, 
  Eye, 
  EyeOff,
  Settings,
  ChevronRight,
  Ruler,
  Users,
  Package
} from 'lucide-react';

export default function CategoriesPage() {
  const { getIdToken } = useAuth();
  const [categories, setCategories] = useState<B2BCategory[]>([]);
  const [globalDropdowns, setGlobalDropdowns] = useState<GlobalDropdown[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'basic' | 'settings'>('basic');
  const [editingCategory, setEditingCategory] = useState<B2BCategory | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    image: '',
    icon: '',
    displayOrder: 0,
    categoryType: 'standard' as 'standard' | 'raw_material'
  });
  
  const [settingsData, setSettingsData] = useState<CategorySettings>({
    allowedUnits: ['pcs'],
    defaultUnit: 'pcs',
    allowedSellerTypes: ['manufacturer', 'distributor', 'dealer'],
    dimensionsEnabled: false,
    dimensionUnits: ['mm', 'cm'],
    dimensionFormat: null,
    dropdownOverrides: {}
  });

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const [catResult, dropdownResult] = await Promise.all([
        getB2BCategories(token, showInactive),
        getGlobalDropdowns(token, { includeSystem: true })
      ]);
      
      setCategories(catResult.categories);
      setGlobalDropdowns(dropdownResult.dropdowns);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  }, [getIdToken, showInactive]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Get dropdown values by key
  const getDropdownValues = (key: string) => {
    const dropdown = globalDropdowns.find(d => d.key === key);
    return dropdown?.values || [];
  };

  const openCreateModal = () => {
    setEditingCategory(null);
    setModalMode('basic');
    setFormData({
      name: '',
      description: '',
      image: '',
      icon: '',
      displayOrder: categories.length,
      categoryType: 'standard'
    });
    setSettingsData({
      allowedUnits: ['pcs'],
      defaultUnit: 'pcs',
      allowedSellerTypes: ['manufacturer', 'distributor', 'dealer'],
      dimensionsEnabled: false,
      dimensionUnits: ['mm', 'cm'],
      dimensionFormat: null,
      dropdownOverrides: {}
    });
    setShowModal(true);
    setError(null);
  };

  const openEditModal = (category: B2BCategory, mode: 'basic' | 'settings' = 'basic') => {
    setEditingCategory(category);
    setModalMode(mode);
    setFormData({
      name: category.name,
      description: category.description || '',
      image: category.image || '',
      icon: category.icon || '',
      displayOrder: category.displayOrder ?? 0,
      categoryType: (category as unknown as { categoryType?: string }).categoryType as 'standard' | 'raw_material' || 'standard'
    });
    setSettingsData(category.settings || {
      allowedUnits: ['pcs'],
      defaultUnit: 'pcs',
      allowedSellerTypes: ['manufacturer', 'distributor', 'dealer'],
      dimensionsEnabled: false,
      dimensionUnits: ['mm', 'cm'],
      dimensionFormat: null,
      dropdownOverrides: {}
    });
    setShowModal(true);
    setError(null);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError('Category name is required');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const payload = {
        ...formData,
        settings: settingsData
      };

      if (editingCategory) {
        await updateB2BCategory(token, editingCategory._id, payload);
      } else {
        await createB2BCategory(token, payload);
      }

      setShowModal(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (category: B2BCategory) => {
    try {
      const token = await getIdToken();
      if (!token) return;
      await updateB2BCategory(token, category._id, { isActive: !category.isActive });
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update');
    }
  };

  const toggleUnit = (unit: string) => {
    setSettingsData(prev => {
      const units = prev.allowedUnits.includes(unit)
        ? prev.allowedUnits.filter(u => u !== unit)
        : [...prev.allowedUnits, unit];
      
      // Ensure at least one unit is selected
      if (units.length === 0) return prev;
      
      // Update default if it's no longer in allowed
      const defaultUnit = units.includes(prev.defaultUnit) ? prev.defaultUnit : units[0];
      
      return { ...prev, allowedUnits: units, defaultUnit: defaultUnit };
    });
  };

  const toggleSellerType = (type: string) => {
    setSettingsData(prev => {
      const types = prev.allowedSellerTypes.includes(type)
        ? prev.allowedSellerTypes.filter(t => t !== type)
        : [...prev.allowedSellerTypes, type];
      
      // Ensure at least one type is selected
      if (types.length === 0) return prev;
      
      return { ...prev, allowedSellerTypes: types };
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
          <p className="text-gray-500">Manage product categories with B2B settings</p>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            <Plus className="h-5 w-5" /> Add Category
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" /> {error}
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {categories.map((category) => (
          <div 
            key={category._id} 
            className={`bg-white rounded-xl shadow-sm overflow-hidden ${!category.isActive ? 'opacity-60' : ''}`}
          >
            {/* Category Image/Header */}
            <div className="h-32 bg-gradient-to-r from-blue-500 to-blue-600 relative">
              {category.image && (
                <img 
                  src={category.image} 
                  alt={category.name}
                  className="w-full h-full object-cover"
                />
              )}
              <div className="absolute top-2 right-2 flex gap-1">
                {(category as unknown as { categoryType?: string }).categoryType === 'raw_material' && (
                  <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-700">
                    Raw Material
                  </span>
                )}
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  category.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {category.isActive ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
            
            {/* Category Info */}
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 mb-1">{category.name}</h3>
              {category.description && (
                <p className="text-sm text-gray-500 mb-3 line-clamp-2">{category.description}</p>
              )}
              
              {/* Stats */}
              <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                <span className="flex items-center gap-1">
                  <Package className="h-4 w-4" />
                  {category.productCount || 0} products
                </span>
                <span className="flex items-center gap-1">
                  <Settings className="h-4 w-4" />
                  {category.specTemplateCount || 0} templates
                </span>
              </div>
              
              {/* Settings Preview */}
              {category.settings && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {category.settings.allowedUnits?.slice(0, 3).map(u => (
                    <span key={u} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">
                      {u}
                    </span>
                  ))}
                  {(category.settings.allowedUnits?.length || 0) > 3 && (
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                      +{(category.settings.allowedUnits?.length || 0) - 3} more
                    </span>
                  )}
                </div>
              )}
              
              {/* Actions */}
              <div className="flex items-center justify-between pt-3 border-t">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleToggleActive(category)}
                    className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                    title={category.isActive ? 'Deactivate' : 'Activate'}
                  >
                    {category.isActive ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={() => openEditModal(category, 'basic')}
                    className="p-2 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50"
                    title="Edit"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                </div>
                <button
                  onClick={() => openEditModal(category, 'settings')}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg"
                >
                  <Settings className="h-4 w-4" />
                  Settings
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
        
        {categories.length === 0 && (
          <div className="col-span-full bg-white rounded-xl shadow-sm p-12 text-center">
            <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Categories Yet</h3>
            <p className="text-gray-600 mb-4">Create your first category to start building your product catalog.</p>
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Add Category
            </button>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="p-4 border-b flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">
                  {editingCategory ? 'Edit Category' : 'Create Category'}
                </h2>
                {editingCategory && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => setModalMode('basic')}
                      className={`px-3 py-1 text-sm rounded-lg ${
                        modalMode === 'basic' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      Basic Info
                    </button>
                    <button
                      onClick={() => setModalMode('settings')}
                      className={`px-3 py-1 text-sm rounded-lg ${
                        modalMode === 'settings' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      B2B Settings
                    </button>
                  </div>
                )}
              </div>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              {error && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" /> {error}
                </div>
              )}

              {modalMode === 'basic' ? (
                /* Basic Info Form */
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., Electrical Equipment"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      rows={3}
                      placeholder="Brief description of the category"
                    />
                  </div>
                  <div>
                    <ImageUpload
                      label="Category Image"
                      maxFiles={1}
                      maxSizeMB={1}
                      currentImages={formData.image ? [formData.image] : []}
                      onUpload={async (files) => {
                        const token = await getIdToken();
                        if (!token) throw new Error('Not authenticated');
                        const result = await uploadCategoryImage(token, files[0]);
                        setFormData({ ...formData, image: result.imageUrl });
                        return [result.imageUrl];
                      }}
                      onRemove={() => setFormData({ ...formData, image: '' })}
                      hint="JPEG, PNG, or WEBP. Max 1MB."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Icon (optional)</label>
                      <input
                        type="text"
                        value={formData.icon}
                        onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="e.g., flash-outline"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Display Order</label>
                      <input
                        type="number"
                        value={formData.displayOrder}
                        onChange={(e) => setFormData({ ...formData, displayOrder: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                  
                  {/* Category Type */}
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Category Type</label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="categoryType"
                          value="standard"
                          checked={formData.categoryType === 'standard'}
                          onChange={() => setFormData({ ...formData, categoryType: 'standard' })}
                          className="text-blue-600"
                        />
                        <span className="text-sm">Standard Products</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="categoryType"
                          value="raw_material"
                          checked={formData.categoryType === 'raw_material'}
                          onChange={() => setFormData({ ...formData, categoryType: 'raw_material' })}
                          className="text-orange-600"
                          data-testid="raw-material-category"
                        />
                        <span className="text-sm">Raw Materials (with Calculator)</span>
                      </label>
                    </div>
                    {formData.categoryType === 'raw_material' && (
                      <p className="text-xs text-orange-600 mt-2">
                        Products in this category will display the weight calculator for buyers to estimate material requirements.
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                /* B2B Settings Form */
                <div className="space-y-6">
                  {/* Unit System */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Ruler className="h-5 w-5 text-gray-600" />
                      <h3 className="font-medium text-gray-900">Unit System</h3>
                    </div>
                    <p className="text-sm text-gray-500 mb-3">Select which units sellers can use for products in this category.</p>
                    <div className="flex flex-wrap gap-2">
                      {getDropdownValues('unit_system').map(unit => (
                        <button
                          key={unit.value}
                          type="button"
                          onClick={() => toggleUnit(unit.value)}
                          className={`px-3 py-1.5 rounded-lg border text-sm transition ${
                            settingsData.allowedUnits.includes(unit.value)
                              ? 'bg-blue-50 border-blue-300 text-blue-700'
                              : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                          }`}
                        >
                          {unit.label}
                          {settingsData.defaultUnit === unit.value && (
                            <span className="ml-1 text-xs">(default)</span>
                          )}
                        </button>
                      ))}
                    </div>
                    {settingsData.allowedUnits.length > 0 && (
                      <div className="mt-3">
                        <label className="text-sm text-gray-600">Default unit:</label>
                        <select
                          value={settingsData.defaultUnit}
                          onChange={(e) => setSettingsData(prev => ({ ...prev, defaultUnit: e.target.value }))}
                          className="ml-2 px-2 py-1 border rounded text-sm"
                        >
                          {settingsData.allowedUnits.map(u => (
                            <option key={u} value={u}>{u}</option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  {/* Seller Types */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Users className="h-5 w-5 text-gray-600" />
                      <h3 className="font-medium text-gray-900">Allowed Seller Types</h3>
                    </div>
                    <p className="text-sm text-gray-500 mb-3">Which types of sellers can list products in this category.</p>
                    <div className="flex flex-wrap gap-2">
                      {getDropdownValues('seller_type').map(type => (
                        <button
                          key={type.value}
                          type="button"
                          onClick={() => toggleSellerType(type.value)}
                          className={`px-3 py-1.5 rounded-lg border text-sm transition ${
                            settingsData.allowedSellerTypes.includes(type.value)
                              ? 'bg-green-50 border-green-300 text-green-700'
                              : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                          }`}
                        >
                          {type.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Dimensions */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Ruler className="h-5 w-5 text-gray-600" />
                        <h3 className="font-medium text-gray-900">Dimensions</h3>
                      </div>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={settingsData.dimensionsEnabled}
                          onChange={(e) => setSettingsData(prev => ({ 
                            ...prev, 
                            dimensionsEnabled: e.target.checked 
                          }))}
                          className="rounded"
                        />
                        <span className="text-sm text-gray-600">Enable dimensions</span>
                      </label>
                    </div>
                    
                    {settingsData.dimensionsEnabled && (
                      <div className="ml-7 space-y-3 p-4 bg-gray-50 rounded-lg">
                        <div>
                          <label className="text-sm text-gray-600 mb-2 block">Dimension Format:</label>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => setSettingsData(prev => ({ ...prev, dimensionFormat: 'LxW' }))}
                              className={`px-3 py-1.5 rounded-lg border text-sm ${
                                settingsData.dimensionFormat === 'LxW'
                                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                                  : 'bg-white border-gray-200'
                              }`}
                            >
                              L × W (2D)
                            </button>
                            <button
                              type="button"
                              onClick={() => setSettingsData(prev => ({ ...prev, dimensionFormat: 'LxWxH' }))}
                              className={`px-3 py-1.5 rounded-lg border text-sm ${
                                settingsData.dimensionFormat === 'LxWxH'
                                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                                  : 'bg-white border-gray-200'
                              }`}
                            >
                              L × W × H (3D)
                            </button>
                          </div>
                        </div>
                        <div>
                          <label className="text-sm text-gray-600 mb-2 block">Allowed Units:</label>
                          <div className="flex flex-wrap gap-2">
                            {getDropdownValues('dimension_unit').map(unit => (
                              <button
                                key={unit.value}
                                type="button"
                                onClick={() => {
                                  setSettingsData(prev => ({
                                    ...prev,
                                    dimensionUnits: prev.dimensionUnits.includes(unit.value)
                                      ? prev.dimensionUnits.filter(u => u !== unit.value)
                                      : [...prev.dimensionUnits, unit.value]
                                  }));
                                }}
                                className={`px-3 py-1 rounded border text-sm ${
                                  settingsData.dimensionUnits.includes(unit.value)
                                    ? 'bg-blue-50 border-blue-300 text-blue-700'
                                    : 'bg-white border-gray-200'
                                }`}
                              >
                                {unit.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t bg-gray-50 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    {editingCategory ? 'Update' : 'Create'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
