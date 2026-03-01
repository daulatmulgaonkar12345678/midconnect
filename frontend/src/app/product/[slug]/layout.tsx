import { Metadata } from 'next';

const API_URL = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || '';

// Generate dynamic metadata for SEO
export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const { slug } = params;
  
  try {
    const response = await fetch(`${API_URL}/api/products/${slug}/seo`, {
      next: { revalidate: 3600 }, // Cache for 1 hour
    });
    
    if (!response.ok) {
      return getDefaultMetadata();
    }
    
    const seoData = await response.json();
    
    return {
      title: seoData.seoTitle,
      description: seoData.seoDescription,
      keywords: `${seoData.productName}, buy ${seoData.productName}, ${seoData.categoryName || 'industrial products'}, suppliers, manufacturers, India, UdyogConnect`,
      openGraph: {
        title: seoData.seoTitle,
        description: seoData.seoDescription,
        url: seoData.canonicalUrl,
        siteName: 'UdyogConnect',
        type: 'website',
        locale: 'en_IN',
      },
      twitter: {
        card: 'summary_large_image',
        title: seoData.seoTitle,
        description: seoData.seoDescription,
      },
      alternates: {
        canonical: seoData.canonicalUrl,
      },
      robots: {
        index: true,
        follow: true,
        googleBot: {
          index: true,
          follow: true,
          'max-snippet': -1,
          'max-image-preview': 'large',
          'max-video-preview': -1,
        },
      },
    };
  } catch (error) {
    console.error('Error fetching SEO data:', error);
    return getDefaultMetadata();
  }
}

function getDefaultMetadata(): Metadata {
  return {
    title: 'Product | UdyogConnect - India\'s Industrial Marketplace',
    description: 'Find verified suppliers of industrial products. Compare prices, MOQ and contact manufacturers directly on UdyogConnect.',
    robots: {
      index: true,
      follow: true,
    },
  };
}

export default function ProductLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
