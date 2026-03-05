import type { Metadata } from 'next';
import RoundBarWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Round Bar Weight Calculator | MS Round Bar, SS Round Bar Weight - UdyogConnect',
  description: 'Free online round bar weight calculator. Calculate weight of MS round bars, SS round bars, bright bars, and TMT bars based on diameter and length. Connect with bar suppliers.',
  keywords: 'round bar weight calculator, MS round bar weight, bright bar weight, TMT bar calculator, steel bar weight per meter, rod weight calculator, India',
  openGraph: {
    title: 'Round Bar Weight Calculator | UdyogConnect',
    description: 'Calculate round bar and rod weight instantly using diameter and length. Connect with verified suppliers.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/round-bar-weight-calculator',
  },
  alternates: {
    canonical: '/tools/round-bar-weight-calculator',
  },
};

export default function RoundBarWeightCalculatorPage() {
  return <RoundBarWeightCalculatorClient />;
}
