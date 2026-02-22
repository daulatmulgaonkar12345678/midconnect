/**
 * Custom hooks for API calls with loading, error, and data states
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { ApiError } from '@/types/api';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: (...args: unknown[]) => Promise<T | null>;
  reset: () => void;
}

/**
 * Hook for public API calls (no auth required)
 */
export function usePublicApi<T>(
  apiFunction: (...args: unknown[]) => Promise<T>
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (...args: unknown[]): Promise<T | null> => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const result = await apiFunction(...args);
      setState({ data: result, loading: false, error: null });
      return result;
    } catch (error) {
      const message = error instanceof ApiError 
        ? error.getUserMessage() 
        : 'An error occurred';
      setState({ data: null, loading: false, error: message });
      return null;
    }
  }, [apiFunction]);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

/**
 * Hook for authenticated API calls
 */
export function useAuthApi<T>(
  apiFunction: (token: string, ...args: unknown[]) => Promise<T>
): UseApiReturn<T> {
  const { getIdToken, signOut } = useAuth();
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (...args: unknown[]): Promise<T | null> => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const token = await getIdToken();
      if (!token) {
        throw new ApiError('Authentication required', 401);
      }
      
      const result = await apiFunction(token, ...args);
      setState({ data: result, loading: false, error: null });
      return result;
    } catch (error) {
      // Handle auth errors by signing out
      if (error instanceof ApiError && error.isAuthError()) {
        await signOut();
      }
      
      const message = error instanceof ApiError 
        ? error.getUserMessage() 
        : 'An error occurred';
      setState({ data: null, loading: false, error: message });
      return null;
    }
  }, [apiFunction, getIdToken, signOut]);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

/**
 * Hook for role-based API calls
 */
export function useRoleApi<T>(
  requiredRole: 'buyer' | 'seller' | 'admin',
  apiFunction: (token: string, ...args: unknown[]) => Promise<T>
): UseApiReturn<T> & { hasPermission: boolean } {
  const { role, getIdToken, signOut } = useAuth();
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  // Check role hierarchy
  const hasPermission = (() => {
    if (role === 'admin') return true;
    if (role === 'seller' && (requiredRole === 'seller' || requiredRole === 'buyer')) return true;
    if (role === 'buyer' && requiredRole === 'buyer') return true;
    return false;
  })();

  const execute = useCallback(async (...args: unknown[]): Promise<T | null> => {
    if (!hasPermission) {
      setState({ data: null, loading: false, error: 'Permission denied' });
      return null;
    }

    setState({ data: null, loading: true, error: null });
    
    try {
      const token = await getIdToken();
      if (!token) {
        throw new ApiError('Authentication required', 401);
      }
      
      const result = await apiFunction(token, ...args);
      setState({ data: result, loading: false, error: null });
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.isAuthError()) {
        await signOut();
      }
      
      const message = error instanceof ApiError 
        ? error.getUserMessage() 
        : 'An error occurred';
      setState({ data: null, loading: false, error: message });
      return null;
    }
  }, [apiFunction, getIdToken, signOut, hasPermission]);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset, hasPermission };
}
