/**
 * Hook to manage offline draft invoices.
 * Provides: save draft locally, list offline drafts, delete draft.
 * Sync is handled centrally by NetworkContext.
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
} from '@/lib/offlineStore';
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

export function useOfflineInvoices(userId: string | null) {
  const { setSyncState } = useNetworkContext();
  const [offlineDrafts, setOfflineDrafts] = useState<OfflineDraftInvoice[]>([]);

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

  // Refresh drafts when sync completes (called by NetworkContext)
  useEffect(() => {
    const unregister = registerSyncListener(() => {
      loadDrafts();
    });
    return unregister;
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

  return {
    offlineDrafts,
    saveDraftOffline,
    updateDraftOffline,
    deleteDraftOffline,
  };
}
