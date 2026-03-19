'use client';

import { useNetworkContext } from '@/context/NetworkContext';
import { Wifi, WifiOff, RefreshCw, CloudUpload } from 'lucide-react';

export default function NetworkStatusBanner() {
  const { isOnline, syncState, triggerSync } = useNetworkContext();

  // Online with nothing pending — don't show banner
  if (isOnline && syncState.pendingCount === 0 && !syncState.isSyncing) {
    return null;
  }

  // Syncing state
  if (isOnline && syncState.isSyncing) {
    return (
      <div
        data-testid="network-syncing-banner"
        className="bg-blue-600 text-white text-xs sm:text-sm font-medium px-4 py-1.5 flex items-center justify-center gap-2"
      >
        <CloudUpload className="h-3.5 w-3.5 animate-pulse" />
        <span>Uploading offline data...</span>
      </div>
    );
  }

  // Online but has pending items
  if (isOnline && syncState.pendingCount > 0) {
    return (
      <div
        data-testid="network-pending-banner"
        className="bg-amber-500 text-white text-xs sm:text-sm font-medium px-4 py-1.5 flex items-center justify-center gap-2"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        <span>{syncState.pendingCount} item{syncState.pendingCount > 1 ? 's' : ''} pending sync</span>
        <button
          onClick={triggerSync}
          className="ml-2 underline hover:no-underline text-xs"
          data-testid="manual-sync-btn"
        >
          Sync now
        </button>
      </div>
    );
  }

  // Offline
  if (!isOnline) {
    return (
      <div
        data-testid="network-offline-banner"
        className="bg-red-600 text-white text-xs sm:text-sm font-medium px-4 py-1.5 flex items-center justify-center gap-2"
      >
        <WifiOff className="h-3.5 w-3.5" />
        <span>Offline Mode</span>
        {syncState.pendingCount > 0 && (
          <span className="opacity-80">
            &middot; {syncState.pendingCount} unsaved change{syncState.pendingCount > 1 ? 's' : ''}
          </span>
        )}
      </div>
    );
  }

  return null;
}
