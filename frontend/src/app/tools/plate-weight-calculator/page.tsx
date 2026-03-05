import type { Metadata } from 'next';
import PlateWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Plate Weight Calculator | Steel Plate, MS Plate Weight - UdyogConnect',
  description: 'Free online plate weight calculator. Calculate weight of MS plates, SS plates, chequered plates, and sheet metal based on thickness and dimensions. Connect with plate suppliers.',
  keywords: 'plate weight calculator, steel plate weight, MS plate weight, sheet metal calculator, chequered plate weight, plate thickness calculator, India',
  openGraph: {
    title: 'Plate Weight Calculator | UdyogConnect',
    description: 'Calculate steel plate and sheet metal weight instantly. Connect with verified suppliers.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/plate-weight-calculator',
  },
  alternates: {
    canonical: '/tools/plate-weight-calculator',
  },
};

export default function PlateWeightCalculatorPage() {
  return <PlateWeightCalculatorClient />;
}
