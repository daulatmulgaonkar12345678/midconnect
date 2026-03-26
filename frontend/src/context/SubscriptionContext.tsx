'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export interface PlanFeatures {
  maxPanels: number;
  maxRules: number;
  maxInvoicesPerMonth: number;
  maxEmployees: number;
  export: boolean;
  pdfExport: boolean;
  automation: boolean;
  maxSessions: number;
  label: string;
}

export interface SubscriptionStatus {
  plan: string;
  status: string;
  isExpired: boolean;
  features: PlanFeatures;
  endDate: string | null;
}

interface SubscriptionContextType {
  subscription: SubscriptionStatus | null;
  loading: boolean;
  canWrite: boolean;
  canExport: boolean;
  canAutomate: boolean;
  canExportPdf: boolean;
  planLabel: string;
  refresh: () => Promise<void>;
  checkLimit: (feature: string, currentCount: number) => { allowed: boolean; limit: number; message: string };
}

const defaultFeatures: PlanFeatures = {
  maxPanels: 3, maxRules: 10, maxInvoicesPerMonth: 10, maxEmployees: 0,
  export: false, pdfExport: false, automation: false, maxSessions: 1, label: 'Free',
};

const SubscriptionContext = createContext<SubscriptionContextType>({
  subscription: null,
  loading: true,
  canWrite: false,
  canExport: false,
  canAutomate: false,
  canExportPdf: false,
  planLabel: 'Free',
  refresh: async () => {},
  checkLimit: () => ({ allowed: true, limit: 0, message: '' }),
});

export function SubscriptionProvider({ children }: { children: React.ReactNode }) {
  const { getIdToken, isAuthenticated } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/api/subscription/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSubscription(await res.json());
      }
    } catch { /* silent */ }
    setLoading(false);
  }, [getIdToken]);

  useEffect(() => {
    if (isAuthenticated) {
      refresh();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated, refresh]);

  const features = subscription?.features || defaultFeatures;
  const isExpired = subscription?.isExpired ?? true;

  const canWrite = !isExpired;
  const canExport = !isExpired && features.export;
  const canAutomate = !isExpired && features.automation;
  const canExportPdf = !isExpired && features.pdfExport;
  const planLabel = features.label || subscription?.plan || 'Free';

  const checkLimit = useCallback(
    (feature: string, currentCount: number) => {
      const limitMap: Record<string, keyof PlanFeatures> = {
        create_panel: 'maxPanels',
        create_rule: 'maxRules',
        create_invoice: 'maxInvoicesPerMonth',
        add_employee: 'maxEmployees',
      };
      const key = limitMap[feature];
      if (!key) return { allowed: true, limit: -1, message: '' };

      const limit = features[key] as number;
      if (limit === -1) return { allowed: true, limit: -1, message: '' };

      if (currentCount >= limit) {
        return {
          allowed: false,
          limit,
          message: `You've reached the limit of ${limit} for your ${planLabel} plan. Upgrade to increase.`,
        };
      }
      return { allowed: true, limit, message: '' };
    },
    [features, planLabel]
  );

  return (
    <SubscriptionContext.Provider
      value={{ subscription, loading, canWrite, canExport, canAutomate, canExportPdf, planLabel, refresh, checkLimit }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  return useContext(SubscriptionContext);
}
