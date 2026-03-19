/**
 * Hook to manage offline draft invoices.
 * Provides: save draft locally, list offline drafts, delete draft, sync status.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useNetworkContext } from '@/context/NetworkContext';
import {
  addOfflineItem,
  getItemsByType,
  deleteOfflineItem,
  updateOfflineItem,
  getPendingCount,
  generateTempId,
  OfflineItem,
} from '@/lib/offlineStore';
import { processOfflineQueue } from '@/lib/syncEngine';
import { registerSyncListener } from '@/context/NetworkContext';
import { toast } from 'sonner';

export interface OfflineDraftInvoice {
  id: string;
  status: string;
  data: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
  lastError?: string;
}

export function useOfflineInvoices(userId: string | null, token: string | null) {
  const { isOnline, setSyncState } = useNetworkContext();
  const [offlineDrafts, setOfflineDrafts] = useState<OfflineDraftInvoice[]>([]);
  const [loading, setLoading] = useState(false);

  // Load offline drafts from IndexedDB
  const loadDrafts = useCallback(async () => {
    try {
      const items = await getItemsByType('invoice');
      const drafts = items
        .filter((i) => i.status !== 'synced')
        .map((i) => ({
          id: i.id,
          status: i.status,
          data: i.data,
          createdAt: i.createdAt,
          updatedAt: i.updatedAt,
          lastError: i.lastError,
        }));
      setOfflineDrafts(drafts);

      // Update global pending count
      const count = await getPendingCount();
      setSyncState((prev) => ({ ...prev, pendingCount: count }));
    } catch (err) {
      console.error('Failed to load offline drafts:', err);
    }
  }, [setSyncState]);

  useEffect(() => {
    loadDrafts();
  }, [loadDrafts]);

  // Save a new draft invoice offline
  const saveDraftOffline = useCallback(
    async (invoiceData: Record<string, unknown>) => {
      if (!userId) return null;
      const tempId = generateTempId(userId);

      const item = await addOfflineItem({
        id: tempId,
        type: 'invoice',
        status: 'draft_offline',
        data: {
          ...invoiceData,
          _tempId: tempId,
          _offlineCreated: true,
        },
        createdBy: userId,
      });

      toast.success('Invoice saved offline as draft');
      await loadDrafts();
      return item;
    },
    [userId, loadDrafts]
  );

  // Update an existing offline draft
  const updateDraftOffline = useCallback(
    async (id: string, invoiceData: Record<string, unknown>) => {
      await updateOfflineItem(id, {
        data: { ...invoiceData, _tempId: id, _offlineCreated: true },
        status: 'draft_offline',
      });
      toast.success('Offline draft updated');
      await loadDrafts();
    },
    [loadDrafts]
  );

  // Delete an offline draft
  const deleteDraftOffline = useCallback(
    async (id: string) => {
      await deleteOfflineItem(id);
      toast.info('Offline draft deleted');
      await loadDrafts();
    },
    [loadDrafts]
  );

  // Run sync when triggered
  const runSync = useCallback(async () => {
    if (!token || !isOnline) return;
    setLoading(true);
    try {
      const result = await processOfflineQueue(token, (state) => {
        setSyncState(state);
      });
      if (result.synced > 0) {
        toast.success(`${result.synced} offline item${result.synced > 1 ? 's' : ''} synced`);
      }
      if (result.failed > 0) {
        toast.error(`${result.failed} item${result.failed > 1 ? 's' : ''} failed to sync. Will retry.`);
      }
      await loadDrafts();
    } catch {
      toast.error('Sync failed. Retrying...');
    }
    setLoading(false);
  }, [token, isOnline, setSyncState, loadDrafts]);

  // Register sync listener (auto-sync when coming online)
  useEffect(() => {
    const unregister = registerSyncListener(() => {
      runSync();
    });
    return unregister;
  }, [runSync]);

  // Auto-sync on mount if online and there are pending items
  useEffect(() => {
    if (isOnline && offlineDrafts.length > 0 && token) {
      const hasPending = offlineDrafts.some((d) => d.status !== 'synced');
      if (hasPending) {
        runSync();
      }
    }
    // Only run on mount + when online status changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline]);

  return {
    offlineDrafts,
    saveDraftOffline,
    updateDraftOffline,
    deleteDraftOffline,
    runSync,
    isSyncing: loading,
  };
}
