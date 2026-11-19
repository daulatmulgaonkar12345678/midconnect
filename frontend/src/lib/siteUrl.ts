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
