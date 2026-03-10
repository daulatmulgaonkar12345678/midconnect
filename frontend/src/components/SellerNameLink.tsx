'use client';

import Link from 'next/link';

interface SellerNameLinkProps {
  sellerSlug: string;
  sellerName: string;
  className?: string;
  showPrefix?: boolean;
}

/**
 * Clickable seller name with hover animation.
 * Used across the platform for consistent seller linking:
 * - Product cards
 * - Product pages
 * - Search results
 * - Category pages
 */
export default function SellerNameLink({ 
  sellerSlug, 
  sellerName, 
  className = '',
  showPrefix = true 
}: SellerNameLinkProps) {
  if (!sellerSlug || !sellerName) return null;

  return (
    <Link 
      href={`/seller-catalog/${sellerSlug}`}
      className={`
        relative inline-flex items-center gap-1
        text-gray-600 hover:text-blue-600 
        transition-colors duration-200
        group
        ${className}
      `}
      data-testid={`seller-link-${sellerSlug}`}
    >
      {showPrefix && <span className="text-gray-400">By</span>}
      <span className="relative">
        {sellerName}
        {/* Animated underline */}
        <span 
          className="
            absolute bottom-0 left-0 
            w-0 h-0.5 
            bg-blue-600 
            group-hover:w-full 
            transition-all duration-300 ease-out
          " 
        />
      </span>
    </Link>
  );
}
