'use client';

import { useState, useEffect } from 'react';
import {
  Ruler,
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

interface UnitDefinition {
  key: string;
  label: string;
  conversion_to_base: number;
}

interface UnitGroup {
  _id?: string;
  name: string;
  display_name: string;
  base_unit: string;
  units: UnitDefinition[];
  is_active?: boolean;
}

export default function AdminUnitGroupsPage() {
  const [unitGroups, setUnitGroups] = useState<UnitGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const [isEditing, setIsEditing] = useState(false);
  const [editingGroup, setEditingGroup] = useState<UnitGroup | null>(null);
  
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/calculator/unit-groups`);
      if (res.ok) {
        setUnitGroups(await res.json());
      }
    } catch (err) {
      setError('Failed to load unit groups');
    } finally {
      setLoading(false);
    }
  };
  
  const handleNewGroup = () => {
    setEditingGroup({
      name: '',
      display_name: '',
      base_unit: '',
      units: []
    });
    setIsEditing(true);
  };
  
  const handleEditGroup = (group: UnitGroup) => {
    setEditingGroup({ ...group });
    setIsEditing(true);
  };
  
  const handleSaveGroup = async () => {
    if (!editingGroup) return;
    
    if (!editingGroup.name || !editingGroup.display_name || !editingGroup.base_unit) {
      setError('Please fill in all required fields');
      return;
    }
    
    if (editingGroup.units.length === 0) {
      setError('Please add at least one unit');
      return;
    }
    
    setSaving(true);
    setError(null);
    
    try {
      const isNew = !editingGroup._id;
      const url = isNew
        ? `${API_URL}/api/calculator/unit-groups`
        : `${API_URL}/api/calculator/unit-groups/${editingGroup._id}`;
      
      const res = await fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingGroup)
      });
      
      if (res.ok) {
        setSuccess(isNew ? 'Unit group created' : 'Unit group updated');
        setIsEditing(false);
        setEditingGroup(null);
        loadData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to save');
      }
    } catch (err) {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  };
  
  const handleAddUnit = () => {
    if (!editingGroup) return;
    
    setEditingGroup({
      ...editingGroup,
      units: [
        ...editingGroup.units,
        { key: '', label: '', conversion_to_base: 1 }
      ]
    });
  };
  
  const handleUpdateUnit = (index: number, unit: UnitDefinition) => {
    if (!editingGroup) return;
    
    const newUnits = [...editingGroup.units];
    newUnits[index] = unit;
    setEditingGroup({ ...editingGroup, units: newUnits });
  };
  
  const handleRemoveUnit = (index: number) => {
    if (!editingGroup) return;
    
    const newUnits = editingGroup.units.filter((_, i) => i !== index);
    setEditingGroup({ ...editingGroup, units: newUnits });
  };
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Unit Groups</h1>
            <p className="text-gray-600">Manage measurement units and conversions</p>
          </div>
          
          {!isEditing && (
            <button
              onClick={handleNewGroup}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              New Unit Group
            </button>
          )}
        </div>
        
        {/* Alerts */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
            <AlertCircle className="h-5 w-5" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}
        
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
            <CheckCircle className="h-5 w-5" />
            {success}
            <button onClick={() => setSuccess(null)} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}
        
        {/* Editor */}
        {isEditing && editingGroup && (
          <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">
                {editingGroup._id ? 'Edit Unit Group' : 'New Unit Group'}
              </h2>
              <button onClick={() => { setIsEditing(false); setEditingGroup(null); }} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Group Name (key) *</label>
                  <input
                    type="text"
                    value={editingGroup.name}
                    onChange={(e) => setEditingGroup({ ...editingGroup, name: e.target.value.toLowerCase().replace(/[^a-z0-9]/g, '') })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., length"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Display Name *</label>
                  <input
                    type="text"
                    value={editingGroup.display_name}
                    onChange={(e) => setEditingGroup({ ...editingGroup, display_name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., Length"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Base Unit *</label>
                  <select
                    value={editingGroup.base_unit}
                    onChange={(e) => setEditingGroup({ ...editingGroup, base_unit: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="">Select...</option>
                    {editingGroup.units.map(u => (
                      <option key={u.key} value={u.key}>{u.key} - {u.label}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">The unit with conversion factor = 1</p>
                </div>
              </div>
              
              {/* Units */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-sm font-medium">Units</label>
                  <button
                    type="button"
                    onClick={handleAddUnit}
                    className="flex items-center gap-1 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
                  >
                    <Plus className="h-4 w-4" />
                    Add Unit
                  </button>
                </div>
                
                <div className="space-y-2">
                  {editingGroup.units.length === 0 ? (
                    <div className="text-center py-6 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed">
                      No units yet. Click "Add Unit" to add measurement units.
                    </div>
                  ) : (
                    editingGroup.units.map((unit, index) => (
                      <div key={index} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                        <div className="flex-1 grid grid-cols-3 gap-3">
                          <div>
                            <label className="text-xs text-gray-500">Key</label>
                            <input
                              type="text"
                              value={unit.key}
                              onChange={(e) => handleUpdateUnit(index, { ...unit, key: e.target.value.toLowerCase() })}
                              className="w-full px-2 py-1 border rounded text-sm"
                              placeholder="e.g., mm"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-gray-500">Label</label>
                            <input
                              type="text"
                              value={unit.label}
                              onChange={(e) => handleUpdateUnit(index, { ...unit, label: e.target.value })}
                              className="w-full px-2 py-1 border rounded text-sm"
                              placeholder="e.g., Millimeter"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-gray-500">Conversion to Base</label>
                            <input
                              type="number"
                              step="any"
                              value={unit.conversion_to_base}
                              onChange={(e) => handleUpdateUnit(index, { ...unit, conversion_to_base: parseFloat(e.target.value) || 0 })}
                              className="w-full px-2 py-1 border rounded text-sm"
                              placeholder="e.g., 0.001"
                            />
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveUnit(index)}
                          className="p-1 text-red-500 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex items-center gap-3 pt-4 border-t">
                <button
                  onClick={handleSaveGroup}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  Save Unit Group
                </button>
                <button
                  onClick={() => { setIsEditing(false); setEditingGroup(null); }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* List */}
        {!isEditing && (
          <div className="bg-white rounded-xl shadow-sm border">
            <div className="p-4 border-b">
              <h2 className="font-semibold">All Unit Groups ({unitGroups.length})</h2>
            </div>
            
            {unitGroups.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Ruler className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>No unit groups yet</p>
              </div>
            ) : (
              <div className="divide-y">
                {unitGroups.map(group => (
                  <div key={group._id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium">{group.display_name}</h3>
                        <p className="text-sm text-gray-500">
                          Key: {group.name} • Base unit: {group.base_unit} • {group.units.length} units
                        </p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {group.units.map(unit => (
                            <span key={unit.key} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                              {unit.key} ({unit.conversion_to_base})
                            </span>
                          ))}
                        </div>
                      </div>
                      <button
                        onClick={() => handleEditGroup(group)}
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
