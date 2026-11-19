// Batch 3 (2026-11-19): server shell for the base product page
// /products/{slug}.
//
// Fetches the public /seo payload once server-side (request-memoized with the
// identical fetch in (main)/layout.tsx, so one upstream call per render) and
// renders the SEO hero — real product name, SEO description, price/seller
// chips — in the initial HTML. The unchanged interactive client island mounts
// below it. When the payload is unavailable (backend error, unknown slug,
// legacy ObjectId URL) the hero renders nothing and the page falls back to
// the previous client-only behavior; nothing is fabricated. Metadata,
// canonical/og:url normalization (Batch 2) and JSON-LD remain owned by
// (main)/layout.tsx.

import ProductSeoHero from '@/components/product/ProductSeoHero';
import { fetchProductSeoPayload } from '@/lib/productSeoServer';
import ProductPageClient from './ProductPageClient';

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await fetchProductSeoPayload(slug);

  return (
    <>
      {payload && <ProductSeoHero payload={payload} />}
      <ProductPageClient />
    </>
  );
}
