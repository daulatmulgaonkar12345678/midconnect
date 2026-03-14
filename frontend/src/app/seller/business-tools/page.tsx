'use client';

import { usePermissions } from './layout';
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
  ArrowRight,
  Loader2
} from 'lucide-react';

const modules = [
  { 
    href: '/seller/business-tools/inventory', 
    label: 'Inventory', 
    description: 'Track stock levels, set alerts, manage SKUs',
    icon: Package2,
    permission: 'manage_inventory',
    gradient: 'from-blue-500 to-blue-600'
  },
  { 
    href: '/seller/business-tools/buyers', 
    label: 'Buyers', 
    description: 'Manage customer records and history',
    icon: Users,
    permission: 'manage_buyers',
    gradient: 'from-green-500 to-green-600'
  },
  { 
    href: '/seller/business-tools/suppliers', 
    label: 'Suppliers', 
    description: 'Track supplier information and contacts',
    icon: Truck,
    permission: 'manage_suppliers',
    gradient: 'from-purple-500 to-purple-600'
  },
  { 
    href: '/seller/business-tools/invoices', 
    label: 'Invoices', 
    description: 'Create invoices and track payments',
    icon: FileText,
    permission: 'create_invoice',
    gradient: 'from-orange-500 to-orange-600'
  },
  { 
    href: '/seller/business-tools/composite-products', 
    label: 'Composite Products', 
    description: 'Bundle products into kits',
    icon: Layers,
    permission: 'manage_listings',
    gradient: 'from-pink-500 to-pink-600'
  },
  { 
    href: '/seller/business-tools/reports', 
    label: 'Reports', 
    description: 'Sales analytics and insights',
    icon: BarChart3,
    permission: 'view_reports',
    gradient: 'from-cyan-500 to-cyan-600'
  },
  { 
    href: '/seller/business-tools/employees', 
    label: 'Employees', 
    description: 'Manage team members and access',
    icon: UserCog,
    permission: 'manage_employees',
    gradient: 'from-amber-500 to-amber-600'
  },
  { 
    href: '/seller/business-tools/roles', 
    label: 'Roles & Permissions', 
    description: 'Configure access control',
    icon: Shield,
    permission: 'manage_roles',
    gradient: 'from-red-500 to-red-600'
  }
];

export default function BusinessToolsPage() {
  const { hasPermission, loading, isAdmin } = usePermissions();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const visibleModules = modules.filter(m => hasPermission(m.permission));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900">Business Tools</h1>
        <p className="text-gray-600 mt-1">
          Manage your inventory, customers, suppliers, and more.
        </p>
        {isAdmin && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mt-3">
            Admin Access - All Modules Available
          </span>
        )}
      </div>

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {visibleModules.map((module) => {
          const Icon = module.icon;
          return (
            <Link
              key={module.href}
              href={module.href}
              className="group bg-white rounded-xl shadow-sm border hover:shadow-md transition-all p-6"
              data-testid={`module-${module.label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl bg-gradient-to-br ${module.gradient} shadow-lg`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                    {module.label}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {module.description}
                  </p>
                </div>
                <ArrowRight className="h-5 w-5 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
              </div>
            </Link>
          );
        })}
      </div>

      {visibleModules.length === 0 && (
        <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
          <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No Access</h3>
          <p className="text-gray-500 mt-1">
            You don&apos;t have permission to access any business tools modules.
            Contact your administrator for access.
          </p>
        </div>
      )}
    </div>
  );
}
