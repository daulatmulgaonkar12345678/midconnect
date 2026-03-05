import type { Metadata } from 'next';
import HexBarWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Hex Bar Weight Calculator | Calculate Hexagonal Steel Bar Weight - UdyogConnect',
  description: 'Free online hexagonal bar weight calculator. Calculate weight of hex bars in MS Steel, SS304, SS316, Aluminum instantly. Connect with verified suppliers in India.',
  keywords: 'hex bar weight calculator, hexagonal bar weight, hex steel bar calculator, hex rod weight, across flats calculator, India',
  openGraph: {
    title: 'Hex Bar Weight Calculator | UdyogConnect',
    description: 'Calculate hexagonal bar weight instantly and connect with verified suppliers across India.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/hex-bar-weight-calculator',
  },
  alternates: {
    canonical: '/tools/hex-bar-weight-calculator',
  },
};

export default function HexBarWeightCalculatorPage() {
  return <HexBarWeightCalculatorClient />;
}
