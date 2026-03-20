/**
 * Offline Storage Service using IndexedDB (via `idb` library)
 *
 * Unified queue: all offline items (invoices, inventory, POs) stored in one store.
 * Each item follows the schema:
 *   { id, type, status, data, createdBy, createdAt, updatedAt }
 */

import { openDB, IDBPDatabase } from 'idb';

const DB_NAME = 'udyogconnect_offline';
const DB_VERSION = 1;
const QUEUE_STORE = 'offline_queue';
const CACHE_STORE = 'data_cache';

export type OfflineItemType = 'invoice' | 'inventory' | 'purchase_order' | 'quotation' | 'buyer';
export type OfflineItemStatus = 'draft_offline' | 'pending' | 'syncing' | 'synced' | 'failed';

export interface OfflineItem {
  id: string;
  type: OfflineItemType;
  status: OfflineItemStatus;
  data: Record<string, unknown>;
  createdBy: string;
  createdAt: number;
  updatedAt: number;
  syncAttempts?: number;
  lastError?: string;
}

export interface CacheItem {
  key: string;
  data: unknown;
  updatedAt: number;
}

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('IndexedDB not available on server'));
  }
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // Unified offline queue
        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          const store = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' });
          store.createIndex('by_status', 'status');
          store.createIndex('by_type', 'type');
          store.createIndex('by_created', 'createdBy');
          store.createIndex('by_updated', 'updatedAt');
        }
        // Cache store for seller listings, etc.
        if (!db.objectStoreNames.contains(CACHE_STORE)) {
          db.createObjectStore(CACHE_STORE, { keyPath: 'key' });
        }
      },
    });
  }
  return dbPromise;
}

// ─── Temp ID generation ───
export function generateTempId(userId: string): string {
  return `temp_${userId}_${Date.now()}`;
}

// ─── Queue operations ───

export async function addOfflineItem(item: Omit<OfflineItem, 'createdAt' | 'updatedAt' | 'syncAttempts'>): Promise<OfflineItem> {
  const db = await getDB();
  const now = Date.now();
  const fullItem: OfflineItem = {
    ...item,
    createdAt: now,
    updatedAt: now,
    syncAttempts: 0,
  };
  await db.put(QUEUE_STORE, fullItem);
  return fullItem;
}

export async function updateOfflineItem(id: string, updates: Partial<OfflineItem>): Promise<void> {
  const db = await getDB();
  const existing = await db.get(QUEUE_STORE, id);
  if (!existing) return;
  const updated = { ...existing, ...updates, updatedAt: Date.now() };
  await db.put(QUEUE_STORE, updated);
}

export async function getOfflineItem(id: string): Promise<OfflineItem | undefined> {
  const db = await getDB();
  return db.get(QUEUE_STORE, id);
}

export async function deleteOfflineItem(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(QUEUE_STORE, id);
}

export async function getAllOfflineItems(): Promise<OfflineItem[]> {
  const db = await getDB();
  return db.getAll(QUEUE_STORE);
}

export async function getItemsByStatus(status: OfflineItemStatus): Promise<OfflineItem[]> {
  const db = await getDB();
  return db.getAllFromIndex(QUEUE_STORE, 'by_status', status);
}

export async function getItemsByType(type: OfflineItemType): Promise<OfflineItem[]> {
  const db = await getDB();
  return db.getAllFromIndex(QUEUE_STORE, 'by_type', type);
}

export async function getItemsByUser(userId: string): Promise<OfflineItem[]> {
  const db = await getDB();
  return db.getAllFromIndex(QUEUE_STORE, 'by_created', userId);
}

export async function getPendingItems(): Promise<OfflineItem[]> {
  const db = await getDB();
  const drafts = await db.getAllFromIndex(QUEUE_STORE, 'by_status', 'draft_offline');
  const pending = await db.getAllFromIndex(QUEUE_STORE, 'by_status', 'pending');
  const failed = await db.getAllFromIndex(QUEUE_STORE, 'by_status', 'failed');
  return [...drafts, ...pending, ...failed];
}

export async function getPendingCount(): Promise<number> {
  const items = await getPendingItems();
  return items.length;
}

export async function clearSyncedItems(): Promise<void> {
  const db = await getDB();
  const synced = await db.getAllFromIndex(QUEUE_STORE, 'by_status', 'synced');
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  for (const item of synced) {
    await tx.store.delete(item.id);
  }
  await tx.done;
}

// ─── Cache operations (for seller listings, inventory, etc.) ───

export async function cacheData(key: string, data: unknown): Promise<void> {
  const db = await getDB();
  await db.put(CACHE_STORE, { key, data, updatedAt: Date.now() });
}

export async function getCachedData<T = unknown>(key: string): Promise<T | null> {
  const db = await getDB();
  const item = await db.get(CACHE_STORE, key);
  return item ? (item.data as T) : null;
}

export async function clearCache(): Promise<void> {
  const db = await getDB();
  await db.clear(CACHE_STORE);
}
