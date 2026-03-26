'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { getAdminUsers, toggleAdminStatus, restoreUser, AdminUser, fetchWithAuth } from '@/lib/api';
import { Loader2, Search, Shield, ShieldOff, RefreshCw, ChevronLeft, ChevronRight, Crown, Eye, AlertTriangle } from 'lucide-react';

export default function UsersPage() {
  const { getIdToken, profile } = useAuth();
  const searchParams = useSearchParams();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'all');
  const [sellerFilter, setSellerFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchUsers();
  }, [page, statusFilter, sellerFilter]);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const options: any = { page, limit: 20 };
      if (search) options.search = search;
      if (statusFilter !== 'all') options.status = statusFilter;
      if (sellerFilter !== 'all') options.isSeller = sellerFilter === 'seller';
      
      const data = await getAdminUsers(token, options);
      setUsers(data?.users ?? []);
      setTotalPages(data?.pages ?? 1);
      setTotal(data?.total ?? 0);
    } catch (err: any) {
      console.error('Failed to fetch users:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleToggleAdmin = async (user: AdminUser) => {
    if (user.id === profile?._id) {
      alert('Cannot modify your own admin status');
      return;
    }
    
    const action = user.isAdmin ? 'revoke admin from' : 'grant admin to';
    if (!confirm(`Are you sure you want to ${action} ${user.email}?`)) return;
    
    try {
      const token = await getIdToken();
      if (!token) return;
      await toggleAdminStatus(token, user.id);
      fetchUsers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRestore = async (user: AdminUser) => {
    if (!confirm(`Restore account for ${user.email}?`)) return;
    
    try {
      const token = await getIdToken();
      if (!token) return;
      await restoreUser(token, user.id);
      fetchUsers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <p className="text-gray-500">Manage all users on the platform</p>
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
                placeholder="Search by email, business name, phone..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </form>
          
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="deleted">Deleted</option>
          </select>
          
          <select
            value={sellerFilter}
            onChange={(e) => { setSellerFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Users</option>
            <option value="seller">Sellers Only</option>
            <option value="buyer">Buyers Only</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="users-table">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subscription</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">End Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Left</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">GST</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {users.map((user: AdminUser) => (
                    <tr key={user.id} className={user.accountStatus === 'deleted' ? 'bg-red-50' : ''} data-testid={`user-row-${user.id}`}>
                      <td className="px-4 py-4">
                        <div>
                          <p className="font-medium text-gray-900 flex items-center gap-2">
                            {user.profile?.businessName || 'No Business Name'}
                            {user.isAdmin && (
                              <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">Admin</span>
                            )}
                          </p>
                          <p className="text-sm text-gray-500">{user.email}</p>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-600">
                        <p>{user.profile?.phone || '-'}</p>
                        <p className="text-gray-400">{user.profile?.city}{user.profile?.state ? `, ${user.profile.state}` : ''}</p>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${
                          user.subscriptionPlan === 'enterprise' ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white' :
                          user.subscriptionPlan === 'pro' ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white' :
                          user.subscriptionPlan === 'standard' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {user.subscriptionPlan === 'pro' && <Crown className="h-3 w-3" />}
                          {(user.subscriptionPlan || 'free').charAt(0).toUpperCase() + (user.subscriptionPlan || 'free').slice(1)}
                        </span>
                        {user.subscriptionStatus === 'suspended' && (
                          <span className="ml-1 px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded-full">Suspended</span>
                        )}
                        {user.subscriptionStatus === 'expired' && (
                          <span className="ml-1 px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded-full">Expired</span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-600">
                        {user.subscriptionEnd ? new Date(user.subscriptionEnd).toLocaleDateString() : '-'}
                      </td>
                      <td className="px-4 py-4">
                        {user.daysRemaining === -1 ? (
                          <span className="text-gray-400">∞</span>
                        ) : (
                          <span className={`flex items-center gap-1 ${
                            user.isExpiringSoon ? 'text-orange-600 font-medium' : 
                            (user.daysRemaining || 0) <= 0 ? 'text-red-600' : 'text-gray-600'
                          }`}>
                            {user.isExpiringSoon && <AlertTriangle className="h-3 w-3" />}
                            {user.daysRemaining ?? 0}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          user.gst?.status === 'verified' ? 'bg-green-100 text-green-700' :
                          user.gst?.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {user.gst?.status || 'None'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          user.accountStatus === 'deleted' ? 'bg-red-100 text-red-700' :
                          user.accountStatus === 'archived' ? 'bg-gray-100 text-gray-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {user.accountStatus || 'Active'}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link
                            href={`/admin/users/${user.id}`}
                            className="p-2 text-gray-400 hover:text-blue-600 transition"
                            title="View Details & Manage Subscription"
                            data-testid={`view-user-${user.id}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Link>
                          {user.accountStatus === 'deleted' && (
                            <button
                              onClick={() => handleRestore(user)}
                              className="p-2 text-gray-400 hover:text-green-600 transition"
                              title="Restore Account"
                            >
                              <RefreshCw className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleToggleAdmin(user)}
                            className={`p-2 transition ${user.isAdmin ? 'text-purple-600 hover:text-purple-800' : 'text-gray-400 hover:text-purple-600'}`}
                            title={user.isAdmin ? 'Revoke Admin' : 'Grant Admin'}
                            disabled={user.id === profile?._id}
                          >
                            {user.isAdmin ? <ShieldOff className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                        No users found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-4 border-t">
                <p className="text-sm text-gray-500">
                  Showing {users.length} of {total} users
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
    </div>
  );
}
