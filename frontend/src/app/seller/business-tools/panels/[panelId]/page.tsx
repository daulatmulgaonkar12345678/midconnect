'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { usePermissions } from '../../layout';
import { toast } from 'sonner';
import Link from 'next/link';
import {
  Plus, Pencil, Trash2, Eye, Loader2, X, Save, Search,
  ChevronLeft, ChevronRight, ArrowLeft, Link2, FileSpreadsheet, FileDown
} from 'lucide-react';
import { RelationField } from './RelationField';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface PanelField {
  key: string;
  label: string;
  type: string;
  required: boolean;
  options?: string[];
  relatedPanel?: string;
  relationType?: string;
  disabled?: boolean;
  order: number;
}

interface Panel {
  id: string;
  name: string;
  slug: string;
  description: string;
  color: string;
  fields: PanelField[];
}

interface RecordData {
  [key: string]: any;
}

interface PanelRecord {
  id: string;
  data: RecordData;
  _resolved?: { [key: string]: { id: string; label: string; sub?: string; sku?: string; buyerName?: string } };
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export default function PanelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const panelId = params.panelId as string;
  const { token, isAdmin, loading: permLoading } = usePermissions();

  const [panel, setPanel] = useState<Panel | null>(null);
  const [records, setRecords] = useState<PanelRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Create/Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<PanelRecord | null>(null);
  const [formData, setFormData] = useState<RecordData>({});
  const [saving, setSaving] = useState(false);

  // View modal
  const [viewRecord, setViewRecord] = useState<PanelRecord | null>(null);

  // Resolved labels for relation fields (fieldKey -> { label, sub })
  const [resolvedLabels, setResolvedLabels] = useState<{ [key: string]: { label: string; sub?: string } }>({});

  // Export states
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const headers = useCallback(() => ({
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json'
  }), [token]);

  const fetchPanel = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/business-tools/panels/${panelId}`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setPanel(data);
      } else {
        toast.error('Panel not found');
        router.push('/seller/business-tools/panels');
      }
    } catch { toast.error('Failed to load panel'); }
  }, [token, panelId, headers, router]);

  const fetchRecords = useCallback(async () => {
    if (!token || !panelId) return;
    setLoading(true);
    try {
      const q = new URLSearchParams({ page: String(page), search });
      const res = await fetch(`${API_URL}/api/business-tools/panels/${panelId}/records?${q}`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setRecords(data.records || []);
        setTotal(data.total || 0);
        setPages(data.pages || 1);
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [token, panelId, page, search, headers]);

  useEffect(() => {
    if (!permLoading && token) { fetchPanel(); fetchRecords(); }
  }, [permLoading, token, fetchPanel, fetchRecords]);

  const activeFields = panel?.fields.filter(f => !f.disabled) || [];

  const openCreate = () => {
    setEditingRecord(null);
    const initial: RecordData = {};
    activeFields.forEach(f => {
      if (f.type === 'boolean') initial[f.key] = false;
      else if (f.type === 'multiselect') initial[f.key] = [];
      else initial[f.key] = '';
    });
    setFormData(initial);
    setResolvedLabels({});
    setShowModal(true);
  };

  const openEdit = (rec: PanelRecord) => {
    setEditingRecord(rec);
    setFormData({ ...rec.data });
    // Pre-populate resolved labels from record's _resolved data
    const labels: { [key: string]: { label: string; sub?: string } } = {};
    if (rec._resolved) {
      for (const [key, resolved] of Object.entries(rec._resolved)) {
        if (resolved) labels[key] = { label: resolved.label, sub: resolved.sub || resolved.sku || resolved.buyerName };
      }
    }
    setResolvedLabels(labels);
    setShowModal(true);
  };

  const openView = async (rec: PanelRecord) => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/panels/${panelId}/records/${rec.id}`, { headers: headers() });
      if (res.ok) {
        const d = await res.json();
        setViewRecord(d.record);
      }
    } catch { setViewRecord(rec); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const url = editingRecord
        ? `${API_URL}/api/business-tools/panels/${panelId}/records/${editingRecord.id}`
        : `${API_URL}/api/business-tools/panels/${panelId}/records`;
      const res = await fetch(url, {
        method: editingRecord ? 'PUT' : 'POST',
        headers: headers(),
        body: JSON.stringify({ data: formData }),
      });
      if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Save failed'); setSaving(false); return; }
      toast.success(editingRecord ? 'Record updated' : 'Record created');
      setShowModal(false);
      fetchRecords();
    } catch { toast.error('Save failed'); }
    setSaving(false);
  };

  const handleDelete = async (rec: PanelRecord) => {
    if (!confirm('Delete this record? This cannot be undone.')) return;
    try {
      const res = await fetch(`${API_URL}/api/business-tools/panels/${panelId}/records/${rec.id}`, {
        method: 'DELETE', headers: headers(),
      });
      if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Delete failed'); return; }
      toast.success('Record deleted');
      fetchRecords();
    } catch { toast.error('Delete failed'); }
  };

  const handleExport = async (format: 'excel' | 'pdf') => {
    const setLoading = format === 'excel' ? setExportingExcel : setExportingPdf;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/business-tools/panels/${panelId}/export/${format}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({ detail: 'Export failed' }));
        toast.error(d.detail || 'Export failed');
        setLoading(false);
        return;
      }
      const blob = await res.blob();
      const ext = format === 'excel' ? 'xlsx' : 'pdf';
      const filename = `${panel?.name?.replace(/\s+/g, '_') || 'export'}_export.${ext}`;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`${format === 'excel' ? 'Excel' : 'PDF'} exported successfully`);
    } catch {
      toast.error('Export failed');
    }
    setLoading(false);
  };

  const setField = (key: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const renderFieldValue = (field: PanelField, value: any, resolved?: any) => {
    if (value === undefined || value === null || value === '') return <span className="text-gray-300">—</span>;
    if (field.type === 'boolean') return value ? <span className="text-green-600 font-medium">Yes</span> : <span className="text-red-500 font-medium">No</span>;
    if (field.type === 'multiselect' && Array.isArray(value)) return value.join(', ') || '—';
    if (field.type === 'relation' && resolved) return <span className="text-indigo-600 font-medium">{resolved.label}{resolved.sub ? ` (${resolved.sub})` : ''}</span>;
    return String(value);
  };

  if (permLoading || (!panel && loading)) {
    return <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;
  }

  if (!panel) {
    return <div className="text-center py-16 text-gray-500">Panel not found</div>;
  }

  // Display columns: first 4 non-disabled fields
  const displayFields = activeFields.slice(0, 4);

  return (
    <div className="space-y-5" data-testid="panel-detail-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Link href="/seller/business-tools/panels" className="p-1.5 hover:bg-gray-100 rounded-lg" data-testid="back-to-panels">
            <ArrowLeft className="h-5 w-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900" data-testid="panel-detail-title">{panel.name}</h1>
            {panel.description && <p className="text-sm text-gray-500">{panel.description}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('excel')}
            disabled={exportingExcel || total === 0}
            className="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            data-testid="export-excel-btn"
          >
            <FileSpreadsheet className="h-4 w-4" />
            {exportingExcel ? 'Exporting...' : 'Excel'}
          </button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={exportingPdf || total === 0}
            className="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            data-testid="export-pdf-btn"
          >
            <FileDown className="h-4 w-4" />
            {exportingPdf ? 'Exporting...' : 'PDF'}
          </button>
          <button onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
            data-testid="create-record-btn"
          >
            <Plus className="h-4 w-4" /> New Record
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search records..." className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm"
          data-testid="records-search"
        />
      </div>

      {/* Records Table */}
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-600" /></div>
      ) : records.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border" data-testid="empty-records">
          <h3 className="text-lg font-semibold text-gray-700">No records yet</h3>
          <p className="text-gray-400 text-sm mt-1">Create your first record to start tracking data.</p>
          <button onClick={openCreate}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
            data-testid="create-first-record-btn"
          >
            <Plus className="h-4 w-4 inline mr-1" /> Create Record
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden" data-testid="records-table">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">#</th>
                  {displayFields.map(f => (
                    <th key={f.key} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{f.label}</th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {records.map((rec, idx) => (
                  <tr key={rec.id} className="hover:bg-gray-50" data-testid={`record-row-${rec.id}`}>
                    <td className="px-4 py-3 text-gray-400 text-xs">{(page - 1) * 50 + idx + 1}</td>
                    {displayFields.map(f => (
                      <td key={f.key} className="px-4 py-3 text-gray-800 max-w-[200px] truncate">
                        {renderFieldValue(f, rec.data[f.key], rec._resolved?.[f.key])}
                      </td>
                    ))}
                    <td className="px-4 py-3 text-gray-400 text-xs">{new Date(rec.createdAt).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openView(rec)} className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded" data-testid={`view-record-${rec.id}`}>
                          <Eye className="h-4 w-4" />
                        </button>
                        <button onClick={() => openEdit(rec)} className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded" data-testid={`edit-record-${rec.id}`}>
                          <Pencil className="h-4 w-4" />
                        </button>
                        {isAdmin && (
                          <button onClick={() => handleDelete(rec)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded" data-testid={`delete-record-${rec.id}`}>
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50/50">
              <span className="text-xs text-gray-500">{total} record{total !== 1 ? 's' : ''}</span>
              <div className="flex items-center gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="p-1 rounded border disabled:opacity-30" data-testid="prev-page">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-gray-600">Page {page} of {pages}</span>
                <button disabled={page >= pages} onClick={() => setPage(p => p + 1)}
                  className="p-1 rounded border disabled:opacity-30" data-testid="next-page">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl w-full max-w-xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="record-modal">
            <div className="p-5 border-b sticky top-0 bg-white z-10 rounded-t-xl flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">{editingRecord ? 'Edit Record' : 'New Record'}</h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5 text-gray-500" /></button>
            </div>
            <div className="p-5 space-y-4">
              {activeFields.map(f => (
                <div key={f.key} data-testid={`form-field-${f.key}`}>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {f.label} {f.required && <span className="text-red-400">*</span>}
                  </label>

                  {f.type === 'text' && (
                    <input type="text" value={formData[f.key] || ''} onChange={e => setField(f.key, e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm" data-testid={`input-${f.key}`} />
                  )}

                  {f.type === 'number' && (
                    <input type="number" value={formData[f.key] || ''} onChange={e => setField(f.key, e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm" data-testid={`input-${f.key}`} />
                  )}

                  {f.type === 'date' && (
                    <input type="date" value={formData[f.key] || ''} onChange={e => setField(f.key, e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm" data-testid={`input-${f.key}`} />
                  )}

                  {f.type === 'longtext' && (
                    <textarea value={formData[f.key] || ''} onChange={e => setField(f.key, e.target.value)}
                      rows={3} className="w-full px-3 py-2 border rounded-lg text-sm" data-testid={`input-${f.key}`} />
                  )}

                  {f.type === 'boolean' && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={!!formData[f.key]} onChange={e => setField(f.key, e.target.checked)}
                        className="rounded border-gray-300 text-indigo-600 w-4 h-4" data-testid={`input-${f.key}`} />
                      <span className="text-sm text-gray-600">{formData[f.key] ? 'Yes' : 'No'}</span>
                    </label>
                  )}

                  {f.type === 'dropdown' && (
                    <select value={formData[f.key] || ''} onChange={e => setField(f.key, e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm" data-testid={`input-${f.key}`}>
                      <option value="">Select...</option>
                      {(f.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  )}

                  {f.type === 'multiselect' && (
                    <div className="flex flex-wrap gap-2">
                      {(f.options || []).map(o => {
                        const selected = (formData[f.key] || []).includes(o);
                        return (
                          <button key={o} type="button"
                            onClick={() => {
                              const current = formData[f.key] || [];
                              setField(f.key, selected ? current.filter((v: string) => v !== o) : [...current, o]);
                            }}
                            className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                              selected ? 'bg-indigo-100 border-indigo-300 text-indigo-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                            }`}
                            data-testid={`input-${f.key}-${o}`}
                          >
                            {o}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {f.type === 'relation' && (
                    <RelationField
                      panelId={panelId}
                      fieldKey={f.key}
                      relatedPanel={f.relatedPanel || ''}
                      value={formData[f.key] || ''}
                      resolvedLabel={resolvedLabels[f.key]?.label}
                      resolvedSub={resolvedLabels[f.key]?.sub}
                      token={token || ''}
                      onChange={(id, label) => {
                        setField(f.key, id);
                        setResolvedLabels(prev => ({ ...prev, [f.key]: { label } }));
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="p-5 border-t bg-gray-50/50 rounded-b-xl flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                data-testid="save-record-btn"
              >
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : editingRecord ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {viewRecord && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setViewRecord(null)}>
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="view-record-modal">
            <div className="p-5 border-b flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Record Details</h2>
              <button onClick={() => setViewRecord(null)} className="p-1 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5 text-gray-500" /></button>
            </div>
            <div className="p-5 space-y-4">
              {activeFields.map(f => (
                <div key={f.key} className="flex flex-col gap-0.5" data-testid={`view-field-${f.key}`}>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{f.label}</span>
                  <span className="text-sm text-gray-900">
                    {renderFieldValue(f, viewRecord.data[f.key], viewRecord._resolved?.[f.key])}
                  </span>
                </div>
              ))}
              <div className="pt-3 border-t text-xs text-gray-400 flex items-center justify-between">
                <span>Created: {new Date(viewRecord.createdAt).toLocaleString()}</span>
                <span>Updated: {new Date(viewRecord.updatedAt).toLocaleString()}</span>
              </div>
            </div>
            <div className="p-5 border-t bg-gray-50/50 rounded-b-xl flex justify-end gap-3">
              <button onClick={() => { setViewRecord(null); openEdit(viewRecord); }}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
                data-testid="edit-from-view-btn"
              >
                <Pencil className="h-4 w-4" /> Edit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
