import type { Metadata } from 'next';
import SteelWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Steel Weight Calculator | Calculate MS Steel, SS304, SS316 Weight - UdyogConnect',
  description: 'Free online steel weight calculator. Calculate weight of MS steel, stainless steel (SS304, SS316), round bars, pipes, plates instantly. Connect with verified steel suppliers in India.',
  keywords: 'steel weight calculator, MS steel weight, SS304 weight calculator, steel bar weight, steel plate weight, steel pipe weight, steel density calculator, India',
  openGraph: {
    title: 'Steel Weight Calculator | UdyogConnect',
    description: 'Calculate steel weight instantly and connect with verified suppliers across India.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/steel-weight-calculator',
  },
  alternates: {
    canonical: '/tools/steel-weight-calculator',
  },
};

export default function SteelWeightCalculatorPage() {
  return <SteelWeightCalculatorClient />;
}
