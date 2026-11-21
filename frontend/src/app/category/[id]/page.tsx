import { notFound, permanentRedirect } from 'next/navigation';

const API_URL = process.env.REACT_APP_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || '';

interface Props {
  params: Promise<{ id: string }>;
}

interface CategoryResolveResponse {
  category?: { slug?: string | null } | null;
}

interface CategoryRedirectResponse {
  redirect?: boolean;
  slug?: string | null;
}

/**
 * SEO v2.1 / Batch 6 - Legacy category route.
 *
 * Old: /category/{id}
 * New: /categories/{slug}
 *
 * Batch 6 final remediation:
 * - Correction 4: Next.js permanentRedirect()/notFound() drive the router by
 *   THROWING a control-flow error. Data lookups run inside a helper that
 *   returns null on failure; both redirect calls and the final notFound()
 *   execute strictly OUTSIDE any try/catch, so a catch block can never
 *   swallow a redirect.
 * - Correction 5: every fallback API response is validated (HTTP ok) BEFORE
 *   it is parsed as JSON.
 * - Redirects go only to a resolved canonical slug; unresolved identifiers
 *   answer a real 404 — never forwarded to /categories/{id}.
 */
async function fetchJsonOrNull<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000)
    });
    // Validate the HTTP response BEFORE parsing JSON (correction 5).
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    // Network/timeout/parse failure: no mapping data. Redirect control-flow
    // errors cannot originate here — the redirect helpers are only called by
    // the page component outside any try/catch (correction 4).
    return null;
  }
}

export default async function CategoryRedirectPage({ params }: Props) {
  const { id } = await params;

  // Primary: enterprise resolver (deterministic: exact slug, ObjectId,
  // explicit legacySlugs/legacyIds only — Batch 6).
  const resolverData = await fetchJsonOrNull<CategoryResolveResponse>(
    `${API_URL}/api/enterprise/resolve/category/${id}`
  );
  const resolverSlug = resolverData?.category?.slug;
  if (resolverSlug) {
    // Outside try/catch: permanentRedirect throws by design (correction 4).
    permanentRedirect(`/categories/${resolverSlug}`);
  }

  // Fallback: explicit redirect mapping (legacyIds / legacySlugs).
  const mappingData = await fetchJsonOrNull<CategoryRedirectResponse>(
    `${API_URL}/api/redirect/category/${id}`
  );
  if (mappingData?.redirect === true && mappingData.slug) {
    permanentRedirect(`/categories/${mappingData.slug}`);
  }

  // No resolvable canonical slug: a genuine 404.
  notFound();
}
