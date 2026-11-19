// Owner-approved canonical site origin (apex host, HTTPS).
//
// Single source of truth for every absolute, self-referencing URL the app
// emits: sitemap entries, robots sitemap reference, canonical link tags,
// Open Graph URLs and structured data (Organization / WebSite JSON-LD).
// The apex host is canonical per owner decision (P1 alignment, 2026-11-17).
export const SITE_URL = 'https://udyogconnect.in';

// Legacy www origin. Kept ONLY so absolute URLs received from backend SEO
// payloads that were emitted before the backend switched to the apex can
// still be converted to app-relative paths during the deploy transition.
// Never emit this value; production URLs must always use SITE_URL.
export const LEGACY_WWW_URL = 'https://www.udyogconnect.in';

// Convert an absolute self URL (canonical apex or legacy www) into an
// app-relative path for internal links.
export const toRelativeUrl = (url: string): string =>
  url.replace(SITE_URL, '').replace(LEGACY_WWW_URL, '');

// Origin-safe canonical self URL for SEO metadata emission (Batch 2).
//
// Product and city canonical/og:url values arrive as ABSOLUTE self URLs from
// backend SEO payloads. Those responses are cached by Next's fetch cache
// (`next: { revalidate }`) and by page-level ISR, so a payload fetched before
// the backend switched to the apex origin can still carry the retired www
// host until each URL's revalidation window expires. There is no origin-aware
// invalidation for that cache, so the emission point itself must be safe:
// this helper converts whatever absolute self URL arrives (apex or legacy
// www) into a path and re-anchors it on the approved apex origin, preserving
// the payload's path. Path-only inputs are anchored directly. Missing,
// foreign, or malformed values fall back to the route's own canonical path
// so a canonical/og:url pair is always emitted and always agrees.
export const canonicalSelfUrl = (
  rawUrl: string | null | undefined,
  fallbackPath: string,
): string => {
  const trimmed = (rawUrl ?? '').trim();
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) {
    return `${SITE_URL}${trimmed}`;
  }
  // Only re-anchor absolute URLs that genuinely carry one of the two approved
  // origins (apex or legacy www). Anything else — foreign hosts,
  // protocol-relative "//host/...", garbage — falls back to the route's own
  // canonical path instead of being emitted.
  const fromApprovedOrigin =
    trimmed.startsWith(`${SITE_URL}/`) ||
    trimmed === SITE_URL ||
    trimmed.startsWith(`${LEGACY_WWW_URL}/`) ||
    trimmed === LEGACY_WWW_URL;
  if (fromApprovedOrigin) {
    return `${SITE_URL}${toRelativeUrl(trimmed)}`;
  }
  return `${SITE_URL}${fallbackPath}`;
};
