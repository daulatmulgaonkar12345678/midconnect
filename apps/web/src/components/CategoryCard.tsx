import Link from 'next/link';
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
  return (
    <Link href={`/category/${category._id}`}>
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:border-blue-200 transition-all group">
        <div className="text-blue-600 mb-4 group-hover:scale-110 transition-transform">
          {category.icon && iconMap[category.icon] ? iconMap[category.icon] : <Package className="h-8 w-8" />}
        </div>
        <h3 className="font-semibold text-gray-900 mb-2">{category.name}</h3>
        <p className="text-sm text-gray-500 line-clamp-2">{category.description}</p>
      </div>
    </Link>
  );
}
