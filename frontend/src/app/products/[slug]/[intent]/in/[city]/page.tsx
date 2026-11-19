import type { Metadata } from 'next';
import { fetchCityData, renderCityPage } from '@/lib/cityPageRenderer';
import { notFound } from 'next/navigation';
import { canonicalSelfUrl } from '@/lib/siteUrl';

const SUPPORTED_INTENTS = ['price', 'buy', 'suppliers', 'wholesale', 'cheap'] as const;
type Intent = (typeof SUPPORTED_INTENTS)[number];

interface IntentCityPageProps {
  params: Promise<{ slug: string; intent: string; city: string }>;
}

function isValidIntent(s: string): s is Intent {
  return (SUPPORTED_INTENTS as readonly string[]).includes(s);
}

export async function generateMetadata({ params }: IntentCityPageProps): Promise<Metadata> {
  const { slug, intent, city } = await params;
  if (!isValidIntent(intent)) return { title: 'Not Found | UdyogConnect', robots: { index: false, follow: false } };

  const data = await fetchCityData(slug, city, intent);
  if (!data) return { title: 'Product Not Found | UdyogConnect', robots: { index: false, follow: false } };

  // Self-canonical for intent+city pages — index ONLY if content is unique (handled via template variation on backend).
  // Fallback to main product page canonical if the backend indicates low uniqueness (future extension).
  // Batch 2: re-anchor on the approved apex origin — cached payloads fetched
  // before the backend apex switch can still carry the www host.
  const pageUrl = canonicalSelfUrl(
    data.seo?.pageUrl,
    `/products/${slug}/${intent}/in/${city}`,
  );

  return {
    title: data.seo?.title,
    description: data.seo?.description,
    alternates: { canonical: pageUrl },
    openGraph: {
      title: data.seo?.title,
      description: data.seo?.description,
      url: pageUrl,
      siteName: 'UdyogConnect',
      type: 'website',
      locale: 'en_IN',
    },
    robots: { index: true, follow: true },
  };
}

export default async function IntentCityProductPage({ params }: IntentCityPageProps) {
  const { slug, intent, city } = await params;
  if (!isValidIntent(intent)) notFound();

  const data = await fetchCityData(slug, city, intent);
  // B4: a product-city pair without eligible supply is a real 404, not a
  // soft-404 rendered with HTTP 200.
  if (!data) notFound();
  return renderCityPage(data, slug, city, intent);
}
