/**
 * Sync Engine — processes the offline queue when back online.
 *
 * Rules:
 *   - Draft invoices → POST to server, server generates real ID & invoice number
 *   - NEVER update existing server records using temp IDs
 *   - Sequential processing to avoid race conditions
 *   - Retry with backoff on failure
 */

import {
  getPendingItems,
  updateOfflineItem,
  deleteOfflineItem,
  getPendingCount,
  OfflineItem,
} from './offlineStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export interface SyncResult {
  total: number;
  synced: number;
  failed: number;
  errors: Array<{ id: string; error: string }>;
}

type SyncStateUpdater = (state: {
  pendingCount: number;
  isSyncing: boolean;
  lastSyncTime: Date | null;
}) => void;

/**
 * Process all pending offline items sequentially.
 * Returns a SyncResult summary.
 */
export async function processOfflineQueue(
  token: string,
  onStateChange?: SyncStateUpdater
): Promise<SyncResult> {
  const items = await getPendingItems();
  const result: SyncResult = { total: items.length, synced: 0, failed: 0, errors: [] };

  if (items.length === 0) {
    onStateChange?.({ pendingCount: 0, isSyncing: false, lastSyncTime: new Date() });
    return result;
  }

  onStateChange?.({
    pendingCount: items.length,
    isSyncing: true,
    lastSyncTime: null,
  });

  for (const item of items) {
    try {
      await updateOfflineItem(item.id, { status: 'syncing' });
      await syncItem(item, token);
      // On success, remove from queue
      await deleteOfflineItem(item.id);
      result.synced++;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      const attempts = (item.syncAttempts || 0) + 1;
      await updateOfflineItem(item.id, {
        status: 'failed',
        syncAttempts: attempts,
        lastError: errorMsg,
      });
      result.failed++;
      result.errors.push({ id: item.id, error: errorMsg });
    }

    // Update pending count after each item
    const remaining = await getPendingCount();
    onStateChange?.({
      pendingCount: remaining,
      isSyncing: true,
      lastSyncTime: null,
    });
  }

  const finalPending = await getPendingCount();
  onStateChange?.({
    pendingCount: finalPending,
    isSyncing: false,
    lastSyncTime: new Date(),
  });

  return result;
}

/**
 * Sync a single offline item to the server.
 */
async function syncItem(item: OfflineItem, token: string): Promise<void> {
  switch (item.type) {
    case 'invoice':
      await syncInvoice(item, token);
      break;
    case 'inventory':
      await syncInventoryUpdate(item, token);
      break;
    case 'purchase_order':
      await syncPurchaseOrder(item, token);
      break;
    default:
      throw new Error(`Unknown item type: ${item.type}`);
  }
}

/**
 * Sync a draft invoice — creates a NEW invoice on the server.
 * Server will generate the real invoice ID and number.
 */
async function syncInvoice(item: OfflineItem, token: string): Promise<void> {
  const invoiceData = item.data;

  // Strip temp fields before sending to server
  const payload = { ...invoiceData };
  delete payload._tempId;
  delete payload._offlineCreated;

  const res = await fetch(`${API_URL}/api/invoices/sync-offline-draft`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Server error ${res.status}`);
  }
}

/**
 * Sync an inventory update.
 */
async function syncInventoryUpdate(item: OfflineItem, token: string): Promise<void> {
  const data = item.data;
  const res = await fetch(`${API_URL}/api/business-tools/inventory/${data.productId}/stock`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ stock: data.newStock }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Server error ${res.status}`);
  }
}

/**
 * Sync a purchase order.
 */
async function syncPurchaseOrder(item: OfflineItem, token: string): Promise<void> {
  const payload = { ...item.data };
  delete payload._tempId;
  delete payload._offlineCreated;

  const res = await fetch(`${API_URL}/api/business-tools/purchase-orders`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Server error ${res.status}`);
  }
}

/**
 * Retry failed items with exponential backoff.
 */
export async function retryFailedItems(
  token: string,
  maxRetries: number = 3,
  onStateChange?: SyncStateUpdater
): Promise<SyncResult> {
  const items = await getPendingItems();
  const failedItems = items.filter(
    (i) => i.status === 'failed' && (i.syncAttempts || 0) < maxRetries
  );

  const result: SyncResult = { total: failedItems.length, synced: 0, failed: 0, errors: [] };

  if (failedItems.length === 0) return result;

  onStateChange?.({
    pendingCount: failedItems.length,
    isSyncing: true,
    lastSyncTime: null,
  });

  for (const item of failedItems) {
    // Exponential backoff: 1s, 2s, 4s
    const backoff = Math.pow(2, item.syncAttempts || 0) * 1000;
    await new Promise((r) => setTimeout(r, backoff));

    try {
      await updateOfflineItem(item.id, { status: 'syncing' });
      await syncItem(item, token);
      await deleteOfflineItem(item.id);
      result.synced++;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      await updateOfflineItem(item.id, {
        status: 'failed',
        syncAttempts: (item.syncAttempts || 0) + 1,
        lastError: errorMsg,
      });
      result.failed++;
      result.errors.push({ id: item.id, error: errorMsg });
    }
  }

  const finalPending = await getPendingCount();
  onStateChange?.({
    pendingCount: finalPending,
    isSyncing: false,
    lastSyncTime: new Date(),
  });

  return result;
}
