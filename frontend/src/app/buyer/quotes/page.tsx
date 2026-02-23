'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { getBuyerQuotes, Quote } from '@/lib/api';
import Link from 'next/link';
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  FileText,
  Package,
  Building2,
  Clock,
  CheckCircle,
  XCircle,
  ChevronRight,
  Calendar
} from 'lucide-react';

type QuoteStatus = '' | 'sent' | 'viewed' | 'accepted' | 'rejected' | 'expired';

const statusTabs: { value: QuoteStatus; label: string; color: string }[] = [
  { value: '', label: 'All', color: 'bg-gray-100 text-gray-700' },
  { value: 'sent', label: 'New', color: 'bg-blue-100 text-blue-700' },
  { value: 'viewed', label: 'Viewed', color: 'bg-purple-100 text-purple-700' },
  { value: 'accepted', label: 'Accepted', color: 'bg-green-100 text-green-700' },
  { value: 'rejected', label: 'Rejected', color: 'bg-red-100 text-red-700' },
  { value: 'expired', label: 'Expired', color: 'bg-gray-100 text-gray-600' }
];

export default function BuyerQuotesPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<QuoteStatus>('');

  useEffect(() => {
    const loadQuotes = async () => {
      try {
        setLoading(true);
        const token = await getIdToken();
        if (!token) {
          router.push('/login');
          return;
        }

        const data = await getBuyerQuotes(token, {
          status: statusFilter || undefined,
          page,
          limit: 20
        });

        setQuotes(data.quotes);
        setTotal(data.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load quotes');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadQuotes();
      }
    }
  }, [user, authLoading, getIdToken, router, statusFilter, page]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short'
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'sent':
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">New</span>;
      case 'viewed':
        return <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">Viewed</span>;
      case 'accepted':
        return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1"><CheckCircle className="h-3 w-3" /> Accepted</span>;
      case 'rejected':
        return <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium flex items-center gap-1"><XCircle className="h-3 w-3" /> Rejected</span>;
      case 'expired':
        return <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium flex items-center gap-1"><Clock className="h-3 w-3" /> Expired</span>;
      default:
        return null;
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/buyer" className="p-2 hover:bg-gray-100 rounded-lg" data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-600" />
                My Quotes
              </h1>
              <p className="text-sm text-gray-500">Quotations received from sellers</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Status Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {statusTabs.map(tab => (
            <button
              key={tab.value}
              onClick={() => { setStatusFilter(tab.value); setPage(1); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition ${
                statusFilter === tab.value 
                  ? tab.color 
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
              data-testid={`tab-${tab.value || 'all'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {quotes.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Quotes Yet</h3>
            <p className="text-gray-600 max-w-md mx-auto">
              When sellers send you quotations, they will appear here. Start by sending inquiries to products you're interested in.
            </p>
            <Link 
              href="/"
              className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Browse Products
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {quotes.map((quote) => (
              <Link 
                key={quote.quoteId}
                href={`/quote/${quote.quoteId}`}
                className="block bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition"
                data-testid={`quote-card-${quote.quoteId}`}
              >
                <div className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Product Icon */}
                    <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Package className="h-6 w-6 text-gray-400" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900 truncate">{quote.productName}</h3>
                        {getStatusBadge(quote.status)}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <Building2 className="h-3.5 w-3.5" />
                          {quote.sellerName}
                        </span>
                        <span className="font-medium text-blue-600">
                          {formatCurrency(quote.totalPrice)}
                        </span>
                        <span className="flex items-center gap-1 text-gray-400">
                          <Calendar className="h-3.5 w-3.5" />
                          Valid till {formatDate(quote.validityDate)}
                        </span>
                      </div>

                      <div className="mt-2 flex items-center gap-4 text-sm">
                        <span className="text-gray-600">
                          Qty: {quote.requestedQuantity} × {formatCurrency(quote.unitPrice)}
                        </span>
                        <span className="text-gray-400">
                          MOQ: {quote.moq}
                        </span>
                      </div>
                    </div>

                    <ChevronRight className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  </div>
                </div>

                {/* Action indicator */}
                {(quote.status === 'sent' || quote.status === 'viewed') && (
                  <div className="px-4 py-2 bg-blue-50 border-t border-blue-100 text-sm text-blue-700">
                    Tap to view and respond to this quote
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > 20 && (
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-gray-600">
              Page {page} of {Math.ceil(total / 20)}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(total / 20)}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
