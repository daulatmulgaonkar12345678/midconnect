'use client';

import { ShieldOff } from 'lucide-react';

export default function NoAccess() {
  return (
    <div data-testid="no-access-page" className="flex flex-col items-center justify-center h-[60vh] text-center px-4">
      <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <ShieldOff className="h-8 w-8 text-red-400" />
      </div>
      <h1 data-testid="no-access-title" className="text-xl font-bold text-gray-900">No Access</h1>
      <p className="text-gray-500 mt-2 max-w-sm">
        You don&apos;t have permission to view this section.
      </p>
      <p className="text-sm text-gray-400 mt-1">
        Please contact your admin to request access.
      </p>
    </div>
  );
}
