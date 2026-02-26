import { Metadata } from 'next';
import { getPublicCategories } from '@/lib/api';
import Link from 'next/link';
import Image from 'next/image';
import { Package, ArrowRight, Zap, Layers, FlaskRound, Building2, Settings, Shield } from 'lucide-react';

export const metadata: Metadata = {
  title: 'All Categories - MidConnect',
  description: 'Browse all industrial product categories. Electrical equipment, steel & metals, chemicals, building materials, and more.',
};

export const revalidate = 60; // 1 minute to reflect seller activity

interface PublicCategory {
  _id: string;
  name: string;
  image?: string;
  icon?: string;
  productCount: number;
  listingCount: number;
}

const iconMap: { [key: string]: React.ReactNode } = {
  'electric': <Zap className="h-8 w-8" />,
  'flash-outline': <Zap className="h-8 w-8" />,
  'layers': <Layers className="h-8 w-8" />,
  'cube-outline': <Package className="h-8 w-8" />,
  'chemical': <FlaskRound className="h-8 w-8" />,
  'flask-outline': <FlaskRound className="h-8 w-8" />,
  'building': <Building2 className="h-8 w-8" />,
  'business-outline': <Building2 className="h-8 w-8" />,
  'settings': <Settings className="h-8 w-8" />,
  'settings-outline': <Settings className="h-8 w-8" />,
  'shield': <Shield className="h-8 w-8" />,
  'shield-outline': <Shield className="h-8 w-8" />,
};

function getIconForCategory(category: PublicCategory) {
  // If category has icon mapping, use it
  if (category.icon && iconMap[category.icon]) {
    return iconMap[category.icon];
  }
  // Fallback: try to match by name
  const lowerName = category.name.toLowerCase();
  if (lowerName.includes('electric') || lowerName.includes('motor')) return iconMap['electric'];
  if (lowerName.includes('chemical')) return iconMap['chemical'];
  if (lowerName.includes('build') || lowerName.includes('construction')) return iconMap['building'];
  if (lowerName.includes('safety') || lowerName.includes('protect')) return iconMap['shield'];
  return <Package className="h-8 w-8" />;
}

export default async function CategoriesPage() {
  let categories: PublicCategory[] = [];

  try {
    categories = await getPublicCategories();
  } catch (error) {
    console.error('Failed to fetch categories:', error);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">All Categories</h1>
        <p className="text-gray-500 mt-2">Browse industrial products across {categories.length} categories</p>
      </div>

      {categories.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {categories.map((category) => {
            const hasImage = category.image && category.image.length > 0;
            return (
              <Link key={category._id} href={`/category/${category._id}`}>
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:border-blue-200 transition-all group">
                  {/* Category Image or Icon */}
                  <div className="mb-4">
                    {hasImage ? (
                      <div className="relative w-16 h-16 rounded-lg overflow-hidden group-hover:scale-110 transition-transform">
                        <Image
                          src={category.image!}
                          alt={category.name}
                          fill
                          className="object-cover"
                          sizes="64px"
                        />
                      </div>
                    ) : (
                      <div className="text-blue-600 group-hover:scale-110 transition-transform">
                        {getIconForCategory(category)}
                      </div>
                    )}
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{category.name}</h3>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">{category.productCount} products</span>
                    <ArrowRight className="h-4 w-4 text-blue-600 opacity-0 group-hover:opacity-100 transition" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-xl">
          <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Categories Yet</h3>
          <p className="text-gray-500">
            Categories appear here when sellers list products for sale.
          </p>
        </div>
      )}
    </div>
  );
}
