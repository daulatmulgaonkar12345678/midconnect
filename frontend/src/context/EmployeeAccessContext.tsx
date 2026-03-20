'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface ModulePermission {
  view: boolean;
  action: boolean;
}

interface EmployeeAccess {
  userId: string;
  role: string;
  status: string;
  permissions: Record<string, ModulePermission>;
  companyId: string | null;
  isAdmin: boolean;
}

interface EmployeeAccessContextType {
  access: EmployeeAccess | null;
  loading: boolean;
  refreshAccess: () => Promise<void>;
  canView: (module: string) => boolean;
  canAction: (module: string) => boolean;
  isFullAdmin: boolean;
  isDisabled: boolean;
  isUnlinked: boolean;
}

const defaultAccess: EmployeeAccess = {
  userId: '', role: 'unassigned', status: 'pending',
  permissions: {}, companyId: null, isAdmin: false,
};

const EmployeeAccessContext = createContext<EmployeeAccessContextType>({
  access: null, loading: true,
  refreshAccess: async () => {},
  canView: () => false,
  canAction: () => false,
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
        setAccess(data);
      }
    } catch {
      // silent
    }
    setLoading(false);
  }, [getIdToken]);

  // Fetch on mount and when user changes
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
      // Re-fetch access on any change
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
    if (!access) return false;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions[module]?.view === true;
  }, [access]);

  const canAction = useCallback((module: string) => {
    if (!access) return false;
    if (access.isAdmin) return true;
    if (access.status === 'disabled' || access.status === 'unlinked') return false;
    return access.permissions[module]?.view === true && access.permissions[module]?.action === true;
  }, [access]);

  const isDisabled = access?.status === 'disabled';
  const isUnlinked = access?.status === 'unlinked' || (!access?.isAdmin && !access?.companyId);

  return (
    <EmployeeAccessContext.Provider value={{
      access, loading, refreshAccess: fetchAccess,
      canView, canAction, isFullAdmin, isDisabled, isUnlinked,
    }}>
      {children}
    </EmployeeAccessContext.Provider>
  );
}
