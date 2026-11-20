// Batch 3 (2026-11-19): server shell for the base product page
// /products/{slug}.
//
// Fetches the public /seo payload once server-side (request-memoized with the
// identical fetch in (main)/layout.tsx, so one upstream call per render) and
// renders the SEO hero — real product name, SEO description, price/seller
// chips — in the initial HTML. The unchanged interactive client island mounts
// below it.
//
// Batch 5 (2026-11-19): when the backend definitively answers 404 for the
// slug (deterministic resolver: the URL is not a product address), the page
// renders the HTTP 404 boundary instead of an empty 200 shell — invalid
// product URLs must not return 200. Legacy ObjectId URLs and transient
// backend failures keep the previous 200 fallback (client island handles
// the legacy redirect; outages must not 404 live pages).

import { notFound } from 'next/navigation';

import ProductSeoHero from '@/components/product/ProductSeoHero';
import { fetchProductSeoPayload } from '@/lib/productSeoServer';
import ProductPageClient from './ProductPageClient';

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const { payload, notFound: slugNotResolved } = await fetchProductSeoPayload(slug);

  // Definitive backend 404: this URL is not a product address.
  if (slugNotResolved) notFound();

  return (
    <>
      {payload && <ProductSeoHero payload={payload} />}
      <ProductPageClient />
    </>
  );
}
