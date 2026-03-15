'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  Bell, CheckCircle2, CreditCard, AlertTriangle, FileText,
  AlertCircle, Check, ChevronRight
} from 'lucide-react';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  referenceId?: string;
  referenceType?: string;
  read: boolean;
  createdAt: string;
}

const typeConfig: Record<string, { icon: typeof Bell; color: string; bg: string }> = {
  payment_received: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  partial_payment: { icon: CreditCard, color: 'text-blue-600', bg: 'bg-blue-50' },
  invoice_overdue: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
  invoice_created: { icon: FileText, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  low_stock: { icon: AlertCircle, color: 'text-orange-600', bg: 'bg-orange-50' },
  system_alert: { icon: AlertCircle, color: 'text-amber-600', bg: 'bg-amber-50' },
};

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function NotificationsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [unread, setUnread] = useState(0);
  const [total, setTotal] = useState(0);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchNotifications = useCallback(async () => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/notifications?limit=100`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
        setUnread(data.unread || 0);
        setTotal(data.total || 0);
      }
    } catch { }
    setLoading(false);
  }, [authHeaders]);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const markRead = async (id: string) => {
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/notifications/${id}/read`, { method: 'PUT', headers: h });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    setUnread(prev => Math.max(0, prev - 1));
  };

  const markAllRead = async () => {
    const h = await authHeaders();
    await fetch(`${API_URL}/api/business-tools/notifications/mark-all-read`, { method: 'PUT', headers: h });
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    setUnread(0);
  };

  const openReference = (n: Notification) => {
    if (!n.read) markRead(n.id);

    if (n.referenceType === 'invoice' && n.referenceId) {
      router.push('/seller/business-tools/invoices');
    } 
    else if (n.referenceType === 'inventory') {
      router.push('/seller/business-tools/inventory');
    }
  };

  if (!hasPermission('create_invoice')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border" data-testid="no-permission">
        <p className="text-gray-500">No permission.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="notifications-page">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-sm text-gray-500 mt-1">
            {unread > 0 ? `${unread} unread` : 'All caught up'} — {total} total
          </p>
        </div>

        {unread > 0 && (
          <button
            onClick={markAllRead}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50"
            data-testid="mark-all-read-btn"
          >
            <Check className="w-4 h-4" />
            Mark all read
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>

      ) : notifications.length === 0 ? (

        <div className="text-center py-16 bg-white rounded-xl border border-gray-100" data-testid="empty-notifications">
          <Bell className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No notifications yet</p>
          <p className="text-sm text-gray-400 mt-1">
            You&apos;ll see payment alerts and reminders here
          </p>
        </div>

      ) : (

        <div className="space-y-2">
          {notifications.map(n => {

            const cfg = typeConfig[n.type] || typeConfig.system_alert;
            const Icon = cfg.icon;

            return (
              <div
                key={n.id}
                onClick={() => openReference(n)}
                className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition ${
                  n.read
                    ? 'bg-white border-gray-100 hover:bg-gray-50'
                    : 'bg-indigo-50/30 border-indigo-100 hover:bg-indigo-50/50'
                }`}
                data-testid={`notification-${n.id}`}
              >

                <div className={`w-9 h-9 rounded-lg ${cfg.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-4.5 h-4.5 ${cfg.color}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className={`text-sm font-medium ${n.read ? 'text-gray-700' : 'text-gray-900'}`}>
                      {n.title}
                    </p>

                    {!n.read && (
                      <span className="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0" />
                    )}
                  </div>

                  <p className="text-xs text-gray-500 mt-0.5">{n.message}</p>
                  <p className="text-xs text-gray-400 mt-1">{timeAgo(n.createdAt)}</p>
                </div>

                <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0 mt-1" />
              </div>
            );
          })}
        </div>

      )}

    </div>
  );
}