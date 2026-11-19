// Batch 3 (2026-11-19): server-only fetch of the public product SEO payload.
//
// Shared by (main)/layout.tsx (metadata + JSON-LD) and the (main)/page.tsx
// server shell (SEO hero). Semantics are identical to the previous
// layout-local `fetchSeo`: same URL, same fetch cache policy
// (`next: { revalidate: 3600 }`), `null` on any failure so every caller keeps
// its existing fallback behavior. Next.js request memoization dedupes the two
// callers into a single upstream call per render.
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

function isObjectId(str: string): boolean {
  return /^[a-f0-9]{24}$/i.test(str);
}

export async function fetchProductSeoPayload(
  slug: string,
): Promise<ProductSeoPayload | null> {
  // Legacy ObjectId addresses are resolved client-side by the redirect
  // check and have no SEO payload (same as the previous layout behavior).
  if (isObjectId(slug)) return null;

  const API_URL =
    process.env.REACT_APP_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    '';

  try {
    const response = await fetch(`${API_URL}/api/products/${slug}/seo`, {
      next: { revalidate: 3600 },
    });
    if (!response.ok) return null;
    return (await response.json()) as ProductSeoPayload;
  } catch {
    return null;
  }
}
