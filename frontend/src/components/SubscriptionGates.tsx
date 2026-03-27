'use client';

import { useState, useCallback } from 'react';
import { useSubscription } from '@/context/SubscriptionContext';
import { AlertCircle, Lock, ArrowRight, Crown, X, Zap, Shield } from 'lucide-react';
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

/* ──────────────────────────────────────────────────────────
   UPGRADE MODAL — Formal popup for free/restricted users
   Shows when they attempt a gated action (create, download, etc.)
   ────────────────────────────────────────────────────────── */

interface UpgradeModalProps {
  open: boolean;
  onClose: () => void;
  feature?: string;
  title?: string;
  description?: string;
}

const FEATURE_LABELS: Record<string, { title: string; desc: string }> = {
  create_panel:   { title: 'Panel Creation', desc: 'Creating custom panels requires a paid plan.' },
  create_record:  { title: 'Record Creation', desc: 'Adding new records requires a paid plan.' },
  export_excel:   { title: 'Excel Export', desc: 'Exporting data to Excel requires a paid plan.' },
  export_pdf:     { title: 'PDF Export', desc: 'Exporting data to PDF requires a paid plan.' },
  create_invoice: { title: 'Invoice Creation', desc: 'Creating invoices requires a paid plan.' },
  automation:     { title: 'Automation', desc: 'Workflow automation requires a paid plan.' },
  add_employee:   { title: 'Team Management', desc: 'Adding team members requires a paid plan.' },
  download:       { title: 'Report Download', desc: 'Downloading reports requires a paid plan.' },
  write:          { title: 'This Action', desc: 'This action requires an active paid plan.' },
};

export function UpgradeModal({ open, onClose, feature, title, description }: UpgradeModalProps) {
  if (!open) return null;

  const featureInfo = feature ? FEATURE_LABELS[feature] : null;
  const displayTitle = title || featureInfo?.title || 'Feature Locked';
  const displayDesc = description || featureInfo?.desc || 'This feature requires a paid plan to access.';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="upgrade-modal">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header gradient */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 px-6 pt-8 pb-6 text-center relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition"
            data-testid="close-upgrade-modal"
          >
            <X className="h-4 w-4 text-white/80" />
          </button>
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Crown className="h-7 w-7 text-white" />
          </div>
          <h3 className="text-xl font-bold text-white">{displayTitle}</h3>
          <p className="text-sm text-slate-300 mt-2">{displayDesc}</p>
        </div>

        {/* Benefits */}
        <div className="px-6 py-5 space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Upgrade to unlock</p>
          {[
            { icon: Zap, label: 'Unlimited panels, records & invoices' },
            { icon: ArrowRight, label: 'Excel & PDF export for all reports' },
            { icon: Shield, label: 'Workflow automation & team access' },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                <Icon className="h-4 w-4 text-blue-600" />
              </div>
              <span className="text-sm text-gray-700">{label}</span>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="px-6 pb-6 flex gap-3">
          <Link
            href="/pricing"
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-violet-700 transition-all shadow-md"
            data-testid="upgrade-plan-btn"
          >
            <Crown className="h-4 w-4" /> View Plans
          </Link>
          <button
            onClick={onClose}
            className="px-4 py-3 border border-gray-200 text-gray-500 rounded-xl text-sm font-medium hover:bg-gray-50 transition"
            data-testid="maybe-later-btn"
          >
            Maybe Later
          </button>
        </div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────
   useUpgradeModal hook — Easy integration into any page
   ────────────────────────────────────────────────────────── */

export function useUpgradeModal() {
  const [modalState, setModalState] = useState<{ open: boolean; feature?: string }>({ open: false });
  const { canWrite, canExport, canAutomate, canExportPdf, subscription } = useSubscription();

  const isFree = !subscription || subscription.plan === 'free' || subscription.isExpired;

  const guardAction = useCallback((feature: string, action: () => void) => {
    const checks: Record<string, boolean> = {
      write: canWrite,
      create_panel: canWrite,
      create_record: canWrite,
      create_invoice: canWrite,
      add_employee: canWrite,
      export_excel: canExport,
      export_pdf: canExportPdf,
      download: canExport,
      automation: canAutomate,
    };

    const allowed = checks[feature] ?? canWrite;

    if (!allowed) {
      setModalState({ open: true, feature });
      return;
    }

    action();
  }, [canWrite, canExport, canExportPdf, canAutomate]);

  const closeModal = useCallback(() => setModalState({ open: false }), []);

  const UpgradeModalComponent = () => (
    <UpgradeModal open={modalState.open} onClose={closeModal} feature={modalState.feature} />
  );

  return { guardAction, isFree, UpgradeModal: UpgradeModalComponent };
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
