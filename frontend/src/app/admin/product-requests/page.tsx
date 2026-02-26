'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Package, 
  FolderOpen, 
  ListPlus,
  Loader2,
  RefreshCw,
  AlertCircle
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface BaseRequest {
  _id: string;
  status: 'pending' | 'approved' | 'rejected';
  requested_by: string;
  requested_by_email: string;
  created_at: string;
  reason?: string;
  admin_notes?: string;
}

interface ProductRequest extends BaseRequest {
  product_name: string;
  suggested_category_id: string;
  description?: string;
}

interface CategoryRequest extends BaseRequest {
  category_name: string;
  description?: string;
}

interface SpecFieldRequest extends BaseRequest {
  category_id: string;
  category_name?: string;
  field_name: string;
  field_type: string;
  unit?: string;
  suggested_options?: string[];
}

type RequestType = 'products' | 'categories' | 'spec-fields';

export default function ProductRequestsPage() {
  const { getIdToken } = useAuth();
  const [activeTab, setActiveTab] = useState<RequestType>('products');
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  const [productRequests, setProductRequests] = useState<ProductRequest[]>([]);
  const [categoryRequests, setCategoryRequests] = useState<CategoryRequest[]>([]);
  const [specFieldRequests, setSpecFieldRequests] = useState<SpecFieldRequest[]>([]);

  const fetchRequests = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getIdToken();
      if (!token) {
        setError('Authentication required');
        return;
      }

      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      // Fetch all request types
      const [prodRes, catRes, specRes] = await Promise.all([
        fetch(`${API_URL}/admin/requests/products?status=${statusFilter}`, { headers, credentials: 'include' }),
        fetch(`${API_URL}/admin/requests/categories?status=${statusFilter}`, { headers, credentials: 'include' }),
        fetch(`${API_URL}/admin/requests/spec-fields?status=${statusFilter}`, { headers, credentials: 'include' })
      ]);

      if (prodRes.ok) {
        const data = await prodRes.json();
        setProductRequests(data.requests || []);
      }
      
      if (catRes.ok) {
        const data = await catRes.json();
        setCategoryRequests(data.requests || []);
      }
      
      if (specRes.ok) {
        const data = await specRes.json();
        setSpecFieldRequests(data.requests || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch requests');
    } finally {
      setIsLoading(false);
    }
  }, [getIdToken, statusFilter]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleReview = async (type: RequestType, id: string, action: 'approved' | 'rejected', notes?: string) => {
    setActionLoading(id);
    setError(null);
    
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Authentication required');

      const endpoint = type === 'products' 
        ? `${API_URL}/admin/requests/products/${id}/review`
        : type === 'categories'
        ? `${API_URL}/admin/requests/categories/${id}/review`
        : `${API_URL}/admin/requests/spec-fields/${id}/review`;

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ status: action, admin_notes: notes })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to process request');
      }

      // Refresh requests
      fetchRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process request');
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr: string | undefined | null) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 'N/A';
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"><Clock className="h-3 w-3" /> Pending</span>;
      case 'approved':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="h-3 w-3" /> Approved</span>;
      case 'rejected':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"><XCircle className="h-3 w-3" /> Rejected</span>;
      default:
        return null;
    }
  };

  const tabs = [
    { id: 'products' as RequestType, label: 'Product Requests', icon: Package, count: productRequests.length },
    { id: 'categories' as RequestType, label: 'Category Requests', icon: FolderOpen, count: categoryRequests.length },
    { id: 'spec-fields' as RequestType, label: 'Spec Field Requests', icon: ListPlus, count: specFieldRequests.length }
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Seller Requests</h1>
        <p className="text-gray-500">Review and approve requests from sellers</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-gray-100">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          data-testid="status-filter"
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="all">All</option>
        </select>
        <button
          onClick={fetchRequests}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
          title="Refresh"
        >
          <RefreshCw className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="text-center py-16">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto" />
        </div>
      ) : (
        <>
          {/* Product Requests */}
          {activeTab === 'products' && (
            productRequests.length > 0 ? (
              <div className="space-y-4">
                {productRequests.map((request) => {
                  // Support both snake_case and camelCase from backend
                  const productName = request.product_name || (request as unknown as { productName?: string }).productName || 'Unknown Product';
                  const requestedByEmail = request.requested_by_email || (request as unknown as { requestedByEmail?: string }).requestedByEmail || 'Unknown';
                  const createdAt = request.created_at || (request as unknown as { createdAt?: string }).createdAt;
                  const categoryId = request.suggested_category_id || (request as unknown as { suggestedCategoryId?: string }).suggestedCategoryId || '';
                  
                  return (
                  <div key={request._id} className="bg-white rounded-xl shadow-sm p-6" data-testid={`product-request-${request._id}`}>
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="font-semibold text-lg">{productName}</h3>
                        <p className="text-sm text-gray-500">
                          Requested by: {requestedByEmail}
                        </p>
                        <p className="text-xs text-gray-400">{formatDate(createdAt)}</p>
                        {categoryId && <p className="text-xs text-gray-400 mt-1">Category ID: {categoryId}</p>}
                      </div>
                      {getStatusBadge(request.status)}
                    </div>
                    
                    {request.description && (
                      <div className="bg-gray-50 rounded-lg p-4 mb-4">
                        <p className="text-sm font-medium text-gray-700 mb-1">Description:</p>
                        <p className="text-sm text-gray-600">{request.description}</p>
                      </div>
                    )}
                    
                    {request.reason && (
                      <div className="bg-blue-50 rounded-lg p-4 mb-4">
                        <p className="text-sm font-medium text-blue-700 mb-1">Reason:</p>
                        <p className="text-sm text-blue-600">{request.reason}</p>
                      </div>
                    )}

                    {request.status === 'pending' && (
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleReview('products', request._id, 'approved')}
                          disabled={actionLoading === request._id}
                          className="flex-1 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          {actionLoading === request._id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                          Approve & Create Product
                        </button>
                        <button
                          onClick={() => handleReview('products', request._id, 'rejected')}
                          disabled={actionLoading === request._id}
                          className="flex-1 border border-red-600 text-red-600 py-2 rounded-lg hover:bg-red-50 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          <XCircle className="h-4 w-4" /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState type="product" />
            )
          )}

          {/* Category Requests */}
          {activeTab === 'categories' && (
            categoryRequests.length > 0 ? (
              <div className="space-y-4">
                {categoryRequests.map((request) => {
                  // Support both snake_case and camelCase from backend
                  const categoryName = request.category_name || (request as unknown as { categoryName?: string }).categoryName || 'Unknown Category';
                  const requestedByEmail = request.requested_by_email || (request as unknown as { requestedByEmail?: string }).requestedByEmail || 'Unknown';
                  const createdAt = request.created_at || (request as unknown as { createdAt?: string }).createdAt;
                  
                  return (
                  <div key={request._id} className="bg-white rounded-xl shadow-sm p-6" data-testid={`category-request-${request._id}`}>
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="font-semibold text-lg">{categoryName}</h3>
                        <p className="text-sm text-gray-500">
                          Requested by: {requestedByEmail}
                        </p>
                        <p className="text-xs text-gray-400">{formatDate(createdAt)}</p>
                      </div>
                      {getStatusBadge(request.status)}
                    </div>
                    
                    {request.description && (
                      <div className="bg-gray-50 rounded-lg p-4 mb-4">
                        <p className="text-sm font-medium text-gray-700 mb-1">Description:</p>
                        <p className="text-sm text-gray-600">{request.description}</p>
                      </div>
                    )}

                    {request.status === 'pending' && (
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleReview('categories', request._id, 'approved')}
                          disabled={actionLoading === request._id}
                          className="flex-1 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          {actionLoading === request._id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                          Approve & Create Category
                        </button>
                        <button
                          onClick={() => handleReview('categories', request._id, 'rejected')}
                          disabled={actionLoading === request._id}
                          className="flex-1 border border-red-600 text-red-600 py-2 rounded-lg hover:bg-red-50 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          <XCircle className="h-4 w-4" /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState type="category" />
            )
          )}

          {/* Spec Field Requests */}
          {activeTab === 'spec-fields' && (
            specFieldRequests.length > 0 ? (
              <div className="space-y-4">
                {specFieldRequests.map((request) => {
                  // Support both snake_case and camelCase from backend
                  const fieldName = request.field_name || (request as unknown as { fieldName?: string }).fieldName || 'Unknown Field';
                  const fieldType = request.field_type || (request as unknown as { fieldType?: string }).fieldType || 'text';
                  const categoryName = request.category_name || (request as unknown as { categoryName?: string }).categoryName || request.category_id || 'Unknown';
                  const requestedByEmail = request.requested_by_email || (request as unknown as { requestedByEmail?: string }).requestedByEmail || 'Unknown';
                  const createdAt = request.created_at || (request as unknown as { createdAt?: string }).createdAt;
                  const unit = request.unit || '';
                  const suggestedOptions = request.suggested_options || (request as unknown as { suggestedOptions?: string[] }).suggestedOptions || [];
                  
                  return (
                  <div key={request._id} className="bg-white rounded-xl shadow-sm p-6" data-testid={`spec-field-request-${request._id}`}>
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="font-semibold text-lg">{fieldName}</h3>
                        <p className="text-sm text-gray-500">
                          Category: {categoryName}
                        </p>
                        <p className="text-sm text-gray-500">
                          Type: {fieldType} {unit && `(${unit})`}
                        </p>
                        <p className="text-xs text-gray-400">
                          Requested by: {requestedByEmail} • {formatDate(createdAt)}
                        </p>
                      </div>
                      {getStatusBadge(request.status)}
                    </div>
                    
                    {suggestedOptions.length > 0 && (
                      <div className="bg-gray-50 rounded-lg p-4 mb-4">
                        <p className="text-sm font-medium text-gray-700 mb-1">Suggested Options:</p>
                        <div className="flex flex-wrap gap-2">
                          {suggestedOptions.map((opt, i) => (
                            <span key={i} className="px-2 py-1 bg-white border rounded text-sm">{opt}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {request.status === 'pending' && (
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleReview('spec-fields', request._id, 'approved')}
                          disabled={actionLoading === request._id}
                          className="flex-1 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          {actionLoading === request._id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                          Approve & Add Field
                        </button>
                        <button
                          onClick={() => handleReview('spec-fields', request._id, 'rejected')}
                          disabled={actionLoading === request._id}
                          className="flex-1 border border-red-600 text-red-600 py-2 rounded-lg hover:bg-red-50 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          <XCircle className="h-4 w-4" /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState type="spec field" />
            )
          )}
        </>
      )}
    </div>
  );
}

function EmptyState({ type }: { type: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-16 text-center">
      <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">No {type} requests</h3>
      <p className="text-gray-500">No {type} requests match your current filter.</p>
    </div>
  );
}
