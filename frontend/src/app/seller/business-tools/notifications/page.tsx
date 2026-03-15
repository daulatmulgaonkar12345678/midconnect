'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  Bell, AlertTriangle, FileText, Package2, ShoppingCart,
  Truck, CheckCircle2, Loader2, Check, CheckCheck, Clock
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Notification {
  id: string;
  sellerId: string;
  type: string;
  title: string;
  message: string;
  referenceId?: string;
  referenceType?: string;
  read: boolean;
  createdAt: string;
  readAt?: string;
}

const TYPE_FILTERS = [
  { value: '', label: 'All' },
  { value: 'low_stock', label: 'Low Stock' },
  { value: 'invoice_created', label: 'Invoices' },
  { value: 'payment_received', label: 'Payments' },
  { value: 'purchase_order', label: 'Purchases' },
  { value: 'inventory_update', label: 'Inventory' },
  { value: 'system', label: 'System' },
];

function getNotificationIcon(type: string) {
  switch (type) {
    case 'low_stock': return <AlertTriangle className="w-5 h-5 text-amber-500" />;
    case 'invoice_created': return <FileText className="w-5 h-5 text-blue-500" />;
    case 'payment_received': return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    case 'purchase_order': return <ShoppingCart className="w-5 h-5 text-purple-500" />;
    case 'inventory_update': return <Package2 className="w-5 h-5 text-cyan-500" />;
    case 'supplier_update': return <Truck className="w-5 h-5 text-indigo-500" />;
    default: return <Bell className="w-5 h-5 text-gray-500" />;
  }
}

function getNotificationBg(type: string, read: boolean) {
  if (read) return 'bg-white';
  switch (type) {
    case 'low_stock': return 'bg-amber-50 border-l-4 border-l-amber-400';
    case 'invoice_created': return 'bg-blue-50 border-l-4 border-l-blue-400';
    case 'payment_received': return 'bg-green-50 border-l-4 border-l-green-400';
    case 'purchase_order': return 'bg-purple-50 border-l-4 border-l-purple-400';
    case 'inventory_update': return 'bg-cyan-50 border-l-4 border-l-cyan-400';
    default: return 'bg-gray-50 border-l-4 border-l-gray-400';
  }
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

export default function NotificationsPage() {
  const { getIdToken } = useAuth();
  const { token, loading: permLoading } = usePermissions();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [page, setPage] = useState(0);
  const [markingAll, setMarkingAll] = useState(false);
  const LIMIT = 20;

  const getAuthHeaders = useCallback(async () => {
    const t = token || await getIdToken();
    if (!t) return null;
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [token, getIdToken]);

  const fetchNotifications = useCallback(async (reset = false) => {
    const h = await getAuthHeaders();
    if (!h) return;
    const skip = reset ? 0 : page * LIMIT;
    const params = new URLSearchParams({
      limit: String(LIMIT),
      skip: String(skip),
    });
    if (showUnreadOnly) params.set('unread_only', 'true');
    if (typeFilter) params.set('notification_type', typeFilter);

    try {
      const res = await fetch(`${API_URL}/api/business-tools/notifications?${params}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
        setTotal(data.total || 0);
        setUnread(data.unread || 0);
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [getAuthHeaders, page, showUnreadOnly, typeFilter]);

  useEffect(() => {
    if (permLoading || !token) return;
    setLoading(true);
    fetchNotifications(true);
  }, [token, permLoading, typeFilter, showUnreadOnly]);

  useEffect(() => {
    if (!token || page === 0) return;
    fetchNotifications();
  }, [page]);

  const markAsRead = async (id: string) => {
    const h = await getAuthHeaders();
    if (!h) return;
    await fetch(`${API_URL}/api/business-tools/notifications/${id}/read`, { method: 'PUT', headers: h });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    setUnread(prev => Math.max(0, prev - 1));
  };

  const markAllRead = async () => {
    const h = await getAuthHeaders();
    if (!h) return;
    setMarkingAll(true);
    await fetch(`${API_URL}/api/business-tools/notifications/mark-all-read`, { method: 'PUT', headers: h });
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    setUnread(0);
    setMarkingAll(false);
  };

  if (loading && notifications.length === 0) {
    return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;
  }

  return (
    <div className="space-y-4" data-testid="notifications-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="notifications-heading">Notifications</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {unread > 0 ? <span className="text-red-600 font-medium">{unread} unread</span> : 'All caught up'} &middot; {total} total
          </p>
        </div>
        {unread > 0 && (
          <button
            onClick={markAllRead}
            disabled={markingAll}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
            data-testid="mark-all-read-btn"
          >
            {markingAll ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCheck className="h-4 w-4" />}
            Mark All Read
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2" data-testid="notification-filters">
        {TYPE_FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => { setTypeFilter(f.value); setPage(0); }}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              typeFilter === f.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            data-testid={`filter-${f.value || 'all'}`}
          >
            {f.label}
          </button>
        ))}
        <button
          onClick={() => { setShowUnreadOnly(!showUnreadOnly); setPage(0); }}
          className={`px-3 py-1.5 text-sm rounded-lg transition ml-auto ${
            showUnreadOnly ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
          data-testid="filter-unread-only"
        >
          {showUnreadOnly ? 'Unread Only' : 'Show All'}
        </button>
      </div>

      {/* Notification List */}
      <div className="space-y-2" data-testid="notification-list">
        {notifications.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border">
            <Bell className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">No Notifications</h3>
            <p className="text-sm text-gray-500 mt-1">
              {typeFilter ? 'No notifications of this type' : 'You\'re all caught up!'}
            </p>
          </div>
        ) : (
          notifications.map(n => (
            <div
              key={n.id}
              className={`flex items-start gap-3 p-4 rounded-xl border transition ${getNotificationBg(n.type, n.read)} ${!n.read ? 'shadow-sm' : ''}`}
              data-testid={`notification-${n.id}`}
            >
              <div className="mt-0.5 flex-shrink-0">
                {getNotificationIcon(n.type)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h3 className={`text-sm ${n.read ? 'text-gray-700' : 'text-gray-900 font-semibold'}`}>
                    {n.title}
                  </h3>
                  <span className="text-xs text-gray-400 whitespace-nowrap flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {timeAgo(n.createdAt)}
                  </span>
                </div>
                <p className="text-sm text-gray-600 mt-0.5">{n.message}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                    {n.type.replace(/_/g, ' ')}
                  </span>
                  {!n.read && (
                    <button
                      onClick={() => markAsRead(n.id)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 transition"
                      data-testid={`mark-read-${n.id}`}
                    >
                      <Check className="h-3 w-3" /> Mark as Read
                    </button>
                  )}
                  {n.read && (
                    <span className="text-[10px] text-green-500 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" /> Read
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {total > LIMIT && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-4 py-2 text-sm bg-white border rounded-lg disabled:opacity-50 hover:bg-gray-50 transition"
            data-testid="prev-page"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {page + 1} of {Math.ceil(total / LIMIT)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={(page + 1) * LIMIT >= total}
            className="px-4 py-2 text-sm bg-white border rounded-lg disabled:opacity-50 hover:bg-gray-50 transition"
            data-testid="next-page"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
