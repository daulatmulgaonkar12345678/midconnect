import type { Metadata } from 'next';
import { Geist } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import { SEO, APP_KEYWORDS } from '@/lib/config';

const geist = Geist({ subsets: ['latin'] });

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
      <body className={`${geist.className} antialiased`}>
        <AuthProvider>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
