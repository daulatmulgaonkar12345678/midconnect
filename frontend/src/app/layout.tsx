import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';
import IndustrialHeader from '@/components/IndustrialHeader';
import Footer from '@/components/Footer';
import { SEO, APP_KEYWORDS } from '@/lib/config';
import ServerWarmUp from '@/components/ServerWarmUp';

// Use Inter font for industrial/corporate look
const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600', '700'] });

export const metadata: Metadata = {
  title: SEO.title,
  description: SEO.description,
  keywords: APP_KEYWORDS,
  openGraph: {
    title: SEO.ogTitle,
    description: SEO.ogDescription,
    type: 'website',
  },
  twitter: {
    card: SEO.twitterCard,
    title: SEO.title,
    description: SEO.ogDescription,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased bg-gray-50`}>
        <AuthProvider>
          <div className="min-h-screen flex flex-col">
            <IndustrialHeader />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
