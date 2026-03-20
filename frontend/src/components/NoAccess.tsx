'use client';

import { ShieldOff } from 'lucide-react';

interface NoAccessProps {
  message?: string;
}

export default function NoAccess({ message }: NoAccessProps) {
  return (
    <div data-testid="no-access-page" className="flex flex-col items-center justify-center h-[60vh] text-center px-4">
      <div className="w-16 h-16 rounded-full bg-red-50/80 flex items-center justify-center mb-5 ring-4 ring-red-100/50">
        <ShieldOff className="h-8 w-8 text-red-400" />
      </div>
      <h1 data-testid="no-access-title" className="text-xl font-bold text-gray-900 tracking-tight">
        Access Restricted
      </h1>
      <p className="text-gray-500 mt-2 max-w-sm leading-relaxed">
        {message || "You don't have permission to view this section."}
      </p>
      <p className="text-sm text-gray-400 mt-2">
        Please contact your admin to enable access.
      </p>
    </div>
  );
}
