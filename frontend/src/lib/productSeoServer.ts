// Batch 3 (2026-11-19): server-only fetch of the public product SEO payload.
//
// Shared by (main)/layout.tsx (metadata + JSON-LD) and the (main)/page.tsx
// server shell (SEO hero). Same URL and fetch cache policy
// (`next: { revalidate: 3600 }`) as the original layout-local `fetchSeo`.
// Next.js request memoization dedupes the two callers into a single upstream
// call per render.
//
// Batch 5 (2026-11-19): the result now distinguishes a definitive backend
// 404 (unknown/invalid slug — the backend resolves slugs deterministically
// and 404s anything that is not a product address) from transient
// unavailability (backend outage, 5xx, network error). Only the definitive
// 404 lets the page render the HTTP 404 boundary; transient failures keep
// the previous fallback behavior (payload null → hero hidden, page renders
// the client island with HTTP 200) so an outage can never 404 live pages.
//
// The payload is the same public, DB-backed payload the browser already
// requests (GET /api/products/{slug}/seo). Nothing here fabricates content:
// consumers render payload fields verbatim and only when present.

export type ProductSeoPayload = {
  productName?: string;
  seoTitle?: string;
  seoDescription?: string;
  canonicalUrl?: string;
  categoryName?: string;
  sellerCount?: number;
  listingCount?: number;
  verifiedSellerCount?: number;
  minPrice?: number | null;
  maxPrice?: number | null;
  minMoq?: number | null;
  sellersByCity?: Record<
    string,
    Array<{ companyName: string; state: string; lowestPrice: number | null; badgeType: string }>
  >;
  jsonLd?: Record<string, unknown>;
  breadcrumbJsonLd?: Record<string, unknown>;
  faqJsonLd?: Record<string, unknown>;
};

export type ProductSeoResult = {
  payload: ProductSeoPayload | null;
  /** True only when the backend definitively answered 404 for this slug. */
  notFound: boolean;
};

function isObjectId(str: string): boolean {
  return /^[a-f0-9]{24}$/i.test(str);
}

export async function fetchProductSeoPayload(
  slug: string,
): Promise<ProductSeoResult> {
  // Legacy ObjectId addresses are resolved client-side by the redirect
  // check and have no SEO payload (same as the previous layout behavior).
  // They are NOT a definitive 404: the page must stay 200 so the client
  // island can perform its legacy redirect.
  if (isObjectId(slug)) return { payload: null, notFound: false };

  const API_URL =
    process.env.REACT_APP_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    '';

  try {
    const response = await fetch(`${API_URL}/api/products/${slug}/seo`, {
      cache: 'no-store',
    });
    // Definitive backend answer: this slug resolves to no product.
    if (response.status === 404) return { payload: null, notFound: true };
    // Transient backend problem: keep the 200 shell fallback.
    if (!response.ok) return { payload: null, notFound: false };
    return { payload: (await response.json()) as ProductSeoPayload, notFound: false };
  } catch {
    return { payload: null, notFound: false };
  }
}
