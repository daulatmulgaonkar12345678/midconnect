'use client';

import { useEffect } from 'react';

export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        console.log('[PWA] Service Worker registered, scope:', registration.scope);

        registration.onupdatefound = () => {
          const installingWorker = registration.installing;
          if (!installingWorker) return;
          installingWorker.onstatechange = () => {
            if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New content available
              console.log('[PWA] New content available, will refresh on next visit');
            }
          };
        };
      })
      .catch((error) => {
        console.error('[PWA] Service Worker registration failed:', error);
      });
  }, []);

  return null;
}
