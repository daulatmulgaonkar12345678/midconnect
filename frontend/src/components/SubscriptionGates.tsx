'use client';

import { useSubscription } from '@/context/SubscriptionContext';
import { AlertCircle, Lock, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export function SubscriptionBanner() {
  const { subscription, loading } = useSubscription();

  if (loading || !subscription?.isExpired) return null;

  return (
    <div
      className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 flex items-center justify-between gap-4"
      data-testid="subscription-expired-banner"
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
          <AlertCircle className="w-5 h-5 text-amber-600" />
        </div>
        <div>
          <p className="text-sm font-semibold text-amber-800">Your plan has expired</p>
          <p className="text-xs text-amber-600">Renew to continue editing, exporting, and running automations.</p>
        </div>
      </div>
      <Link
        href="/pricing"
        className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors whitespace-nowrap"
        data-testid="renew-plan-btn"
      >
        Renew Plan <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}

export function FeatureGate({ feature, children, fallback }: { feature: string; children: React.ReactNode; fallback?: React.ReactNode }) {
  const { subscription, canWrite, canExport, canAutomate, canExportPdf } = useSubscription();

  const featureChecks: Record<string, boolean> = {
    write: canWrite,
    export: canExport,
    export_excel: canExport,
    export_pdf: canExportPdf,
    automation: canAutomate,
  };

  const allowed = featureChecks[feature] ?? canWrite;

  if (allowed) return <>{children}</>;

  if (fallback) return <>{fallback}</>;

  return (
    <div className="relative group">
      <div className="opacity-50 pointer-events-none select-none">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="bg-gray-900/90 text-white px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 shadow-lg">
          <Lock className="w-3 h-3" /> Upgrade to unlock
        </div>
      </div>
    </div>
  );
}

export function LimitIndicator({ feature, current }: { feature: string; current: number }) {
  const { checkLimit, planLabel } = useSubscription();
  const { allowed, limit, message } = checkLimit(feature, current);

  if (limit === -1) return null;

  const percentage = limit > 0 ? Math.round((current / limit) * 100) : 0;
  const isNearLimit = percentage >= 80;
  const isAtLimit = !allowed;

  return (
    <div className="flex items-center gap-2 text-xs" data-testid={`limit-indicator-${feature}`}>
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden max-w-[80px]">
        <div
          className={`h-full rounded-full transition-all ${isAtLimit ? 'bg-red-500' : isNearLimit ? 'bg-amber-500' : 'bg-blue-500'}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className={`font-medium ${isAtLimit ? 'text-red-600' : isNearLimit ? 'text-amber-600' : 'text-gray-500'}`}>
        {current}/{limit}
      </span>
      {isAtLimit && (
        <Link
          href="/pricing"
          className="text-blue-600 font-medium hover:text-blue-700"
        >
          Upgrade
        </Link>
      )}
    </div>
  );
}
