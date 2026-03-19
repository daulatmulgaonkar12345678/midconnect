'use client';

import React, { createContext, useContext, useEffect, useRef, useCallback, useState } from 'react';
import { useNetwork } from '@/hooks/useNetwork';
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

// Listeners that get called when we go online
type SyncListener = () => void;
const syncListeners: SyncListener[] = [];

export function registerSyncListener(fn: SyncListener) {
  syncListeners.push(fn);
  return () => {
    const idx = syncListeners.indexOf(fn);
    if (idx >= 0) syncListeners.splice(idx, 1);
  };
}

export function NetworkProvider({ children }: { children: React.ReactNode }) {
  const { isOnline } = useNetwork();
  const prevOnline = useRef(isOnline);
  const [syncState, setSyncState] = useState<SyncState>({
    pendingCount: 0,
    isSyncing: false,
    lastSyncTime: null,
  });

  const triggerSync = useCallback(() => {
    syncListeners.forEach(fn => fn());
  }, []);

  // Show toasts on network change
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
      // Trigger sync when coming back online
      setTimeout(() => triggerSync(), 500);
    }
  }, [isOnline, triggerSync]);

  return (
    <NetworkContext.Provider value={{ isOnline, syncState, setSyncState, triggerSync }}>
      {children}
    </NetworkContext.Provider>
  );
}
