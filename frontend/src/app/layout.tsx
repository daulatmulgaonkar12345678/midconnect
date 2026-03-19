import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';
import IndustrialHeader from '@/components/IndustrialHeader';
import Footer from '@/components/Footer';
import { SEO, APP_KEYWORDS } from '@/lib/config';
import ServerWarmUp from '@/components/ServerWarmUp';
import ServiceWorkerRegister from '@/components/ServiceWorkerRegister';

// Use Inter font for industrial/corporate look
const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600', '700'] });

export const metadata: Metadata = {
  title: SEO.title,
  description: SEO.description,
  keywords: APP_KEYWORDS,
  icons: {
    icon: 'https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/o4stdhdf_image.png',
    shortcut: 'https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/o4stdhdf_image.png',
    apple: 'https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/o4stdhdf_image.png',
  },
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
      <head>
        <link rel="icon" href="/favicon.png" type="image/png" sizes="any" />
        <link rel="shortcut icon" href="/favicon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/favicon.png" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#4f46e5" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="UdyogConnect" />
      </head>
      <body className={`${inter.className} antialiased bg-gray-50`}>
        <AuthProvider>
          <ServerWarmUp />
          <ServiceWorkerRegister />
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
