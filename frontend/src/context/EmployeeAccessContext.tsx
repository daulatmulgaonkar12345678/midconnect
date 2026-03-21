'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface PanelPerm {
  canView: boolean;
  canCreate: boolean;
  canEdit: boolean;
}

interface EmployeePermissions {
  modules: Record<string, boolean>;
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

const defaultPermissions: EmployeePermissions = {
  modules: {},
  panels: {},
};

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
        // Ensure permissions has the new structure
        const perms = data.permissions || {};
        if (!perms.modules) {
          // Backward compat: old format
          const modules: Record<string, boolean> = {};
          for (const [k, v] of Object.entries(perms)) {
            if (k === 'modules' || k === 'panels') continue;
            const val = v as Record<string, boolean>;
            modules[k] = val?.view === true;
          }
          data.permissions = { modules, panels: {} };
        }
        data.permittedPanels = data.permittedPanels || [];
        setAccess(data);
      }
    } catch {
      // silent
    }
    setLoading(false);
  }, [getIdToken]);

  useEffect(() => {
    if (user) {
      fetchAccess();
    } else {
      setAccess(null);
      setLoading(false);
    }
  }, [user, fetchAccess]);

  // Socket.IO real-time listener
  useEffect(() => {
    if (!access?.userId) return;

    const socket = io(API_URL, {
      path: '/api/socket.io/',
      transports: ['polling', 'websocket'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 3000,
      reconnectionDelayMax: 30000,
      timeout: 10000,
    });

    socket.on('connect', () => {
      socket.emit('join_user_room', { userId: access.userId });
    });

    socket.on('access_updated', () => {
      fetchAccess();
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [access?.userId, fetchAccess]);

  const isFullAdmin = access?.isAdmin === true;

  const canView = useCallback((module: string) => {
    if (loading) return true;
    if (!access) return true;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.modules?.[module] === true;
  }, [access, loading]);

  const canAction = useCallback((module: string) => {
    if (loading) return true;
    if (!access) return true;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    // New format: module=true means full access (view+action)
    return access.permissions?.modules?.[module] === true;
  }, [access, loading]);

  const canViewPanel = useCallback((panelId: string) => {
    if (loading) return true;
    if (!access) return true;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.panels?.[panelId]?.canView === true;
  }, [access, loading]);

  const canCreatePanel = useCallback((panelId: string) => {
    if (loading) return true;
    if (!access) return true;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.panels?.[panelId]?.canCreate === true;
  }, [access, loading]);

  const canEditPanel = useCallback((panelId: string) => {
    if (loading) return true;
    if (!access) return true;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions?.panels?.[panelId]?.canEdit === true;
  }, [access, loading]);

  const isDisabled = access?.status === 'disabled';
  const isUnlinked = access?.status === 'unlinked' || (!access?.isAdmin && !access?.companyId);

  return (
    <EmployeeAccessContext.Provider value={{
      access, loading, refreshAccess: fetchAccess,
      canView, canAction,
      canViewPanel, canCreatePanel, canEditPanel,
      isFullAdmin, isDisabled, isUnlinked,
    }}>
      {children}
    </EmployeeAccessContext.Provider>
  );
}
