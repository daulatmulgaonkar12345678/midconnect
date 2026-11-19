// Batch 3 (2026-11-19): server-rendered product hero (React Server Component).
//
// Renders the SEO-critical identity content of /products/{slug} in the
// INITIAL HTML — the part that was previously a client-side "Loading
// product…" shell: exactly one H1 with the real product name, the payload's
// own SEO description, breadcrumb, and price/seller chips only when the
// public /seo payload carries real values. Every string shown here comes
// verbatim from the payload — nothing is fabricated, defaulted, or
// synthesized. When the payload is missing or nameless, the hero renders
// nothing and the page falls back to the previous client-only behavior.
//
// Zero interactivity, zero client JavaScript: no 'use client', no hooks, no
// event handlers. The interactive page (client island) renders below this
// section unchanged. The island's own H1 / breadcrumb / seller-count chip /
// price chip are removed in the same change — the hero is their single
// source, so the page never shows duplicate or conflicting headings.
//
// Canonical/og:url metadata and JSON-LD remain owned by (main)/layout.tsx
// (Batch 2 behavior, untouched).

import Link from 'next/link';
import { ChevronRight, Users } from 'lucide-react';
import type { ProductSeoPayload } from '@/lib/productSeoServer';

const formatINR = (value: number): string => `₹${value.toLocaleString('en-IN')}`;

export default function ProductSeoHero({ payload }: { payload?: ProductSeoPayload | null }) {
  const name = payload?.productName?.trim();
  // Without a real product name there is nothing honest to render.
  if (!payload || !name) return null;

  const description = payload.seoDescription?.trim() || '';
  const sellerCount =
    typeof payload.sellerCount === 'number' && payload.sellerCount > 0
      ? payload.sellerCount
      : null;
  const minPrice =
    typeof payload.minPrice === 'number' && payload.minPrice > 0 ? payload.minPrice : null;
  const maxPrice =
    typeof payload.maxPrice === 'number' && payload.maxPrice > 0 ? payload.maxPrice : null;
  const hasChips = sellerCount !== null || minPrice !== null || maxPrice !== null;

  return (
    <section className="bg-white border-b border-slate-200" data-testid="seo-hero">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Breadcrumb — same markup/order the client identity block used */}
        <nav className="flex items-center gap-2 text-sm text-slate-500 mb-4" data-testid="seo-hero-breadcrumb">
          <Link href="/" className="hover:text-slate-700">Home</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/products" className="hover:text-slate-700">Products</Link>
          {payload.categoryName && (
            <>
              <ChevronRight className="h-4 w-4" />
              <span className="hover:text-slate-700">{payload.categoryName}</span>
            </>
          )}
          <ChevronRight className="h-4 w-4" />
          <span className="text-slate-900 font-medium">{name}</span>
        </nav>

        <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 mb-2" data-testid="seo-hero-name">
          {name}
        </h1>

        {description && (
          <p className="text-slate-600 mb-4" data-testid="seo-hero-description">
            {description}
          </p>
        )}

        {hasChips && (
          <div className="flex flex-wrap gap-3" data-testid="seo-hero-chips">
            {sellerCount !== null && (
              <div
                className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg"
                data-testid="seo-hero-seller-count"
              >
                <Users className="h-4 w-4" />
                <span className="font-medium">
                  {sellerCount} {sellerCount === 1 ? 'Seller' : 'Sellers'}
                </span>
              </div>
            )}
            {minPrice !== null && (
              <div
                className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg"
                data-testid="seo-hero-price"
              >
                <span className="font-bold">₹</span>
                <span className="font-medium">From {formatINR(minPrice)}</span>
              </div>
            )}
            {minPrice === null && maxPrice !== null && (
              <div
                className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg"
                data-testid="seo-hero-price"
              >
                <span className="font-bold">₹</span>
                <span className="font-medium">Up to {formatINR(maxPrice)}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
