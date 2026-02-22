'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { CheckCircle, XCircle, Eye, Clock, MapPin, Phone, Mail, FileText, AlertCircle, Loader2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://midconnect.onrender.com/api';

interface GSTRequest {
  _id: string;
  email: string;
  business_name: string;
  gst_number: string;
  owner_name: string;
  gst_document_url?: string;
  gst_status: string;
  business_location?: string;
  phone?: string;
  created_at?: string;
  updated_at?: string;
}

export default function GSTVerificationPage() {
  const { getIdToken, isAdmin } = useAuth();
  const [requests, setRequests] = useState<GSTRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<GSTRequest | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingGST();
  }, []);

  const fetchPendingGST = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getIdToken();
      if (!token) {
        setError('Authentication required');
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/admin/gst/pending`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to fetch pending GST requests');
      }

      const data = await response.json();
      setRequests(data.pending_reviews || []);
    } catch (err) {
      console.error('Failed to fetch GST requests:', err);
      setError(err instanceof Error ? err.message : 'Failed to load pending GST requests');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (userId: string, verified: boolean) => {
    setActionLoading(userId);
    
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(`${API_URL}/admin/users/${userId}/verify-gst?verified=${verified}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Verification failed');
      }

      // Remove from list and close modal
      setRequests(requests.filter(r => r._id !== userId));
      setSelectedRequest(null);
    } catch (err) {
      console.error('Verification failed:', err);
      alert(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setActionLoading(null);
    }
  };

  // Not admin
  if (!isAdmin) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900">Access Denied</h2>
        <p className="text-gray-500">You need admin privileges to access this page.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">GST Verification</h1>
          <p className="text-gray-500">Review and verify seller GST submissions</p>
        </div>
        <button
          onClick={fetchPendingGST}
          disabled={isLoading}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition flex items-center gap-2"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Refresh
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-16">
          <Loader2 className="h-12 w-12 text-blue-600 mx-auto animate-spin" />
          <p className="mt-4 text-gray-500">Loading pending GST verifications...</p>
        </div>
      ) : requests.length > 0 ? (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Seller</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">GST Number</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {requests.map((request) => (
                <tr key={request._id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900">{request.business_name}</p>
                      <p className="text-sm text-gray-500">{request.email}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-mono text-sm">{request.gst_number}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {request.business_location || '-'}
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      <Clock className="h-3 w-3" /> Pending
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSelectedRequest(request)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleVerify(request._id, true)}
                        disabled={actionLoading === request._id}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg disabled:opacity-50"
                        title="Approve"
                      >
                        {actionLoading === request._id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle className="h-4 w-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleVerify(request._id, false)}
                        disabled={actionLoading === request._id}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50"
                        title="Reject"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* EMPTY STATE - Important UX */
        <div className="bg-white rounded-xl shadow-sm p-16 text-center">
          <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Pending GST Verifications</h3>
          <p className="text-gray-500 max-w-md mx-auto">
            No sellers have submitted GST for verification yet. 
            When sellers become sellers and submit their GST, they will appear here for review.
          </p>
        </div>
      )}

      {/* Detail Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full mx-4 p-6">
            <h2 className="text-xl font-bold mb-4">GST Verification Details</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-gray-500">Business Name</label>
                <p className="font-medium">{selectedRequest.business_name}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-500 flex items-center gap-1">
                    <Mail className="h-3 w-3" /> Email
                  </label>
                  <p className="font-medium text-sm">{selectedRequest.email}</p>
                </div>
                <div>
                  <label className="text-sm text-gray-500 flex items-center gap-1">
                    <Phone className="h-3 w-3" /> Phone
                  </label>
                  <p className="font-medium text-sm">{selectedRequest.phone || '-'}</p>
                </div>
              </div>
              <div>
                <label className="text-sm text-gray-500 flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> Location
                </label>
                <p className="font-medium">{selectedRequest.business_location || '-'}</p>
              </div>
              <div>
                <label className="text-sm text-gray-500">GST Number</label>
                <p className="font-mono font-medium text-lg">{selectedRequest.gst_number}</p>
              </div>
              {selectedRequest.gst_document_url && (
                <div>
                  <label className="text-sm text-gray-500">Document</label>
                  <a
                    href={selectedRequest.gst_document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-blue-600 hover:underline"
                  >
                    <FileText className="h-4 w-4" /> View GST Certificate
                  </a>
                </div>
              )}
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => handleVerify(selectedRequest._id, true)}
                disabled={actionLoading === selectedRequest._id}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading === selectedRequest._id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
                Approve
              </button>
              <button
                onClick={() => handleVerify(selectedRequest._id, false)}
                disabled={actionLoading === selectedRequest._id}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <XCircle className="h-4 w-4" /> Reject
              </button>
              <button
                onClick={() => setSelectedRequest(null)}
                className="flex-1 border border-gray-300 py-2 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
