import { Metadata } from 'next';
import { getCategories } from '@/lib/api';
import CategoryCard from '@/components/CategoryCard';
import { Category } from '@/types';

export const metadata: Metadata = {
  title: 'All Categories - MidConnect',
  description: 'Browse all industrial product categories. Electrical equipment, steel & metals, chemicals, building materials, and more.',
};

export const revalidate = 3600;

export default async function CategoriesPage() {
  let categories: Category[] = [];

  try {
    categories = await getCategories();
  } catch (error) {
    console.error('Failed to fetch categories:', error);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">All Categories</h1>
        <p className="text-gray-500 mt-2">Browse industrial products across {categories.length} categories</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {categories.map((category) => (
          <CategoryCard key={category._id} category={category} />
        ))}
      </div>
    </div>
  );
}
