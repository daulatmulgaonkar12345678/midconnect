// Batch 3 (2026-11-19) server-rendered product hero tests (node:test).
//
// /products/{slug} previously shipped a 'use client' shell whose initial HTML
// contained metadata + JSON-LD but zero visible product content (no H1, just
// "Loading product…"). The remediation renders a server-side hero
// (ProductSeoHero) from the existing public /seo payload and moves the
// interactive page to ProductPageClient.tsx (client island).
//
// Behavioral tests exercise the REAL compiled sources
// (dist/lib/productSeoServer.js, dist/components/product/ProductSeoHero.js)
// through tsc -p tests/seo/tsconfig.seo.json; third-party UI libraries
// (next/link, lucide-react) are stubbed at the module seam only.
import test from 'node:test';
import assert from 'node:assert/strict';
import Module from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, 'dist');
const require = createRequire(import.meta.url);
const React = require('react');

// Map the "@/..." tsconfig path alias to the compiled CommonJS output and
// seam out third-party UI libraries (tsc does not rewrite path aliases).
const stub = (name) => path.join(here, 'stubs', name);
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (request.startsWith('@/')) {
    return originalResolve.call(this, path.join(dist, request.slice(2)), ...rest);
  }
  if (request === 'next/link') {
    return originalResolve.call(this, stub('next-link.js'), ...rest);
  }
  if (request === 'lucide-react') {
    return originalResolve.call(this, stub('lucide-react.js'), ...rest);
  }
  return originalResolve.call(this, request, ...rest);
};

process.env.REACT_APP_BACKEND_URL = 'http://127.0.0.1:3999';

const { fetchProductSeoPayload } = require(path.join(dist, 'lib', 'productSeoServer.js'));
const { default: ProductSeoHero } = require(path.join(dist, 'components', 'product', 'ProductSeoHero.js'));
const { renderToStaticMarkup } = require('react-dom/server');

const SLUG = 'vfd-vfd-plc-hmi-control-equipments-supplier-india';
const FIXTURE = {
  productName: 'VFD',
  seoTitle: 'Compare VFD Prices in India (2026) | UdyogConnect',
  seoDescription: 'Variable frequency drives (VFD) for smooth motor speed control',
  categoryName: 'VFD, PLC, HMI & Control Equipments',
  sellerCount: 1,
  listingCount: 14,
  verifiedSellerCount: 1,
  minPrice: 5000,
  maxPrice: 12000,
};

const renderHero = (payload) => renderToStaticMarkup(React.createElement(ProductSeoHero, { payload }));

async function withFetch(stub, fn) {
  const original = globalThis.fetch;
  globalThis.fetch = stub;
  try {
    return await fn();
  } finally {
    globalThis.fetch = original;
  }
}

// ---------- fetchProductSeoPayload (server-side data path) ----------

test('fetchProductSeoPayload hits the public /seo endpoint with the ISR cache policy', async () => {
  let capturedUrl = '';
  let capturedInit = null;
  const result = await withFetch(
    (url, init) => {
      capturedUrl = String(url);
      capturedInit = init;
      return { ok: true, status: 200, json: async () => FIXTURE };
    },
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(capturedUrl, `http://127.0.0.1:3999/api/products/${SLUG}/seo`);
  assert.deepEqual(capturedInit.next, { revalidate: 3600 });
  assert.equal(result.notFound, false);
  assert.equal(result.payload.productName, FIXTURE.productName);
  assert.equal(result.payload.seoDescription, FIXTURE.seoDescription);
});

test('legacy ObjectId slugs never hit the API and are not a definitive 404', async () => {
  let calls = 0;
  const result = await withFetch(
    () => { calls += 1; return { ok: true, json: async () => FIXTURE }; },
    () => fetchProductSeoPayload('6a44cd478b430643bfad1873'),
  );
  assert.equal(calls, 0);
  assert.equal(result.payload, null);
  assert.equal(result.notFound, false);
});

test('definitive backend 404 flags the slug as not found (Batch 5: page renders the 404 boundary)', async () => {
  const result = await withFetch(
    () => ({ ok: false, status: 404, json: async () => ({}) }),
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(result.payload, null);
  assert.equal(result.notFound, true);
});

test('non-404 failures stay transient (notFound false, fallback behavior preserved)', async () => {
  const serverError = await withFetch(
    () => ({ ok: false, status: 503, json: async () => ({}) }),
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(serverError.payload, null);
  assert.equal(serverError.notFound, false);

  const thrown = await withFetch(
    () => { throw new Error('backend down'); },
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(thrown.payload, null);
  assert.equal(thrown.notFound, false);
});

// ---------- ProductSeoHero (initial-HTML content) ----------

test('hero renders the real product name as exactly one H1', () => {
  const html = renderHero(FIXTURE);
  assert.equal((html.match(/<h1/g) || []).length, 1);
  assert.match(html, /data-testid="seo-hero-name"/);
  assert.ok(html.includes(FIXTURE.productName));
});

test('hero renders the payload SEO description verbatim', () => {
  const html = renderHero(FIXTURE);
  assert.match(html, /data-testid="seo-hero-description"/);
  assert.ok(html.includes(`>${FIXTURE.seoDescription}</p>`));
});

test('hero renders a price chip only from real numeric payload values', () => {
  const priced = renderHero(FIXTURE);
  assert.match(priced, /data-testid="seo-hero-price"/);
  assert.ok(priced.includes('From'));
  assert.ok(priced.includes('5,000'));

  const maxOnly = renderHero({ ...FIXTURE, minPrice: null });
  assert.ok(maxOnly.includes('Up to'));
  assert.ok(maxOnly.includes('12,000'));

  const unpriced = renderHero({ ...FIXTURE, minPrice: null, maxPrice: null });
  assert.doesNotMatch(unpriced, /data-testid="seo-hero-price"/);
  assert.doesNotMatch(unpriced, /From|Up to/);
});

test('hero renders a seller chip only when sellerCount is a positive number', () => {
  assert.ok(renderHero(FIXTURE).match(/data-testid="seo-hero-seller-count"/));
  assert.ok(renderHero(FIXTURE).includes('Seller'));
  assert.ok(renderHero({ ...FIXTURE, sellerCount: 3 }).includes('Sellers'));

  const zero = renderHero({ ...FIXTURE, sellerCount: 0 });
  assert.doesNotMatch(zero, /data-testid="seo-hero-seller-count"/);

  const unknown = renderHero({ ...FIXTURE, sellerCount: undefined });
  assert.doesNotMatch(unknown, /data-testid="seo-hero-seller-count"/);
});

test('hero renders nothing without a real product name (no fabricated heading)', () => {
  assert.equal(renderHero({ ...FIXTURE, productName: undefined }), '');
  assert.equal(renderHero({ ...FIXTURE, productName: '' }), '');
  assert.equal(renderHero({}), '');
  assert.equal(renderHero(null ?? undefined), '');
});

test('hero markup contains no content beyond payload values and fixed labels (anti-fabrication)', () => {
  const html = renderHero(FIXTURE);
  let text = html.replace(/<!--[\s\S]*?-->/g, ' ').replace(/<[^>]+>/g, ' ');
  text = text
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#x27;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  const removable = [
    FIXTURE.productName, FIXTURE.seoDescription, FIXTURE.categoryName,
    'Home', 'Products', 'Seller', 'Sellers', 'From', 'Up to', '₹',
    '1', '3', '5,000', '12,000', '14',
  ].filter(Boolean).sort((a, b) => b.length - a.length); // longest first: 'VFD' is a substring of the category/description
  for (const piece of removable) text = text.split(piece).join(' ');
  const leftoverWords = (text.match(/[A-Za-z]{3,}/g) || []).join(' ');
  assert.equal(leftoverWords, '');
});

// ---------- structural invariants (single H1 / Batch 1 & 2 preservation) ----------

const islandSrc = readFileSync(
  path.join(here, '..', '..', 'src', 'app', 'products', '[slug]', '(main)', 'ProductPageClient.tsx'),
  'utf8',
);
const shellSrc = readFileSync(
  path.join(here, '..', '..', 'src', 'app', 'products', '[slug]', '(main)', 'page.tsx'),
  'utf8',
);
const layoutSrc = readFileSync(
  path.join(here, '..', '..', 'src', 'app', 'products', '[slug]', '(main)', 'layout.tsx'),
  'utf8',
);
const heroSrc = readFileSync(
  path.join(here, '..', '..', 'src', 'components', 'product', 'ProductSeoHero.tsx'),
  'utf8',
);

test('client island no longer emits an H1, breadcrumb, seller-count or price chip', () => {
  assert.doesNotMatch(islandSrc, /<h1/);
  assert.doesNotMatch(islandSrc, /data-testid="product-name"/);
  assert.doesNotMatch(islandSrc, /<ChevronRight/);
  assert.doesNotMatch(islandSrc, /<Users/);
  assert.doesNotMatch(islandSrc, /bg-blue-50 text-blue-700/);
  assert.doesNotMatch(islandSrc, /bg-green-50 text-green-700/);
});

test('client island keeps its interactivity (client component with data fetching)', () => {
  assert.match(islandSrc, /^'use client';/);
  assert.match(islandSrc, /getEnterpriseProduct/);
  assert.match(islandSrc, /getProductFacets/);
  assert.match(islandSrc, /filterProductListings/);
  assert.match(islandSrc, /Loading product\.\.\./);
});

test('server shell renders hero before the island and falls back to island-only on null payload', () => {
  assert.match(shellSrc, /import ProductSeoHero/);
  assert.match(shellSrc, /import \{ fetchProductSeoPayload \} from '@\/lib\/productSeoServer';/);
  assert.match(shellSrc, /import ProductPageClient from '\.\/ProductPageClient';/);
  assert.match(shellSrc, /\{\s*payload && <ProductSeoHero payload=\{payload\} \/>/);
  assert.ok(shellSrc.includes('<ProductPageClient />'));
});

test('layout keeps Batch 2 canonical normalization and owns metadata + JSON-LD', () => {
  assert.match(layoutSrc, /canonicalSelfUrl\(seoData\.canonicalUrl, `\/products\/\$\{slug\}`\)/);
  assert.doesNotMatch(layoutSrc, /www\.udyogconnect\.in/);
  assert.match(layoutSrc, /application\/ld\+json/);
  assert.match(layoutSrc, /fetchProductSeoPayload/);
});

test('hero is a pure server component (no client directive, no hooks)', () => {
  assert.doesNotMatch(heroSrc, /^['\"]use client['\"];?/m);
  assert.doesNotMatch(heroSrc, /useState|useEffect|useMemo|useCallback/);
  assert.match(heroSrc, /data-testid="seo-hero-name"/);
});
