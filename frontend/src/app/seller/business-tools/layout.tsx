'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { NetworkProvider, useNetworkContext } from '@/context/NetworkContext';
import NetworkStatusBanner from '@/components/NetworkStatusBanner';
import { Toaster } from 'sonner';
import ReferralModal from '@/components/ReferralModal';
import { EmployeeAccessProvider, useEmployeeAccess } from '@/context/EmployeeAccessContext';
import NoAccess from '@/components/NoAccess';
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
  X,
  Settings,
  Building2,
  Save,
  AlertTriangle,
  Home,
  LineChart,
  Bell,
  Clock,
  Wifi,
  WifiOff,
  Gift,
  LayoutGrid
} from 'lucide-react';

// ──────────────────────────────────────
// Permission Context (consumed by child pages)
// ──────────────────────────────────────
interface PermissionContextType {
  permissions: string[];
  isAdmin: boolean;
  hasPermission: (permission: string) => boolean;
  canAction: (module: string) => boolean;
  loading: boolean;
  token: string | null;
}

const PermissionContext = createContext<PermissionContextType>({
  permissions: [],
  isAdmin: false,
  hasPermission: () => false,
  canAction: () => false,
  loading: true,
  token: null
});

export const usePermissions = () => useContext(PermissionContext);

// ──────────────────────────────────────
// Route → Module mapping for route-level protection
// ──────────────────────────────────────
const ROUTE_MODULE_MAP: Record<string, string> = {
  '/seller/business-tools': 'dashboard',
  '/seller/business-tools/inventory': 'inventory',
  '/seller/business-tools/low-stock-alerts': 'inventory',
  '/seller/business-tools/composite-products': 'inventory',
  '/seller/business-tools/buyers': 'buyers',
  '/seller/business-tools/suppliers': 'suppliers',
  '/seller/business-tools/invoices': 'invoices',
  '/seller/business-tools/pending-orders': 'invoices',
  '/seller/business-tools/quotations': 'quotations',
  '/seller/business-tools/purchase-orders': 'purchase_orders',
  '/seller/business-tools/charts': 'reports',
  '/seller/business-tools/analytics': 'reports',
  '/seller/business-tools/reports': 'reports',
  '/seller/business-tools/employees': 'employees',
  '/seller/business-tools/roles': 'employees',
  '/seller/business-tools/activity-logs': 'settings',
  '/seller/business-tools/settings': 'settings',
  '/seller/business-tools/notifications': 'dashboard',
  '/seller/business-tools/panels': 'dashboard',
};

// ──────────────────────────────────────
// Navigation items
// ──────────────────────────────────────
const navItems = [
  {
    href: '/seller/business-tools',
    label: 'Home',
    icon: Home,
    permission: 'create_invoice',
    module: 'dashboard',
    color: 'indigo',
    exact: true
  },
  {
    href: '/seller/business-tools/notifications',
    label: 'Notifications',
    icon: Bell,
    permission: 'create_invoice',
    module: 'dashboard',
    color: 'red',
    showBadge: true
  },
  { 
    href: '/seller/business-tools/inventory', 
    label: 'Inventory', 
    icon: Package2,
    permission: 'manage_inventory',
    module: 'inventory',
    color: 'blue'
  },
  { 
    href: '/seller/business-tools/low-stock-alerts', 
    label: 'Low Stock Alerts', 
    icon: AlertTriangle,
    permission: 'manage_inventory',
    module: 'inventory',
    color: 'orange'
  },
  { 
    href: '/seller/business-tools/buyers', 
    label: 'Buyers', 
    icon: Users,
    permission: 'manage_buyers',
    module: 'buyers',
    color: 'green'
  },
  { 
    href: '/seller/business-tools/suppliers', 
    label: 'Suppliers', 
    icon: Truck,
    permission: 'manage_suppliers',
    module: 'suppliers',
    color: 'purple'
  },
  { 
    href: '/seller/business-tools/invoices', 
    label: 'Invoices', 
    icon: FileText,
    permission: 'create_invoice',
    module: 'invoices',
    color: 'orange'
  },
  {
    href: '/seller/business-tools/pending-orders',
    label: 'Pending Orders',
    icon: Clock,
    permission: 'create_invoice',
    module: 'invoices',
    color: 'amber'
  },
  {
    href: '/seller/business-tools/quotations',
    label: 'Quotations',
    icon: Layers,
    permission: 'create_invoice',
    module: 'quotations',
    color: 'violet'
  },
  {
    href: '/seller/business-tools/charts',
    label: 'Charts & Graphs',
    icon: LineChart,
    permission: 'manage_inventory',
    module: 'reports',
    color: 'cyan'
  },
  { 
    href: '/seller/business-tools/analytics', 
    label: 'Product Analytics', 
    icon: BarChart3,
    permission: 'manage_inventory',
    module: 'reports',
    color: 'blue'
  },
  { 
    href: '/seller/business-tools/composite-products', 
    label: 'Composite Products', 
    icon: Layers,
    permission: 'manage_inventory',
    module: 'inventory',
    color: 'pink'
  },
  { 
    href: '/seller/business-tools/reports', 
    label: 'Reports', 
    icon: BarChart3,
    permission: 'view_reports',
    module: 'reports',
    color: 'cyan'
  },
  { 
    href: '/seller/business-tools/employees', 
    label: 'Employees', 
    icon: UserCog,
    permission: 'manage_employees',
    module: 'employees',
    color: 'amber'
  },
  { 
    href: '/seller/business-tools/roles', 
    label: 'Roles & Permissions', 
    icon: Shield,
    permission: 'manage_roles',
    module: 'employees',
    color: 'red'
  },
  { 
    href: '/seller/business-tools/activity-logs', 
    label: 'Activity Logs', 
    icon: Activity,
    permission: 'manage_roles',
    module: 'settings',
    color: 'slate'
  },
  { 
    href: '/seller/business-tools/settings', 
    label: 'Business Settings', 
    icon: Settings,
    permission: 'create_invoice',
    module: 'settings',
    color: 'indigo'
  }
];

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
    slate: { active: 'bg-slate-100 text-slate-700 border-slate-500', inactive: 'text-gray-600 hover:bg-slate-50 hover:text-slate-600' },
    indigo: { active: 'bg-indigo-100 text-indigo-700 border-indigo-500', inactive: 'text-gray-600 hover:bg-indigo-50 hover:text-indigo-600' },
    violet: { active: 'bg-violet-100 text-violet-700 border-violet-500', inactive: 'text-gray-600 hover:bg-violet-50 hover:text-violet-600' },
  };
  return isActive ? colors[color]?.active || '' : colors[color]?.inactive || '';
};

// ──────────────────────────────────────
// Small helper components
// ──────────────────────────────────────
function NetworkIndicator() {
  const { isOnline, syncState } = useNetworkContext();
  return (
    <div
      data-testid="network-indicator"
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
        isOnline
          ? 'bg-emerald-50 text-emerald-700'
          : 'bg-red-50 text-red-700'
      }`}
    >
      {isOnline ? (
        <>
          <Wifi className="h-3 w-3" />
          <span className="hidden sm:inline">Online</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3 w-3" />
          <span className="hidden sm:inline">Offline</span>
        </>
      )}
      {syncState.pendingCount > 0 && (
        <span className="bg-amber-500 text-white rounded-full min-w-[16px] h-4 flex items-center justify-center text-[10px] ml-0.5">
          {syncState.pendingCount}
        </span>
      )}
    </div>
  );
}

function CompanyBanner() {
  const { access, loading } = useEmployeeAccess();
  if (loading || !access) return null;

  const name = access.companyName || 'No Company Linked';
  const logo = access.companyLogoUrl;
  const role = access.isAdmin ? 'Admin' : (access.role && access.role !== 'unassigned' ? access.role : '');

  return (
    <div data-testid="company-banner" className="flex items-center gap-3 px-3 py-3 mb-3 rounded-lg bg-gradient-to-r from-slate-50 to-blue-50 border border-slate-200/80">
      {logo ? (
        <img
          src={logo}
          alt={name}
          className="w-10 h-10 rounded-lg object-cover border border-slate-200 flex-shrink-0"
          data-testid="company-banner-logo"
        />
      ) : (
        <div className="w-10 h-10 rounded-lg bg-blue-100 border border-blue-200 flex items-center justify-center flex-shrink-0" data-testid="company-banner-logo-placeholder">
          <Building2 className="h-5 w-5 text-blue-600" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate" data-testid="company-banner-name">
          {name}
        </p>
        {role && (
          <p className="text-xs text-gray-500 truncate" data-testid="company-banner-role">
            {role}
          </p>
        )}
      </div>
    </div>
  );
}

// ──────────────────────────────────────
// Inner component – rendered INSIDE providers
// Hooks (useEmployeeAccess) work correctly here
// ──────────────────────────────────────
interface BusinessToolsInnerProps {
  children: React.ReactNode;
  permissions: string[];
  isAdmin: boolean;
  hasPermission: (permission: string) => boolean;
  loading: boolean;
  token: string | null;
  businessToolAccess: string;
}

function BusinessToolsInner({
  children,
  permissions,
  isAdmin,
  hasPermission,
  loading,
  token,
  businessToolAccess: btAccess,
}: BusinessToolsInnerProps) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingForm, setOnboardingForm] = useState({
    businessName: '', phone: '', address: '', city: '', state: '', gstNumber: '',
  });
  const [onboardingSaving, setOnboardingSaving] = useState(false);
  const [showReferral, setShowReferral] = useState(false);
  const [customPanels, setCustomPanels] = useState<{id: string; name: string; slug: string; color: string}[]>([]);
  const accessLevel = btAccess;

  // CORRECTLY inside EmployeeAccessProvider
  const { canView, canAction: empCanAction, loading: empLoading, access: empAccess } = useEmployeeAccess();

  // Determine sidebar panels: admin sees all fetched panels, employees see permitted panels
  const sidebarPanels = isAdmin ? customPanels : (empAccess?.permittedPanels || []);
  const showPanelsSection = isAdmin ? accessLevel === 'advanced' : sidebarPanels.length > 0;

  // Combined: admin always has full access; employees checked via RBAC
  const effectiveCanView = useCallback(
    (module: string) => isAdmin || canView(module),
    [isAdmin, canView]
  );
  const effectiveCanAction = useCallback(
    (module: string) => isAdmin || empCanAction(module),
    [isAdmin, empCanAction]
  );

  // Check if seller needs onboarding
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/seller-profile`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (res.ok) {
          const data = await res.json();
          if (!data.profileComplete) setShowOnboarding(true);
        }
      } catch { /* empty */ }
    })();
  }, [token]);

  // Fetch unread notification count for sidebar badge
  useEffect(() => {
    if (!token) return;
    const fetchUnread = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/notifications/unread-count`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (res.ok) {
          const data = await res.json();
          setUnreadCount(data.unread || 0);
        }
      } catch { /* empty */ }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, [token]);

  // Fetch custom panels for sidebar (only if advanced access)
  useEffect(() => {
    if (!token || accessLevel !== 'advanced') return;
    (async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/panels`, { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setCustomPanels(data.panels || []);
        }
      } catch { /* empty */ }
    })();
  }, [token, accessLevel]);

  const submitOnboarding = async () => {
    if (!onboardingForm.businessName.trim()) { alert('Business name is required'); return; }
    setOnboardingSaving(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/business-tools/seller-profile`,
        {
          method: 'PUT',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(onboardingForm),
        }
      );
      if (res.ok) {
        setShowOnboarding(false);
      } else {
        const data = await res.json();
        alert(data.detail || 'Failed to save');
      }
    } catch { alert('Error saving profile'); }
    setOnboardingSaving(false);
  };

  // Loading state: for non-admin users, wait for employee access to resolve
  if (!isAdmin && empLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center" data-testid="employee-access-loading">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm text-gray-500">Loading your permissions...</p>
        </div>
      </div>
    );
  }

  // Global access gate: if businessToolAccess is "none", block everything
  if (accessLevel === 'none') {
    return (
      <PermissionContext.Provider value={{ permissions, isAdmin, hasPermission, canAction: effectiveCanAction, loading, token }}>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center" data-testid="no-business-tools-access">
          <div className="text-center max-w-md px-6">
            <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
              <LayoutGrid className="h-8 w-8 text-gray-400" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">Business Tools Not Enabled</h2>
            <p className="text-gray-500 mt-2 text-sm">
              Business tools access is not enabled for your account. Contact your platform admin to enable access.
            </p>
            <Link href="/seller" className="inline-flex items-center gap-2 mt-6 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
              <ChevronLeft className="h-4 w-4" /> Back to Dashboard
            </Link>
          </div>
        </div>
      </PermissionContext.Provider>
    );
  }

  // Filter nav items and check route access
  const visibleNavItems = navItems.filter(item => effectiveCanView(item.module));
  const requiredModule = ROUTE_MODULE_MAP[pathname] || null;
  const routeBlocked = requiredModule ? !effectiveCanView(requiredModule) : false;

  return (
    <PermissionContext.Provider value={{ permissions, isAdmin, hasPermission, canAction: effectiveCanAction, loading, token }}>
      <Toaster position="top-right" richColors closeButton />
      <div className="min-h-screen bg-gray-50">
        {/* Network Status Banner */}
        <NetworkStatusBanner />
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
              
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowReferral(true)}
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium hover:bg-indigo-100 transition-colors"
                  data-testid="refer-earn-header-btn"
                >
                  <Gift className="h-3.5 w-3.5" />
                  Refer & Earn
                </button>
                <NetworkIndicator />
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="lg:hidden p-2 text-gray-600 hover:text-gray-900"
                  data-testid="mobile-menu-toggle"
                >
                  {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                </button>
              </div>
            </div>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex gap-6">
            {/* Sidebar Navigation - Desktop */}
            <aside className="hidden lg:block w-64 flex-shrink-0">
              <nav className="bg-white rounded-xl shadow-sm border p-4 sticky top-24" data-testid="desktop-sidebar">
                <CompanyBanner />
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
                  Modules
                </h2>
                <div className="space-y-1">
                  {visibleNavItems.map((item) => {
                    const isActive = item.exact
                      ? pathname === item.href
                      : pathname.startsWith(item.href);
                    const Icon = item.icon;
                    const hasBadge = item.showBadge && unreadCount > 0;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        data-testid={`nav-${item.module}-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                          getColorClasses(item.color, isActive)
                        } ${isActive ? 'border-l-4' : ''}`}
                      >
                        <Icon className="h-5 w-5" />
                        <span className="flex-1">{item.label}</span>
                        {hasBadge && (
                          <span className="ml-auto bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1" data-testid="notification-badge">
                            {unreadCount > 99 ? '99+' : unreadCount}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
                {/* Custom Panels Section */}
                {showPanelsSection && (
                  <>
                    <div className="mt-5 pt-4 border-t border-gray-100">
                      <div className="flex items-center justify-between mb-3">
                        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Custom Panels</h2>
                      </div>
                      <div className="space-y-1">
                        {isAdmin && (
                          <Link
                            href="/seller/business-tools/panels"
                            data-testid="nav-panels-manage"
                            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                              getColorClasses('indigo', pathname === '/seller/business-tools/panels')
                            } ${pathname === '/seller/business-tools/panels' ? 'border-l-4' : ''}`}
                          >
                            <LayoutGrid className="h-5 w-5" />
                            <span className="flex-1">Manage Panels</span>
                          </Link>
                        )}
                        {sidebarPanels.map(p => {
                          const panelPath = `/seller/business-tools/panels/${p.id}`;
                          const active = pathname === panelPath;
                          return (
                            <Link key={p.id} href={panelPath}
                              data-testid={`nav-panel-${p.id}`}
                              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                                getColorClasses(p.color || 'blue', active)
                              } ${active ? 'border-l-4' : ''}`}
                            >
                              <LayoutGrid className="h-4 w-4" />
                              <span className="flex-1 truncate">{p.name}</span>
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
              </nav>
            </aside>

            {/* Mobile Navigation */}
            {mobileMenuOpen && (
              <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={() => setMobileMenuOpen(false)}>
                <div className="absolute left-0 top-0 bottom-0 w-72 bg-white shadow-xl" onClick={e => e.stopPropagation()}>
                  <div className="p-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900 mb-3">Business Tools</h2>
                    <CompanyBanner />
                  </div>
                  <nav className="p-4 space-y-1" data-testid="mobile-sidebar">
                    {visibleNavItems.map((item) => {
                      const isActive = item.exact
                        ? pathname === item.href
                        : pathname.startsWith(item.href);
                      const Icon = item.icon;
                      const hasBadge = item.showBadge && unreadCount > 0;
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
                          <span className="flex-1">{item.label}</span>
                          {hasBadge && (
                            <span className="ml-auto bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                              {unreadCount > 99 ? '99+' : unreadCount}
                            </span>
                          )}
                        </Link>
                      );
                    })}
                    {/* Custom Panels - Mobile */}
                    {showPanelsSection && (
                      <>
                        <div className="mt-4 pt-3 border-t border-gray-100">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 px-3">Custom Panels</p>
                          {isAdmin && (
                            <Link
                              href="/seller/business-tools/panels"
                              onClick={() => setMobileMenuOpen(false)}
                              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                                getColorClasses('indigo', pathname === '/seller/business-tools/panels')
                              }`}
                            >
                              <LayoutGrid className="h-5 w-5" />
                              <span>Manage Panels</span>
                            </Link>
                          )}
                          {sidebarPanels.map(p => (
                            <Link key={p.id} href={`/seller/business-tools/panels/${p.id}`}
                              onClick={() => setMobileMenuOpen(false)}
                              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                                getColorClasses(p.color || 'blue', pathname === `/seller/business-tools/panels/${p.id}`)
                              }`}
                            >
                              <LayoutGrid className="h-4 w-4" />
                              <span className="truncate">{p.name}</span>
                            </Link>
                          ))}
                        </div>
                      </>
                    )}
                  </nav>
                </div>
              </div>
            )}

            {/* Main Content */}
            <main className="flex-1 min-w-0" data-testid="main-content-area">
              {routeBlocked ? (
                <NoAccess message="You don't have permission to view this module. Ask your admin to enable access." />
              ) : (
                children
              )}
            </main>
          </div>
        </div>

        {/* Onboarding Modal */}
        {showOnboarding && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[80] p-4" data-testid="onboarding-modal">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
              <div className="text-center mb-6">
                <Building2 className="w-10 h-10 text-indigo-600 mx-auto mb-2" />
                <h2 className="text-xl font-bold text-gray-900">Set Up Your Business Profile</h2>
                <p className="text-sm text-gray-500 mt-1">Complete your profile to generate professional invoices</p>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name *</label>
                  <input type="text" value={onboardingForm.businessName}
                    onChange={e => setOnboardingForm(p => ({ ...p, businessName: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Akash Enterprises"
                    data-testid="onboard-business-name" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                    <input type="text" value={onboardingForm.phone}
                      onChange={e => setOnboardingForm(p => ({ ...p, phone: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="9876543210"
                      data-testid="onboard-phone" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">GST <span className="text-gray-400">(optional)</span></label>
                    <input type="text" value={onboardingForm.gstNumber}
                      onChange={e => setOnboardingForm(p => ({ ...p, gstNumber: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="22AAAAA0000A1Z5"
                      data-testid="onboard-gst" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                  <input type="text" value={onboardingForm.address}
                    onChange={e => setOnboardingForm(p => ({ ...p, address: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="Street address"
                    data-testid="onboard-address" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                    <input type="text" value={onboardingForm.city}
                      onChange={e => setOnboardingForm(p => ({ ...p, city: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      data-testid="onboard-city" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                    <input type="text" value={onboardingForm.state}
                      onChange={e => setOnboardingForm(p => ({ ...p, state: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      data-testid="onboard-state" />
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6 justify-end">
                <button onClick={() => setShowOnboarding(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="onboard-skip-btn">Skip for now</button>
                <button onClick={submitOnboarding} disabled={onboardingSaving}
                  className="flex items-center gap-2 px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50" data-testid="onboard-save-btn">
                  <Save className="w-4 h-4" /> {onboardingSaving ? 'Saving...' : 'Complete Setup'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Referral Modal */}
        <ReferralModal isOpen={showReferral} onClose={() => setShowReferral(false)} token={token} />
      </div>
    </PermissionContext.Provider>
  );
}

// ──────────────────────────────────────
// Outer Layout – providers only, no hooks that depend on providers
// ──────────────────────────────────────
export default function BusinessToolsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [businessToolAccess, setBusinessToolAccess] = useState<string>('standard');

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
      setBusinessToolAccess(data.businessToolAccess || 'standard');
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

  const hasPermission = useCallback(
    (permission: string) => isAdmin || permissions.includes(permission),
    [isAdmin, permissions]
  );

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center" data-testid="auth-loading">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <EmployeeAccessProvider>
      <NetworkProvider>
        <BusinessToolsInner
          permissions={permissions}
          isAdmin={isAdmin}
          hasPermission={hasPermission}
          loading={loading}
          token={token}
          businessToolAccess={businessToolAccess}
        >
          {children}
        </BusinessToolsInner>
      </NetworkProvider>
    </EmployeeAccessProvider>
  );
}
