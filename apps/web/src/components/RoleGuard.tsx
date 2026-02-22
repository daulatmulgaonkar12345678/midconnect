'use client';

import { ReactNode } from 'react';
import { useAuth, UserRole } from '@/context/AuthContext';
import Link from 'next/link';
import { ShieldAlert, LogIn, Store } from 'lucide-react';

interface RoleGuardProps {
  children: ReactNode;
  allowedRoles: UserRole[];
  fallback?: ReactNode;
  showMessage?: boolean;
}

/**
 * Component to guard content based on user role
 * 
 * Usage:
 * <RoleGuard allowedRoles={['seller', 'admin']}>
 *   <SellerDashboard />
 * </RoleGuard>
 */
export default function RoleGuard({ 
  children, 
  allowedRoles, 
  fallback,
  showMessage = true 
}: RoleGuardProps) {
  const { role, loading } = useAuth();

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Check if user has required role
  const hasAccess = allowedRoles.includes(role);

  if (hasAccess) {
    return <>{children}</>;
  }

  // Show fallback if provided
  if (fallback) {
    return <>{fallback}</>;
  }

  // Show appropriate message based on role
  if (!showMessage) {
    return null;
  }

  if (role === 'guest') {
    return (
      <div className="text-center py-16 px-4">
        <LogIn className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Sign In Required</h2>
        <p className="text-gray-500 mb-6">Please sign in to access this feature</p>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
        >
          <LogIn className="h-5 w-5" /> Sign In
        </Link>
      </div>
    );
  }

  if (allowedRoles.includes('seller') && role === 'buyer') {
    return (
      <div className="text-center py-16 px-4">
        <Store className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Become a Seller</h2>
        <p className="text-gray-500 mb-6">Upgrade your account to access seller features</p>
        <Link
          href="/sell"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
        >
          <Store className="h-5 w-5" /> Start Selling
        </Link>
      </div>
    );
  }

  return (
    <div className="text-center py-16 px-4">
      <ShieldAlert className="h-16 w-16 text-gray-300 mx-auto mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 mb-2">Access Denied</h2>
      <p className="text-gray-500">You don't have permission to access this page</p>
    </div>
  );
}

/**
 * Higher-order component version of RoleGuard
 */
export function withRoleGuard<P extends object>(
  Component: React.ComponentType<P>,
  allowedRoles: UserRole[]
) {
  return function GuardedComponent(props: P) {
    return (
      <RoleGuard allowedRoles={allowedRoles}>
        <Component {...props} />
      </RoleGuard>
    );
  };
}
