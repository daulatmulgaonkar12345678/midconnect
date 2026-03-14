'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { 
  Package2,
  Users,
  Truck,
  FileText,
  Layers,
  BarChart3,
  UserCog,
  Shield,
  Activity,
  ChevronLeft,
  Loader2,
  Menu,
  X
} from 'lucide-react';

// Permission context for access control
interface PermissionContextType {
  permissions: string[];
  isAdmin: boolean;
  hasPermission: (permission: string) => boolean;
  loading: boolean;
  token: string | null;
}

const PermissionContext = createContext<PermissionContextType>({
  permissions: [],
  isAdmin: false,
  hasPermission: () => false,
  loading: true,
  token: null
});

export const usePermissions = () => useContext(PermissionContext);

// Business Tools navigation items
const navItems = [
  { 
    href: '/seller/business-tools/inventory', 
    label: 'Inventory', 
    icon: Package2,
    permission: 'manage_inventory',
    color: 'blue'
  },
  { 
    href: '/seller/business-tools/buyers', 
    label: 'Buyers', 
    icon: Users,
    permission: 'manage_buyers',
    color: 'green'
  },
  { 
    href: '/seller/business-tools/suppliers', 
    label: 'Suppliers', 
    icon: Truck,
    permission: 'manage_suppliers',
    color: 'purple'
  },
  { 
    href: '/seller/business-tools/invoices', 
    label: 'Invoices', 
    icon: FileText,
    permission: 'create_invoice',
    color: 'orange'
  },
  { 
    href: '/seller/business-tools/composite-products', 
    label: 'Composite Products', 
    icon: Layers,
    permission: 'manage_inventory',
    color: 'pink'
  },
  { 
    href: '/seller/business-tools/reports', 
    label: 'Reports', 
    icon: BarChart3,
    permission: 'view_reports',
    color: 'cyan'
  },
  { 
    href: '/seller/business-tools/employees', 
    label: 'Employees', 
    icon: UserCog,
    permission: 'manage_employees',
    color: 'amber'
  },
  { 
    href: '/seller/business-tools/roles', 
    label: 'Roles & Permissions', 
    icon: Shield,
    permission: 'manage_roles',
    color: 'red'
  },
  { 
    href: '/seller/business-tools/activity-logs', 
    label: 'Activity Logs', 
    icon: Activity,
    permission: 'manage_roles',
    color: 'slate'
  }
];

export default function BusinessToolsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, getIdToken, loading: authLoading } = useAuth();
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  const loadPermissions = useCallback(async () => {
    try {
      const idToken = await getIdToken();
      if (!idToken) {
        router.push('/login');
        return;
      }
      setToken(idToken);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/my-permissions`,
        {
          headers: { Authorization: `Bearer ${idToken}` }
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          router.push('/login');
          return;
        }
        throw new Error('Failed to load permissions');
      }

      const data = await response.json();
      setPermissions(data.permissions || []);
      setIsAdmin(data.isAdmin || false);
    } catch (err) {
      console.error('Error loading permissions:', err);
    } finally {
      setLoading(false);
    }
  }, [getIdToken, router]);

  useEffect(() => {
    if (!authLoading && user) {
      loadPermissions();
    } else if (!authLoading && !user) {
      router.push('/login');
    }
  }, [authLoading, user, loadPermissions, router]);

  const hasPermission = useCallback((permission: string) => {
    return isAdmin || permissions.includes(permission);
  }, [isAdmin, permissions]);

  // Filter nav items based on permissions
  const visibleNavItems = navItems.filter(item => hasPermission(item.permission));

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const getColorClasses = (color: string, isActive: boolean) => {
    const colors: Record<string, { active: string; inactive: string }> = {
      blue: { active: 'bg-blue-100 text-blue-700 border-blue-500', inactive: 'text-gray-600 hover:bg-blue-50 hover:text-blue-600' },
      green: { active: 'bg-green-100 text-green-700 border-green-500', inactive: 'text-gray-600 hover:bg-green-50 hover:text-green-600' },
      purple: { active: 'bg-purple-100 text-purple-700 border-purple-500', inactive: 'text-gray-600 hover:bg-purple-50 hover:text-purple-600' },
      orange: { active: 'bg-orange-100 text-orange-700 border-orange-500', inactive: 'text-gray-600 hover:bg-orange-50 hover:text-orange-600' },
      pink: { active: 'bg-pink-100 text-pink-700 border-pink-500', inactive: 'text-gray-600 hover:bg-pink-50 hover:text-pink-600' },
      cyan: { active: 'bg-cyan-100 text-cyan-700 border-cyan-500', inactive: 'text-gray-600 hover:bg-cyan-50 hover:text-cyan-600' },
      amber: { active: 'bg-amber-100 text-amber-700 border-amber-500', inactive: 'text-gray-600 hover:bg-amber-50 hover:text-amber-600' },
      red: { active: 'bg-red-100 text-red-700 border-red-500', inactive: 'text-gray-600 hover:bg-red-50 hover:text-red-600' },
      slate: { active: 'bg-slate-100 text-slate-700 border-slate-500', inactive: 'text-gray-600 hover:bg-slate-50 hover:text-slate-600' }
    };
    return isActive ? colors[color]?.active : colors[color]?.inactive;
  };

  return (
    <PermissionContext.Provider value={{ permissions, isAdmin, hasPermission, loading, token }}>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-4">
                <Link 
                  href="/seller" 
                  className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
                >
                  <ChevronLeft className="h-5 w-5" />
                  <span className="hidden sm:inline">Back to Dashboard</span>
                </Link>
                <div className="h-6 w-px bg-gray-300 hidden sm:block" />
                <h1 className="text-lg font-semibold text-gray-900">Business Tools</h1>
              </div>
              
              {/* Mobile menu button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden p-2 text-gray-600 hover:text-gray-900"
              >
                {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex gap-6">
            {/* Sidebar Navigation - Desktop */}
            <aside className="hidden lg:block w-64 flex-shrink-0">
              <nav className="bg-white rounded-xl shadow-sm border p-4 sticky top-24">
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
                  Modules
                </h2>
                <div className="space-y-1">
                  {visibleNavItems.map((item) => {
                    const isActive = pathname.startsWith(item.href);
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                          getColorClasses(item.color, isActive)
                        } ${isActive ? 'border-l-4' : ''}`}
                      >
                        <Icon className="h-5 w-5" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              </nav>
            </aside>

            {/* Mobile Navigation */}
            {mobileMenuOpen && (
              <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={() => setMobileMenuOpen(false)}>
                <div className="absolute left-0 top-0 bottom-0 w-72 bg-white shadow-xl" onClick={e => e.stopPropagation()}>
                  <div className="p-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900">Business Tools</h2>
                  </div>
                  <nav className="p-4 space-y-1">
                    {visibleNavItems.map((item) => {
                      const isActive = pathname.startsWith(item.href);
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                            getColorClasses(item.color, isActive)
                          } ${isActive ? 'border-l-4' : ''}`}
                        >
                          <Icon className="h-5 w-5" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </nav>
                </div>
              </div>
            )}

            {/* Main Content */}
            <main className="flex-1 min-w-0">
              {children}
            </main>
          </div>
        </div>
      </div>
    </PermissionContext.Provider>
  );
}
