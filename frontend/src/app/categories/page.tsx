'use client';

import { useState, useEffect } from 'react';
import { getPublicCategories } from '@/lib/api';
import Link from 'next/link';
import Image from 'next/image';
import { Package, ArrowRight, Zap, Layers, FlaskRound, Building2, Settings, Shield, Loader2 } from 'lucide-react';

interface PublicCategory {
  _id: string;
  name: string;
  slug?: string;  // SEO v2.1: slug for routing
  image?: string;
  icon?: string;
  productCount: number;
  listingCount: number;
}

const iconMap: { [key: string]: React.ReactNode } = {
  'electric': <Zap className="h-12 w-12" />,
  'flash-outline': <Zap className="h-12 w-12" />,
  'layers': <Layers className="h-12 w-12" />,
  'cube-outline': <Package className="h-12 w-12" />,
  'chemical': <FlaskRound className="h-12 w-12" />,
  'flask-outline': <FlaskRound className="h-12 w-12" />,
  'building': <Building2 className="h-12 w-12" />,
  'business-outline': <Building2 className="h-12 w-12" />,
  'settings': <Settings className="h-12 w-12" />,
  'settings-outline': <Settings className="h-12 w-12" />,
  'shield': <Shield className="h-12 w-12" />,
  'shield-outline': <Shield className="h-12 w-12" />,
};

function getIconForCategory(category: PublicCategory) {
  if (category.icon && iconMap[category.icon]) {
    return iconMap[category.icon];
  }
  const lowerName = category.name.toLowerCase();
  if (lowerName.includes('electric') || lowerName.includes('motor')) return iconMap['electric'];
  if (lowerName.includes('chemical')) return iconMap['chemical'];
  if (lowerName.includes('build') || lowerName.includes('construction')) return iconMap['building'];
  if (lowerName.includes('safety') || lowerName.includes('protect')) return iconMap['shield'];
  return <Package className="h-12 w-12" />;
}

function CategoryCard({ category }: { category: PublicCategory }) {
  const [imageError, setImageError] = useState(false);
  const hasImage = category.image && category.image.length > 0 && !imageError;
  
  // SEO v2.1: Use slug-based URL if available
  const categoryUrl = category.slug 
    ? `/categories/${category.slug}` 
    : `/categories/${category._id}`;
  
  return (
    <Link href={categoryUrl} data-testid={`category-card-${category._id}`}>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-lg hover:border-blue-200 transition-all group overflow-hidden h-full">
        {/* Category Image Container - Large & Professional */}
        <div className="relative w-full h-32 sm:h-36 md:h-40 lg:h-44 bg-gradient-to-br from-gray-50 to-gray-100 overflow-hidden">
          {hasImage ? (
            <>
              <Image
                src={category.image!}
                alt={category.name}
                fill
                className="object-cover group-hover:scale-105 transition-transform duration-300"
                sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                onError={() => setImageError(true)}
              />
              {/* Subtle gradient overlay on hover */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-blue-600/80 group-hover:scale-110 transition-transform duration-300">
              {getIconForCategory(category)}
            </div>
          )}
          
          {/* Product count badge */}
          {category.productCount > 0 && (
            <div className="absolute top-3 right-3 px-2 py-1 bg-white/90 backdrop-blur-sm rounded-full text-xs font-medium text-gray-700 shadow-sm">
              {category.productCount} products
            </div>
          )}
        </div>
        
        {/* Card Content */}
        <div className="p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-1">
              {category.name}
            </h3>
            <ArrowRight className="h-4 w-4 text-blue-600 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
          </div>
          {/* <p className="text-sm text-gray-500 mt-1">
            {category.listingCount || 0} sellers
          </p> */}
        </div>
      </div>
    </Link>
  );
}

export default function CategoriesPage() {
  const [categories, setCategories] = useState<PublicCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await getPublicCategories();
        setCategories(data);
      } catch (err) {
        console.error('Failed to fetch categories:', err);
        setError('Failed to load categories');
      } finally {
        setLoading(false);
      }
    };
    fetchCategories();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
        <p className="text-gray-500 mt-4">Loading categories...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">All Categories</h1>
        <p className="text-gray-500 mt-2">Browse industrial products across {categories.length} categories</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {categories.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {categories.map((category) => (
            <CategoryCard key={category._id} category={category} />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-white rounded-xl border border-gray-100">
          <div className="bg-blue-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Package className="h-10 w-10 text-blue-500" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-3">Categories Coming Soon</h3>
          <p className="text-gray-500 max-w-md mx-auto mb-2">
            We&apos;re onboarding verified industrial suppliers across India.
          </p>
          <p className="text-sm text-gray-400 max-w-md mx-auto">
            Categories will appear here once sellers start listing their products. Check back soon!
          </p>
        </div>
      )}
    </div>
  );
}
