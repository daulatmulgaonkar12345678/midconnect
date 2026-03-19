'use client';

import React, { createContext, useContext, useEffect, useRef, useCallback, useState } from 'react';
import { useNetwork } from '@/hooks/useNetwork';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';

interface SyncState {
  pendingCount: number;
  isSyncing: boolean;
  lastSyncTime: Date | null;
}

interface NetworkContextType {
  isOnline: boolean;
  syncState: SyncState;
  setSyncState: React.Dispatch<React.SetStateAction<SyncState>>;
  triggerSync: () => void;
}

const NetworkContext = createContext<NetworkContextType>({
  isOnline: true,
  syncState: { pendingCount: 0, isSyncing: false, lastSyncTime: null },
  setSyncState: () => {},
  triggerSync: () => {},
});

export function useNetworkContext() {
  return useContext(NetworkContext);
}

// External listeners for pages that want to know when sync completes
type SyncListener = () => void;
const postSyncListeners: SyncListener[] = [];

export function registerSyncListener(fn: SyncListener) {
  postSyncListeners.push(fn);
  return () => {
    const idx = postSyncListeners.indexOf(fn);
    if (idx >= 0) postSyncListeners.splice(idx, 1);
  };
}

export function NetworkProvider({ children }: { children: React.ReactNode }) {
  const { isOnline } = useNetwork();
  const { getIdToken } = useAuth();
  const prevOnline = useRef(isOnline);
  const syncRunning = useRef(false);
  const [syncState, setSyncState] = useState<SyncState>({
    pendingCount: 0,
    isSyncing: false,
    lastSyncTime: null,
  });

  // Load pending count on mount
  useEffect(() => {
    (async () => {
      try {
        const { getPendingCount } = await import('@/lib/offlineStore');
        const count = await getPendingCount();
        setSyncState(prev => ({ ...prev, pendingCount: count }));
      } catch {
        // IndexedDB not available (SSR or first load)
      }
    })();
  }, []);

  // Core sync function — runs the sync engine directly
  const runSync = useCallback(async () => {
    if (syncRunning.current || !isOnline) return;
    syncRunning.current = true;

    try {
      const token = await getIdToken();
      if (!token) {
        syncRunning.current = false;
        return;
      }

      const { processOfflineQueue } = await import('@/lib/syncEngine');
      const result = await processOfflineQueue(token, (state) => {
        setSyncState(state);
      });

      if (result.synced > 0) {
        toast.success(`${result.synced} offline item${result.synced > 1 ? 's' : ''} synced successfully`);
      }
      if (result.failed > 0) {
        toast.error(`${result.failed} item${result.failed > 1 ? 's' : ''} failed to sync. Will retry.`);
      }

      // Notify any page-level listeners that sync is done (e.g., refresh invoice list)
      postSyncListeners.forEach(fn => fn());
    } catch {
      toast.error('Sync failed. Will retry automatically.');
    }

    syncRunning.current = false;
  }, [isOnline, getIdToken]);

  const triggerSync = useCallback(() => {
    runSync();
  }, [runSync]);

  // Show toasts on network change and auto-sync
  useEffect(() => {
    if (prevOnline.current === isOnline) return;
    prevOnline.current = isOnline;

    if (!isOnline) {
      toast.warning('You are offline. Changes will be saved locally', {
        id: 'network-status',
        duration: 5000,
      });
    } else {
      toast.success('Back online. Syncing data...', {
        id: 'network-status',
        duration: 3000,
      });
      // Auto-sync when coming back online
      setTimeout(() => runSync(), 800);
    }
  }, [isOnline, runSync]);

  // Auto-sync on mount if there are pending items
  useEffect(() => {
    if (isOnline && syncState.pendingCount > 0 && !syncState.isSyncing) {
      // Small delay to let auth settle
      const timer = setTimeout(() => runSync(), 2000);
      return () => clearTimeout(timer);
    }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <NetworkContext.Provider value={{ isOnline, syncState, setSyncState, triggerSync }}>
      {children}
    </NetworkContext.Provider>
  );
}
