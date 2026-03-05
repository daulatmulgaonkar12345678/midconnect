import type { Metadata } from 'next';
import PipeWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Pipe Weight Calculator | Calculate Steel Pipe, MS Pipe Weight - UdyogConnect',
  description: 'Free online pipe weight calculator. Calculate weight of MS pipes, SS pipes, seamless pipes, ERW pipes based on outer diameter and thickness. Connect with verified pipe suppliers.',
  keywords: 'pipe weight calculator, steel pipe weight, MS pipe weight, seamless pipe calculator, ERW pipe weight, pipe thickness calculator, India',
  openGraph: {
    title: 'Pipe Weight Calculator | UdyogConnect',
    description: 'Calculate pipe weight instantly using outer diameter and wall thickness. Connect with verified suppliers.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/pipe-weight-calculator',
  },
  alternates: {
    canonical: '/tools/pipe-weight-calculator',
  },
};

export default function PipeWeightCalculatorPage() {
  return <PipeWeightCalculatorClient />;
}
