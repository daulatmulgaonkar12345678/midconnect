'use client';

import { useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

export default function ServerWarmUp() {
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    // Only warm up once per session
    if (typeof window !== 'undefined' && sessionStorage.getItem('serverWarmed')) {
      return;
    }

    const warmUpServer = async () => {
      const startTime = Date.now();
      setIsWarmingUp(true);

      // Show banner if warm-up takes longer than 1.5 seconds
      const bannerTimeout = setTimeout(() => {
        setShowBanner(true);
      }, 1500);

      try {
        const healthUrl = API_URL ? `${API_URL}/api/health` : '/api/health';
        const response = await fetch(healthUrl, {
          method: 'GET',
          cache: 'no-store',
        });

        if (response.ok) {
          const duration = Date.now() - startTime;
          console.log(`Server warm-up completed in ${duration}ms`);
          
          // Mark as warmed for this session
          if (typeof window !== 'undefined') {
            sessionStorage.setItem('serverWarmed', 'true');
          }
        }
      } catch (error) {
        console.warn('Backend warm-up failed:', error);
      } finally {
        clearTimeout(bannerTimeout);
        setIsWarmingUp(false);
        setShowBanner(false);
      }
    };

    warmUpServer();
  }, []);

  // Show connecting banner only if it's taking too long
  if (showBanner && isWarmingUp) {
    return (
      <div className="fixed top-0 left-0 right-0 z-[9999] bg-blue-600 text-white py-2 px-4 text-center text-sm">
        <div className="flex items-center justify-center gap-2">
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          <span>Connecting to secure marketplace server...</span>
        </div>
      </div>
    );
  }

  return null;
}
