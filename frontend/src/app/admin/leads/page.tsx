'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getAdminInquiries, exportAdminInquiries } from '@/lib/api';
import type { AdminInquiry } from '@/types';
import { 
  Search, Filter, Download, ChevronLeft, ChevronRight, 
  Loader2, AlertCircle, CheckCircle, XCircle, Flag, Clock 
} from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  reported: 'bg-purple-100 text-purple-800',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Clock className="w-3 h-3" />,
  accepted: <CheckCircle className="w-3 h-3" />,
  rejected: <XCircle className="w-3 h-3" />,
  reported: <Flag className="w-3 h-3" />,
};

export default function AdminLeadsPage() {
  const { getIdToken } = useAuth();
  const [inquiries, setInquiries] = useState<AdminInquiry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    fetchInquiries();
  }, [page, statusFilter, categoryFilter, dateFrom, dateTo]);

  const fetchInquiries = async () => {
    try {
      setIsLoading(true);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const data = await getAdminInquiries(token, {
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        page,
        limit: 20
      });
      
      // Debug: Log full API response to verify data structure
      console.log("ADMIN INQUIRIES API RESPONSE:", JSON.stringify(data, null, 2));
      if (data?.inquiries?.[0]) {
        console.log("FIRST INQUIRY productName:", data.inquiries[0].productName);
        console.log("FIRST INQUIRY product.name:", data.inquiries[0].product?.name);
      }
      
      setInquiries(data?.inquiries ?? []);
      setTotalPages(data?.pages ?? 1);
      setTotal(data?.total ?? 0);
    } catch (err: any) {
      console.error('Failed to fetch inquiries:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const blob = await exportAdminInquiries(token, {
        status: statusFilter || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined
      });
      
      // Download the file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      console.error('Export failed:', err);
      alert('Export failed: ' + err.message);
    } finally {
      setIsExporting(false);
    }
  };

  const clearFilters = () => {
    setStatusFilter('');
    setCategoryFilter('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  if (error) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-lg">
        <p>Failed to load leads: {error}</p>
        <button onClick={fetchInquiries} className="mt-2 text-sm underline">Retry</button>
      </div>
    );
  }

  return (
    <div data-testid="admin-leads-page">
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Leads / Inquiries</h1>
          <p className="text-gray-500 text-sm">
            Single Source of Truth: All data from inquiries collection
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            data-testid="toggle-filters-btn"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            data-testid="export-csv-btn"
          >
            {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6" data-testid="filters-panel">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                data-testid="status-filter"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
                <option value="reported">Reported</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <input
                type="text"
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
                placeholder="Filter by category..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                data-testid="category-filter"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                data-testid="date-from-filter"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                data-testid="date-to-filter"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={clearFilters}
              className="text-sm text-gray-600 hover:text-gray-900"
              data-testid="clear-filters-btn"
            >
              Clear all filters
            </button>
          </div>
        </div>
      )}

      {/* Stats Summary */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-600">
          Showing <span className="font-semibold">{inquiries.length}</span> of{' '}
          <span className="font-semibold">{total}</span> total leads
        </p>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
          </div>
        ) : inquiries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <AlertCircle className="h-12 w-12 mb-4" />
            <p>No leads found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200" data-testid="leads-table">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Buyer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Seller</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subscription</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {inquiries.map((inquiry) => {
                  // Support multiple field name formats from backend
                  const productName = inquiry.product?.name || 
                    (inquiry as unknown as { productName?: string }).productName ||
                    (inquiry as unknown as { listing?: { name?: string } }).listing?.name ||
                    'N/A';
                  const categoryName = inquiry.category ||
                    (inquiry as unknown as { categoryName?: string }).categoryName ||
                    (inquiry as unknown as { listing?: { category?: string } }).listing?.category ||
                    'N/A';
                  const buyerName = inquiry.buyer?.name ||
                    (inquiry as unknown as { buyerName?: string }).buyerName ||
                    inquiry.buyer?.email?.split('@')[0] ||
                    'N/A';
                  const sellerName = inquiry.seller?.name ||
                    (inquiry as unknown as { sellerName?: string }).sellerName ||
                    (inquiry as unknown as { seller?: { businessName?: string } }).seller?.businessName ||
                    inquiry.seller?.email?.split('@')[0] ||
                    'N/A';
                  
                  return (
                  <tr key={inquiry._id} className="hover:bg-gray-50" data-testid={`lead-row-${inquiry._id}`}>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[inquiry.status] || 'bg-gray-100 text-gray-800'}`}>
                        {STATUS_ICONS[inquiry.status]}
                        {inquiry.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900 max-w-[200px] truncate">
                        {productName}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {categoryName}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">
                        <p className="font-medium text-gray-900">{buyerName}</p>
                        <p className="text-gray-500 text-xs">{inquiry.buyer?.city || ''}{inquiry.buyer?.city && inquiry.buyer?.state ? ', ' : ''}{inquiry.buyer?.state || ''}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">
                        <p className="font-medium text-gray-900">{sellerName}</p>
                        <p className="text-gray-500 text-xs">{inquiry.seller?.city || ''}{inquiry.seller?.city && inquiry.seller?.state ? ', ' : ''}{inquiry.seller?.state || ''}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        inquiry.sellerSubscriptionPlan === 'pro' ? 'bg-blue-100 text-blue-800' :
                        inquiry.sellerSubscriptionPlan === 'trial' ? 'bg-purple-100 text-purple-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {inquiry.sellerSubscriptionPlan || 'free'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {inquiry.quantity || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {inquiry.createdAt ? new Date(inquiry.createdAt).toLocaleDateString('en-IN', {
                        timeZone: 'Asia/Kolkata',
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                        }) : 'N/A'}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200" data-testid="pagination">
            <p className="text-sm text-gray-500">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                data-testid="prev-page-btn"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                data-testid="next-page-btn"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
