import Link from 'next/link';
import Image from 'next/image';
import { Category } from '@/types';
import { 
  Zap, Layers, FlaskRound, Building2, Settings, Shield, Package 
} from 'lucide-react';

const iconMap: { [key: string]: React.ReactNode } = {
  'flash-outline': <Zap className="h-8 w-8" />,
  'cube-outline': <Package className="h-8 w-8" />,
  'flask-outline': <FlaskRound className="h-8 w-8" />,
  'business-outline': <Building2 className="h-8 w-8" />,
  'settings-outline': <Settings className="h-8 w-8" />,
  'shield-outline': <Shield className="h-8 w-8" />,
};

interface CategoryCardProps {
  category: Category;
}

export default function CategoryCard({ category }: CategoryCardProps) {
  // Check if category has an uploaded image
  const hasImage = category.image && category.image.length > 0;
  
  return (
    <Link href={`/category/${category._id}`}>
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
              {category.icon && iconMap[category.icon] ? iconMap[category.icon] : <Package className="h-8 w-8" />}
            </div>
          )}
        </div>
        <h3 className="font-semibold text-gray-900 mb-2">{category.name}</h3>
        <p className="text-sm text-gray-500 line-clamp-2">{category.description}</p>
      </div>
    </Link>
  );
}
