import { Metadata } from 'next';
import SellerCatalogPage from './SellerCatalogPage';

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata(
  { params }: Props
): Promise<Metadata> {
  const { slug } = await params;
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';
  
  try {
    const response = await fetch(`${API_URL}/api/seller-catalog/${slug}`, {
      next: { revalidate: 3600 } // Revalidate every hour
    });
    
    if (!response.ok) {
      return {
        title: 'Seller Not Found | Udyog Connect',
        description: 'The seller you are looking for could not be found.'
      };
    }
    
    const data = await response.json();
    const seller = data.seller;
    
    const title = `${seller.companyName} | Industrial Supplier in ${seller.location?.city || 'India'} | Udyog Connect`;
    const description = `${seller.companyName} - Industrial supplier${seller.location?.city ? ` in ${seller.location.city}` : ''}. Browse ${data.totalProducts} products across ${data.totalCategories} categories. ${seller.rating?.avgRating > 0 ? `Rated ${seller.rating.avgRating}/5 with ${seller.rating.totalReviews} reviews.` : ''} Send inquiry and connect directly.`;
    
    return {
      title,
      description,
      keywords: [
        seller.companyName,
        'industrial supplier',
        seller.location?.city,
        seller.location?.state,
        'B2B marketplace',
        'Udyog Connect'
      ].filter(Boolean),
      openGraph: {
        title,
        description,
        type: 'profile',
        images: seller.logo ? [{ url: seller.logo }] : undefined,
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
      },
      other: {
        // Schema.org Organization structured data
        'application-name': 'Udyog Connect',
      }
    };
  } catch {
    return {
      title: 'Seller Catalog | Udyog Connect',
      description: 'Browse seller catalog on Udyog Connect - India\'s B2B industrial marketplace.'
    };
  }
}

export default async function Page({ params }: Props) {
  const { slug } = await params;
  return <SellerCatalogPage slug={slug} />;
}
