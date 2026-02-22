'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /dashboard/new-listing to /seller/listings/new
 * This maintains backward compatibility with existing links
 */
export default function DashboardNewListingRedirect() {
  const router = useRouter();
  
  useEffect(() => {
    router.replace('/seller/listings/new');
  }, [router]);
  
  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-500">Redirecting...</p>
    </div>
  );
}
