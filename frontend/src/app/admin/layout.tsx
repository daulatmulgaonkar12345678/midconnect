'use client';

import { ReactNode, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  LayoutDashboard, 
  Users, 
  Package, 
  FileText, 
  ShieldCheck,
  Settings,
  LogOut,
  FolderTree,
  ClipboardList,
  Loader2,
  AlertTriangle,
  ListChecks,
  Store,
  Calculator,
  Ruler,
  Beaker,
  Wallet,
  CreditCard,
  UserCheck
} from 'lucide-react';

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, profile, loading, isAdmin, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Auth gate - redirect if not admin
  useEffect(() => {
    if (!loading && !user) {
      router.push('/login?redirect=/admin');
    }
  }, [loading, user, router]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading admin panel...</p>
        </div>
      </div>
    );
  }

  // Not logged in
  if (!user) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // Not admin
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
          <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">
            You don't have admin privileges to access this area.
          </p>
          <div className="space-y-3">
            <Link 
              href="/"
              className="block w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Go to Homepage
            </Link>
            <button 
              onClick={() => signOut()}
              className="block w-full py-3 px-4 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    );
  }

  const navItems = [
    { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
    // B2B Foundation (Phase 1)
    { href: '/admin/dropdowns', label: 'Global Dropdowns', icon: ListChecks },
    { href: '/admin/categories', label: 'Categories', icon: FolderTree },
    { href: '/admin/spec-templates', label: 'Spec Templates', icon: ClipboardList },
    // Calculator System
    { href: '/admin/calculators', label: 'Calculators', icon: Calculator },
    { href: '/admin/unit-groups', label: 'Unit Groups', icon: Ruler },
    { href: '/admin/materials', label: 'Materials', icon: Beaker },
    // Product Management
    { href: '/admin/products', label: 'Products', icon: Package },
    // Commercial SSOT - Seller Listings
    { href: '/admin/listings', label: 'Seller Listings', icon: Store },
    // User Management
    { href: '/admin/users', label: 'Users', icon: Users },
    { href: '/admin/gst-verification', label: 'GST Verification', icon: FileText },
    { href: '/admin/product-requests', label: 'Product Requests', icon: FileText },
    { href: '/admin/payouts', label: 'Payouts', icon: Wallet },
    { href: '/admin/subscriptions', label: 'Subscriptions', icon: CreditCard },
    { href: '/admin/employees', label: 'Employees', icon: UserCheck },
    { href: '/admin/settings', label: 'Settings', icon: Settings },
  ];

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin';
    return pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Admin Header */}
      <header className="bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <ShieldCheck className="h-8 w-8 text-blue-400" />
              <span className="text-xl font-bold">Admin Panel</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-400">
                {profile?.email}
              </span>
              <Link href="/" className="text-gray-300 hover:text-white flex items-center gap-2">
                <LogOut className="h-4 w-4" /> Exit Admin
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white shadow-sm min-h-[calc(100vh-64px)] hidden md:block">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                  isActive(item.href)
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <item.icon className="h-5 w-5" /> {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
