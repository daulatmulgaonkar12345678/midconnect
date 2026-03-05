import type { Metadata } from 'next';
import BeamWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Beam Weight Calculator | Calculate I Beam & H Beam Weight - UdyogConnect',
  description: 'Free online beam weight calculator. Calculate weight of I-beam, H-beam, ISMB, ISHB in MS Steel instantly. Connect with verified suppliers in India.',
  keywords: 'beam weight calculator, I beam weight, H beam weight, ISMB weight, ISHB weight, structural beam calculator, steel beam, India',
  openGraph: {
    title: 'Beam Weight Calculator | UdyogConnect',
    description: 'Calculate I-beam and H-beam weight instantly and connect with verified suppliers across India.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/beam-weight-calculator',
  },
  alternates: {
    canonical: '/tools/beam-weight-calculator',
  },
};

export default function BeamWeightCalculatorPage() {
  return <BeamWeightCalculatorClient />;
}
