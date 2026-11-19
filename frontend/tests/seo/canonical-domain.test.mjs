// P1 canonical-domain alignment tests (node:test).
//
// Exercises the REAL compiled sitemap()/robots() code paths with a mocked
// backend API, and asserts every emitted URL uses the owner-approved apex
// origin https://udyogconnect.in — no www, no duplicates, eligibility intact.
import test from 'node:test';
import assert from 'node:assert/strict';
import Module from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import fs from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, 'dist');

// Map the "@/..." tsconfig path alias to the compiled CommonJS output
// (tsc does not rewrite path aliases at emit time).
const stub = (name) => path.join(here, 'stubs', name);
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (request.startsWith('@/')) {
    return originalResolve.call(this, path.join(dist, request.slice(2)), ...rest);
  }
  if (request === 'next/font/google') {
    return originalResolve.call(this, stub('next-font-google.js'), ...rest);
  }
  if (request.endsWith('.css')) {
    return originalResolve.call(this, stub('empty.js'), ...rest);
  }
  return originalResolve.call(this, request, ...rest);
};

// Deterministic backend payloads. The empty productSlug and the
// cityEligible=false pair must NOT produce sitemap entries.
const apiData = new Map([
  ['/api/seo/sitemap-products', {
    products: [
      { productSlug: 'abb-contactor', lastModified: '2026-11-01T10:00:00Z' },
      { productSlug: '' },
    ],
  }],
  ['/api/categories', {
    categories: [
      { name: 'Circuit Breakers', slug: 'circuit-breakers' },
      { name: 'Industrial Pumps' },
    ],
  }],
  ['/api/seo/sitemap-city-pages', {
    pairs: [
      { productSlug: 'abb-contactor', citySlug: 'mumbai', lastModified: '2026-11-02T00:00:00Z', cityEligible: true, priceEligible: true, suppliersEligible: true },
      { productSlug: 'never-eligible', citySlug: 'delhi', lastModified: null, cityEligible: false, priceEligible: true, suppliersEligible: true },
    ],
  }],
]);

globalThis.fetch = async (input) => {
  const url = String(input);
  for (const [suffix, data] of apiData) {
    if (url.includes(suffix)) return { ok: true, json: async () => data };
  }
  return { ok: false, json: async () => ({}) };
};

const require = createRequire(import.meta.url);
const { default: sitemap } = require(path.join(dist, 'app', 'sitemap.js'));
const { default: robots } = require(path.join(dist, 'app', 'robots.js'));

const APEX = 'https://udyogconnect.in';
const urls = async () => (await sitemap()).map((e) => e.url);

test('robots sitemap reference uses the apex HTTPS origin', () => {
  assert.equal(robots().sitemap, `${APEX}/sitemap.xml`);
});

test('sitemap emits only apex HTTPS URLs', async () => {
  const all = await urls();
  assert.ok(all.length > 0, 'sitemap should not be empty');
  for (const url of all) {
    assert.ok(url.startsWith('https://'), `non-HTTPS URL: ${url}`);
    assert.ok(url === APEX || url.startsWith(`${APEX}/`), `non-apex URL: ${url}`);
    assert.ok(!url.includes('www.udyogconnect'), `www URL emitted: ${url}`);
    assert.ok(!url.includes('udyogconnect.com'), `wrong domain emitted: ${url}`);
  }
});

test('homepage entry is the bare apex origin, exactly once', async () => {
  const all = await urls();
  assert.ok(all.includes(APEX), `homepage entry must be ${APEX}`);
  assert.equal(all.filter((u) => u === APEX).length, 1, 'duplicate homepage canonical');
});

test('product URLs use the apex domain', async () => {
  const all = await urls();
  assert.ok(all.includes(`${APEX}/products/abb-contactor`), `missing product URL in: ${all.join(', ')}`);
});

test('category URLs use the apex domain (stored slug and slugified fallback)', async () => {
  const all = await urls();
  assert.ok(all.includes(`${APEX}/categories/circuit-breakers`));
  assert.ok(all.includes(`${APEX}/categories/industrial-pumps`));
});

test('city and intent URLs use the apex domain', async () => {
  const all = await urls();
  assert.ok(all.includes(`${APEX}/products/abb-contactor/in/mumbai`));
  assert.ok(all.includes(`${APEX}/products/abb-contactor/price/in/mumbai`));
  assert.ok(all.includes(`${APEX}/products/abb-contactor/suppliers/in/mumbai`));
});

test('ineligible city pairs are excluded (Phase 1 eligibility intact)', async () => {
  const joined = (await urls()).join('\n');
  assert.ok(!joined.includes('delhi'), 'cityEligible=false pair leaked into sitemap');
  assert.ok(!joined.includes('never-eligible'), 'ineligible product leaked into sitemap');
});

test('empty product slugs produce no entries', async () => {
  const all = await urls();
  assert.ok(all.every((u) => !u.endsWith('/products/') && !u.includes('/products//')), 'empty slug emitted');
});

test('no duplicate URLs in the sitemap', async () => {
  const all = await urls();
  assert.equal(new Set(all).size, all.length, 'duplicate sitemap URLs');
});

// ---- F3: sitemap API failure behavior — no silent partial sitemap ----
// A network failure or a non-2xx backend response (the API returns 503 when
// the database is unavailable or eligibility overflows) must REJECT the
// sitemap promise, never silently return a static-only "successful" sitemap.
const withFailingFetch = async (impl, run) => {
  const original = globalThis.fetch;
  globalThis.fetch = impl;
  try {
    await run();
  } finally {
    globalThis.fetch = original;
  }
};

test('sitemap rejects when the products API is unreachable (network error)', async () => {
  await withFailingFetch(async () => {
    throw new Error('ECONNREFUSED');
  }, async () => {
    await assert.rejects(() => sitemap(), /\[sitemap\] sitemap-products fetch failed/);
  });
});

test('sitemap rejects when the products API responds 503', async () => {
  await withFailingFetch(async () => ({ ok: false, status: 503, json: async () => ({}) }), async () => {
    await assert.rejects(() => sitemap(), /\[sitemap\] sitemap-products API responded 503/);
  });
});

test('sitemap rejects when the categories API responds 503', async () => {
  await withFailingFetch(async (input) => {
    if (String(input).includes('/api/categories')) {
      return { ok: false, status: 503, json: async () => ({}) };
    }
    return { ok: true, json: async () => (apiData.get('/api/seo/sitemap-products')) };
  }, async () => {
    await assert.rejects(() => sitemap(), /\[sitemap\] categories API responded 503/);
  });
});

test('sitemap rejects when the city-pages API responds 503', async () => {
  await withFailingFetch(async (input) => {
    if (String(input).includes('/api/seo/sitemap-city-pages')) {
      return { ok: false, status: 503, json: async () => ({}) };
    }
    for (const [suffix, data] of apiData) {
      if (String(input).includes(suffix)) return { ok: true, json: async () => data };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  }, async () => {
    await assert.rejects(() => sitemap(), /\[sitemap\] sitemap-city-pages API responded 503/);
  });
});

// ---- Calculator canonical metadata (shared metadataBase) ----
// The root layout must pin metadataBase to the owner-approved apex origin so
// every RELATIVE canonical URL resolves against https://udyogconnect.in.
// Next.js otherwise falls back to VERCEL_URL or localhost:3000.
const CALCS = [
  'angle-weight-calculator',
  'beam-weight-calculator',
  'channel-weight-calculator',
  'hex-bar-weight-calculator',
  'pipe-weight-calculator',
  'plate-weight-calculator',
  'round-bar-weight-calculator',
  'steel-weight-calculator',
];

const rootMetadata = require(path.join(dist, 'app', 'layout.js')).metadata;
const calcPages = Object.fromEntries(
  CALCS.map((slug) => [
    slug,
    require(path.join(dist, 'app', 'tools', slug, 'page.js')).metadata,
  ]),
);

test('root layout pins metadataBase to the apex origin', () => {
  assert.ok(rootMetadata, 'root layout must export metadata');
  assert.ok(rootMetadata.metadataBase instanceof URL, 'metadataBase must be a URL');
  assert.equal(rootMetadata.metadataBase.origin, APEX);
});

test('all eight calculator pages declare a relative canonical', () => {
  for (const slug of CALCS) {
    const meta = calcPages[slug];
    assert.ok(meta, `metadata missing for ${slug}`);
    const canonical = meta?.alternates?.canonical;
    assert.ok(
      typeof canonical === 'string' && canonical.startsWith('/'),
      `canonical for ${slug} should stay relative: ${canonical}`,
    );
  }
});

test('all eight calculator canonicals resolve to the apex origin (no localhost/vercel/www/.com)', () => {
  const base = rootMetadata.metadataBase;
  for (const slug of CALCS) {
    const canonical = calcPages[slug].alternates.canonical;
    const resolved = new URL(canonical, base);
    assert.equal(resolved.origin, APEX, `${slug} canonical resolved to ${resolved.origin}`);
    assert.equal(resolved.pathname, `/tools/${slug}`, `${slug} canonical path mismatch`);
    const host = resolved.host;
    assert.ok(!host.startsWith('localhost'), `${slug} canonical hit localhost: ${host}`);
    assert.ok(!host.includes('vercel'), `${slug} canonical hit a Vercel hostname: ${host}`);
    assert.ok(!host.startsWith('www.'), `${slug} canonical hit the www domain: ${host}`);
    assert.ok(!host.endsWith('.com'), `${slug} canonical hit the wrong TLD: ${host}`);
  }
});

const og = rootMetadata.openGraph;
test('root layout openGraph URLs resolve against the apex origin', () => {
  if (og?.url !== undefined) {
    const resolved = new URL(String(og.url), rootMetadata.metadataBase);
    assert.equal(resolved.origin, APEX, `openGraph url resolved to ${resolved.origin}`);
  }
  if (og?.images !== undefined) {
    for (const image of [].concat(og.images)) {
      const src = typeof image === 'string' ? image : image?.url;
      if (src) {
        const resolved = new URL(String(src), rootMetadata.metadataBase);
        assert.equal(resolved.origin, APEX, `openGraph image resolved to ${resolved.origin}`);
      }
    }
  }
});

// ---- Batch 2: product & city canonical + og:url emission (stale-payload safety) ----
//
// Production evidence (2026-11-19): /products/<slug>/in/pune served a stale
// www canonical + og:url while the live backend payload already returned apex
// URLs — the Next fetch cache (`next: { revalidate: 3600 }`) kept serving a
// payload captured before the backend apex switch, and the emission point
// trusted the payload's absolute URL verbatim. These tests pin the emission
// guarantee: whatever origin the payload carries, canonical and og:url MUST
// be the apex origin, preserve the payload's path, and agree exactly.

const productLayout = require(path.join(dist, 'app', 'products', '[slug]', '(main)', 'layout.js'));
const cityPage = require(path.join(dist, 'app', 'products', '[slug]', 'in', '[city]', 'page.js'));
const intentCityPage = require(path.join(dist, 'app', 'products', '[slug]', '[intent]', 'in', '[city]', 'page.js'));
const { canonicalSelfUrl } = require(path.join(dist, 'lib', 'siteUrl.js'));

const SEO_PAYLOAD = (canonicalUrl) => ({
  productName: 'ABB Contactor',
  seoTitle: 'ABB Contactor Price in India (2026) | UdyogConnect',
  seoDescription: 'Compare verified ABB Contactor sellers.',
  canonicalUrl,
  categoryName: 'Contactors',
});

const withPayloads = async (payloads, run) => {
  const original = globalThis.fetch;
  globalThis.fetch = async (input) => {
    const url = String(input);
    for (const [suffix, payload] of Object.entries(payloads)) {
      if (url.includes(suffix)) {
        return { ok: true, json: async () => (typeof payload === 'function' ? payload(url) : payload) };
      }
    }
    return { ok: false, json: async () => ({}) };
  };
  try {
    await run();
  } finally {
    globalThis.fetch = original;
  }
};

const params = (o) => Promise.resolve(o);

test('canonicalSelfUrl re-anchors legacy www payload URLs on the apex origin', () => {
  assert.equal(canonicalSelfUrl('https://www.udyogconnect.in/products/abb-contactor', '/products/x'), `${APEX}/products/abb-contactor`);
  assert.equal(canonicalSelfUrl(`${APEX}/products/abb-contactor`, '/products/x'), `${APEX}/products/abb-contactor`);
  assert.equal(canonicalSelfUrl('/products/abb-contactor', '/products/x'), `${APEX}/products/abb-contactor`);
  assert.equal(canonicalSelfUrl(undefined, '/products/abb-contactor'), `${APEX}/products/abb-contactor`);
  assert.equal(canonicalSelfUrl(null, '/products/abb-contactor/in/pune'), `${APEX}/products/abb-contactor/in/pune`);
  assert.equal(canonicalSelfUrl('', '/products/x'), `${APEX}/products/x`);
  assert.equal(canonicalSelfUrl('https://example.com/products/abb-contactor', '/products/x'), `${APEX}/products/x`);
  assert.equal(canonicalSelfUrl('//www.udyogconnect.in/products/x', '/products/x'), `${APEX}/products/x`);
});

test('product canonical + og:url re-anchor a stale www payload on the apex origin', async () => {
  await withPayloads({
    '/api/products/abb-contactor/seo': SEO_PAYLOAD('https://www.udyogconnect.in/products/abb-contactor'),
  }, async () => {
    const meta = await productLayout.generateMetadata({ params: params({ slug: 'abb-contactor' }) });
    assert.equal(meta.alternates.canonical, `${APEX}/products/abb-contactor`);
    assert.equal(meta.openGraph.url, meta.alternates.canonical);
    assert.ok(!JSON.stringify(meta).includes('www.udyogconnect'));
  });
});

test('product canonical + og:url keep an apex payload unchanged (path preserved)', async () => {
  await withPayloads({
    '/api/products/abb-contactor/seo': SEO_PAYLOAD(`${APEX}/products/abb-contactor`),
  }, async () => {
    const meta = await productLayout.generateMetadata({ params: params({ slug: 'abb-contactor' }) });
    assert.equal(meta.alternates.canonical, `${APEX}/products/abb-contactor`);
    assert.equal(meta.openGraph.url, meta.alternates.canonical);
  });
});

test('product canonical falls back to the apex route path when the payload omits canonicalUrl', async () => {
  await withPayloads({
    '/api/products/abb-contactor/seo': SEO_PAYLOAD(undefined),
  }, async () => {
    const meta = await productLayout.generateMetadata({ params: params({ slug: 'abb-contactor' }) });
    assert.equal(meta.alternates.canonical, `${APEX}/products/abb-contactor`);
    assert.equal(meta.openGraph.url, meta.alternates.canonical);
  });
});

const CITY_PAYLOAD = (pageUrl) => ({
  product: { name: 'ABB Contactor', slug: 'abb-contactor' },
  city: { name: 'Mumbai', slug: 'mumbai' },
  seo: { title: 'ABB Contactor in Mumbai | UdyogConnect', description: 'd', pageUrl },
});

test('city page canonical + og:url re-anchor a stale www payload on the apex origin', async () => {
  await withPayloads({
    '/api/products/abb-contactor/city/mumbai': CITY_PAYLOAD('https://www.udyogconnect.in/products/abb-contactor/in/mumbai'),
  }, async () => {
    const meta = await cityPage.generateMetadata({ params: params({ slug: 'abb-contactor', city: 'mumbai' }) });
    assert.equal(meta.alternates.canonical, `${APEX}/products/abb-contactor/in/mumbai`);
    assert.equal(meta.openGraph.url, meta.alternates.canonical);
    assert.ok(!JSON.stringify(meta).includes('www.udyogconnect'));
  });
});

test('city page canonical falls back to the apex route path when the payload omits pageUrl', async () => {
  await withPayloads({
    '/api/products/abb-contactor/city/mumbai': { product: { name: 'ABB Contactor' }, city: { name: 'Mumbai' }, seo: { title: 't' } },
  }, async () => {
    const meta = await cityPage.generateMetadata({ params: params({ slug: 'abb-contactor', city: 'mumbai' }) });
    assert.equal(meta.alternates.canonical, `${APEX}/products/abb-contactor/in/mumbai`);
    assert.equal(meta.openGraph.url, meta.alternates.canonical);
  });
});

test('intent+city canonical + og:url re-anchor a stale www payload on the apex origin', async () => {
  await withPayloads({
    '/api/products/abb-contactor/city/mumbai': (url) => ({
      product: { name: 'ABB Contactor', slug: 'abb-contactor' },
      city: { name: 'Mumbai', slug: 'mumbai' },
      seo: {
        title: 't',
        description: 'd',
        pageUrl: url.includes('intent=price')
          ? 'https://www.udyogconnect.in/products/abb-contactor/price/in/mumbai'
          : 'https://www.udyogconnect.in/products/abb-contactor/in/mumbai',
      },
    }),
  }, async () => {
    const meta = await intentCityPage.generateMetadata({ params: params({ slug: 'abb-contactor', intent: 'price', city: 'mumbai' }) });
    assert.equal(meta.alternates.canonical, `${APEX}/products/abb-contactor/price/in/mumbai`);
    assert.equal(meta.openGraph.url, meta.alternates.canonical);
    assert.ok(!JSON.stringify(meta).includes('www.udyogconnect'));
  });
});

test('emission modules route canonical/og:url through canonicalSelfUrl (source-level guard)', () => {
  for (const rel of [
    'src/app/products/[slug]/(main)/layout.tsx',
    'src/app/products/[slug]/in/[city]/page.tsx',
    'src/app/products/[slug]/[intent]/in/[city]/page.tsx',
  ]) {
    const src = fs.readFileSync(path.join(here, '..', '..', rel), 'utf8');
    assert.ok(src.includes('canonicalSelfUrl('), `emission must normalize via canonicalSelfUrl: ${rel}`);
    assert.ok(!src.includes('canonical: seoData.canonicalUrl'), `raw payload canonical emitted: ${rel}`);
    assert.ok(!src.includes('const pageUrl = data.seo?.pageUrl'), `raw payload page URL emitted: ${rel}`);
  }
});
