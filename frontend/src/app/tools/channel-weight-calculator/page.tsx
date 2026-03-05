import type { Metadata } from 'next';
import ChannelWeightCalculatorClient from './client';

export const metadata: Metadata = {
  title: 'Channel Weight Calculator | Calculate C Channel Steel Weight - UdyogConnect',
  description: 'Free online C-channel weight calculator. Calculate weight of ISMC, ISLC channels in MS Steel, SS304 instantly. Connect with verified suppliers in India.',
  keywords: 'channel weight calculator, C channel weight, ISMC weight, ISLC weight, steel channel calculator, structural channel, India',
  openGraph: {
    title: 'Channel Weight Calculator | UdyogConnect',
    description: 'Calculate C-channel section weight instantly and connect with verified suppliers across India.',
    type: 'website',
    url: 'https://udyogconnect.com/tools/channel-weight-calculator',
  },
  alternates: {
    canonical: '/tools/channel-weight-calculator',
  },
};

export default function ChannelWeightCalculatorPage() {
  return <ChannelWeightCalculatorClient />;
}
