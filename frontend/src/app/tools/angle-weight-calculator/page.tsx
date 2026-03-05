import type { Metadata } from 'next';
import AngleWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Angle Weight Calculator | Calculate L Angle Steel Weight - UdyogConnect',
  description: 'Free online L-angle weight calculator. Calculate weight of equal and unequal angle sections in MS Steel, SS304 instantly. Connect with verified suppliers in India.',
  keywords: 'angle weight calculator, L angle weight, equal angle weight, unequal angle calculator, steel angle weight, structural angle, India',
  openGraph: {
    title: 'Angle Weight Calculator | UdyogConnect',
    description: 'Calculate L-angle section weight instantly and connect with verified suppliers across India.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/angle-weight-calculator',
  },
  alternates: {
    canonical: '/tools/angle-weight-calculator',
  },
};

export default function AngleWeightCalculatorPage() {
  return <AngleWeightCalculatorClient />;
}
