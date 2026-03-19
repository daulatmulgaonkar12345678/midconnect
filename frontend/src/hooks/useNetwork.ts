'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

export type NetworkStatus = 'online' | 'offline';

interface UseNetworkReturn {
  isOnline: boolean;
  status: NetworkStatus;
  lastChanged: Date | null;
}

export function useNetwork(): UseNetworkReturn {
  const [isOnline, setIsOnline] = useState(true);
  const [lastChanged, setLastChanged] = useState<Date | null>(null);
  const initialized = useRef(false);

  const updateStatus = useCallback((online: boolean) => {
    setIsOnline(online);
    setLastChanged(new Date());
  }, []);

  useEffect(() => {
    // Set initial state from navigator
    if (!initialized.current) {
      setIsOnline(typeof navigator !== 'undefined' ? navigator.onLine : true);
      initialized.current = true;
    }

    const handleOnline = () => updateStatus(true);
    const handleOffline = () => updateStatus(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [updateStatus]);

  return {
    isOnline,
    status: isOnline ? 'online' : 'offline',
    lastChanged,
  };
}
