'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface ModulePerm {
  view: boolean;
  edit: boolean;
}

interface PanelPerm {
  canView: boolean;
  canCreate: boolean;
  canEdit: boolean;
}

interface EmployeePermissions {
  modules: Record<string, ModulePerm>;
  panels: Record<string, PanelPerm>;
}

interface PermittedPanel {
  id: string;
  name: string;
  color: string;
  slug: string;
}

interface EmployeeAccess {
  userId: string;
  role: string;
  status: string;
  permissions: EmployeePermissions;
  companyId: string | null;
  isAdmin: boolean;
  companyName: string;
  companyLogoUrl: string;
  permittedPanels: PermittedPanel[];
}

interface EmployeeAccessContextType {
  access: EmployeeAccess | null;
  loading: boolean;
  refreshAccess: () => Promise<void>;
  canView: (module: string) => boolean;
  canAction: (module: string) => boolean;
  canViewPanel: (panelId: string) => boolean;
  canCreatePanel: (panelId: string) => boolean;
  canEditPanel: (panelId: string) => boolean;
  isFullAdmin: boolean;
  isDisabled: boolean;
  isUnlinked: boolean;
}

const EmployeeAccessContext = createContext<EmployeeAccessContextType>({
  access: null, loading: true,
  refreshAccess: async () => {},
  canView: () => false,
  canAction: () => false,
  canViewPanel: () => false,
  canCreatePanel: () => false,
  canEditPanel: () => false,
  isFullAdmin: false,
  isDisabled: false,
  isUnlinked: false,
});

export const useEmployeeAccess = () => useContext(EmployeeAccessContext);

function normalizeModulePerms(raw: Record<string, unknown>): Record<string, ModulePerm> {
  const result: Record<string, ModulePerm> = {};
  for (const [k, v] of Object.entries(raw)) {
    if (typeof v === 'boolean') {
      result[k] = { view: v, edit: v };
    } else if (v && typeof v === 'object' && ('view' in v || 'edit' in v)) {
      const obj = v as Record<string, boolean>;
      result[k] = { view: obj.view === true, edit: obj.edit === true };
    } else if (v && typeof v === 'object' && ('action' in v)) {
      // Old format
      const obj = v as Record<string, boolean>;
      result[k] = { view: obj.view === true, edit: obj.action === true };
    }
  }
  return result;
}

export function EmployeeAccessProvider({ children }: { children: React.ReactNode }) {
  const { getIdToken, user } = useAuth();
  const [access, setAccess] = useState<EmployeeAccess | null>(null);
  const [loading, setLoading] = useState(true);
  const socketRef = useRef<Socket | null>(null);

  const fetchAccess = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) { setLoading(false); return; }
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/my-access`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const perms = data.permissions || {};
        // Normalize modules to {view, edit} format
        if (perms.modules) {
          perms.modules = normalizeModulePerms(perms.modules);
        } else {
          // Old flat format - convert
          const modules: Record<string, ModulePerm> = {};
          for (const [k, v] of Object.entries(perms)) {
            if (k === 'modules' || k === 'panels') continue;
            if (v && typeof v === 'object') {
              const obj = v as Record<string, boolean>;
              modules[k] = { view: obj.view === true, edit: obj.action === true || obj.edit === true };
            }
          }
          perms.modules = modules;
          if (!perms.panels) perms.panels = {};
        }
        data.permissions = perms;
        data.permittedPanels = data.permittedPanels || [];
        setAccess(data);
      }
    } catch {
      // silent
    }
    setLoading(false);
  }, [getIdToken]);

  useEffect(() => {
    if (user) { fetchAccess(); } else { setAccess(null); setLoading(false); }
  }, [user, fetchAccess]);

  useEffect(() => {
    if (!access?.userId) return;
    const socket = io(API_URL, {
      path: '/api/socket.io/',
      transports: ['polling', 'websocket'],
      reconnection: true, reconnectionAttempts: 10,
      reconnectionDelay: 3000, reconnectionDelayMax: 30000, timeout: 10000,
    });
    socket.on('connect', () => { socket.emit('join_user_room', { userId: access.userId }); });
    socket.on('access_updated', () => { fetchAccess(); });
    socketRef.current = socket;
    return () => { socket.disconnect(); socketRef.current = null; };
  }, [access?.userId, fetchAccess]);

  const isFullAdmin = access?.isAdmin === true;

  const canView = useCallback((module: string) => {
    if (loading || !access || access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    const mp = access.permissions?.modules?.[module];
    if (!mp) return false;
    if (typeof mp === 'boolean') return mp;
    return mp.view === true;
  }, [access, loading]);

  const canAction = useCallback((module: string) => {
    if (loading || !access || access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    const mp = access.permissions?.modules?.[module];
    if (!mp) return false;
    if (typeof mp === 'boolean') return mp;
    return mp.edit === true;
  }, [access, loading]);

  const canViewPanel = useCallback((panelId: string) => {
    if (loading || !access || access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.panels?.[panelId]?.canView === true;
  }, [access, loading]);

  const canCreatePanel = useCallback((panelId: string) => {
    if (loading || !access || access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.panels?.[panelId]?.canCreate === true;
  }, [access, loading]);

  const canEditPanel = useCallback((panelId: string) => {
    if (loading || !access || access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.panels?.[panelId]?.canEdit === true;
  }, [access, loading]);

  const isDisabled = access?.status === 'disabled';
  const isUnlinked = access?.status === 'unlinked' || (!access?.isAdmin && !access?.companyId);

  return (
    <EmployeeAccessContext.Provider value={{
      access, loading, refreshAccess: fetchAccess,
      canView, canAction, canViewPanel, canCreatePanel, canEditPanel,
      isFullAdmin, isDisabled, isUnlinked,
    }}>
      {children}
    </EmployeeAccessContext.Provider>
  );
}
