'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Category } from '@/types';
import { 
  Zap, Layers, FlaskRound, Building2, Settings, Shield, Package, ArrowRight 
} from 'lucide-react';
import { useState } from 'react';

const iconMap: { [key: string]: React.ReactNode } = {
  'flash-outline': <Zap className="h-12 w-12" />,
  'cube-outline': <Package className="h-12 w-12" />,
  'flask-outline': <FlaskRound className="h-12 w-12" />,
  'business-outline': <Building2 className="h-12 w-12" />,
  'settings-outline': <Settings className="h-12 w-12" />,
  'shield-outline': <Shield className="h-12 w-12" />,
  'electric': <Zap className="h-12 w-12" />,
  'chemical': <FlaskRound className="h-12 w-12" />,
  'building': <Building2 className="h-12 w-12" />,
};

interface CategoryCardProps {
  category: Category | {
    _id: string;
    name: string;
    image?: string;
    icon?: string;
    productCount?: number;
    listingCount?: number;
  };
  showProductCount?: boolean;
}

export default function CategoryCard({ category, showProductCount = true }: CategoryCardProps) {
  const [imageError, setImageError] = useState(false);
  
  // Check if category has an uploaded image
  const hasImage = category.image && category.image.length > 0 && !imageError;
  
  // Get icon based on category
  const getIcon = () => {
    if (category.icon && iconMap[category.icon]) {
      return iconMap[category.icon];
    }
    // Fallback: try to match by name
    const lowerName = category.name.toLowerCase();
    if (lowerName.includes('electric') || lowerName.includes('motor')) return iconMap['electric'];
    if (lowerName.includes('chemical')) return iconMap['chemical'];
    if (lowerName.includes('build') || lowerName.includes('construction')) return iconMap['building'];
    return <Package className="h-12 w-12" />;
  };
  
  return (
    <Link href={`/category/${category._id}`} data-testid={`category-card-${category._id}`}>
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
              {/* Subtle gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-blue-600/80 group-hover:scale-110 transition-transform duration-300">
              {getIcon()}
            </div>
          )}
          
          {/* Product count badge */}
          {showProductCount && category.productCount !== undefined && category.productCount > 0 && (
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
          {category.description && (
            <p className="text-sm text-gray-500 mt-1 line-clamp-2">{category.description}</p>
          )}
        </div>
      </div>
    </Link>
  );
}
