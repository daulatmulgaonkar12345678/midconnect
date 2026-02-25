'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Menu, X, User, LogOut, ShoppingBag, Settings, Package, ChevronDown, LayoutDashboard } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { APP_NAME } from '@/lib/config';
import EnterpriseSearchBar from './EnterpriseSearchBar';

export default function Header() {
  const { user, profile, signOut, loading, isAdmin, isSeller, role } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const router = useRouter();

  const handleSignOut = async () => {
    await signOut();
    setIsUserMenuOpen(false);
    router.push('/');
  };

  return (
    <header className="bg-white shadow-sm sticky top-0 z-50 overflow-visible">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 overflow-visible">
        <div className="flex items-center justify-between h-16 gap-4 overflow-visible">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <ShoppingBag className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900 hidden sm:inline">{APP_NAME}</span>
          </Link>

          {/* Enterprise Search Bar - Desktop */}
          <div className="hidden md:block flex-1 max-w-2xl overflow-visible">
            <EnterpriseSearchBar 
              variant="header" 
              showLocationFilter={true}
            />
          </div>

          {/* Navigation - Desktop */}
          <nav className="hidden md:flex items-center gap-4 flex-shrink-0">
            <Link href="/products" className="text-gray-600 hover:text-gray-900 text-sm">Products</Link>
            <Link href="/categories" className="text-gray-600 hover:text-gray-900 text-sm">Categories</Link>
            
            {!loading && (
              user ? (
                <div className="relative">
                  <button
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
                  >
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <User className="h-4 w-4 text-blue-600" />
                    </div>
                    <span className="text-sm max-w-[100px] truncate">
                      {profile?.businessName || user.email?.split('@')[0]}
                    </span>
                    <ChevronDown className="h-4 w-4" />
                  </button>

                  {/* User Dropdown */}
                  {isUserMenuOpen && (
                    <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-100 py-2 z-50">
                      <div className="px-4 py-2 border-b border-gray-100">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {profile?.businessName || 'User'}
                        </p>
                        <p className="text-xs text-gray-500 truncate">{user.email}</p>
                        <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${
                          isAdmin ? 'bg-purple-100 text-purple-700' :
                          isSeller ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {isAdmin ? 'Admin' : isSeller ? 'Seller' : 'Buyer'}
                        </span>
                      </div>

                      {/* Role-based menu items */}
                      {isAdmin && (
                        <Link
                          href="/admin"
                          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <Settings className="h-4 w-4" /> Admin Panel
                        </Link>
                      )}

                      {isSeller && (
                        <Link
                          href="/seller"
                          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <LayoutDashboard className="h-4 w-4" /> Seller Dashboard
                        </Link>
                      )}

                      {isSeller && (
                        <Link
                          href="/seller/listings"
                          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <Package className="h-4 w-4" /> My Listings
                        </Link>
                      )}

                      <Link
                        href="/seller/profile"
                        className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        onClick={() => setIsUserMenuOpen(false)}
                      >
                        <User className="h-4 w-4" /> Profile
                      </Link>

                      <button
                        onClick={handleSignOut}
                        className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                      >
                        <LogOut className="h-4 w-4" /> Sign Out
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <Link
                    href="/login"
                    className="text-gray-600 hover:text-gray-900"
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                  >
                    Sign Up
                  </Link>
                </div>
              )
            )}
          </nav>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t">
            {/* Mobile Search */}
            <div className="mb-4">
              <EnterpriseSearchBar 
                variant="header" 
                showLocationFilter={false}
              />
            </div>
            <nav className="flex flex-col gap-4">
              <Link href="/products" className="text-gray-600" onClick={() => setIsMenuOpen(false)}>Products</Link>
              <Link href="/categories" className="text-gray-600" onClick={() => setIsMenuOpen(false)}>Categories</Link>
              
              {!loading && (
                user ? (
                  <>
                    {isAdmin && (
                      <Link href="/admin" className="text-gray-600" onClick={() => setIsMenuOpen(false)}>
                        Admin Panel
                      </Link>
                    )}
                    {isSeller && (
                      <Link href="/seller" className="text-gray-600" onClick={() => setIsMenuOpen(false)}>
                        Seller Dashboard
                      </Link>
                    )}
                    {isSeller && (
                      <Link href="/seller/listings" className="text-gray-600" onClick={() => setIsMenuOpen(false)}>
                        My Listings
                      </Link>
                    )}
                    <Link href="/seller/profile" className="text-gray-600" onClick={() => setIsMenuOpen(false)}>
                      Profile
                    </Link>
                    <button onClick={handleSignOut} className="text-left text-red-600">
                      Sign Out
                    </button>
                  </>
                ) : (
                  <>
                    <Link href="/login" className="text-blue-600" onClick={() => setIsMenuOpen(false)}>Login</Link>
                    <Link href="/register" className="text-blue-600" onClick={() => setIsMenuOpen(false)}>Sign Up</Link>
                  </>
                )
              )}
            </nav>
          </div>
        )}
      </div>

      {/* Click outside handler for dropdown */}
      {isUserMenuOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsUserMenuOpen(false)}
        />
      )}
    </header>
  );
}
