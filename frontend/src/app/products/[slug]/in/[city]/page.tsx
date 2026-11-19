import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { fetchCityData, renderCityPage } from '@/lib/cityPageRenderer';

interface CityPageProps {
  params: Promise<{ slug: string; city: string }>;
}

export async function generateMetadata({ params }: CityPageProps): Promise<Metadata> {
  const { slug, city } = await params;
  const data = await fetchCityData(slug, city);
  if (!data) return { title: 'Product Not Found | UdyogConnect', robots: { index: false, follow: false } };

  const pageUrl = data.seo?.pageUrl || data.seo?.cityPageUrl;
  return {
    title: data.seo?.title || `${data.product?.name} in ${city} | UdyogConnect`,
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

export default async function CityProductPage({ params }: CityPageProps) {
  const { slug, city } = await params;
  const data = await fetchCityData(slug, city);
  // B4: a product-city pair without eligible supply is a real 404, not a
  // soft-404 rendered with HTTP 200.
  if (!data) notFound();
  return renderCityPage(data, slug, city, undefined);
}
