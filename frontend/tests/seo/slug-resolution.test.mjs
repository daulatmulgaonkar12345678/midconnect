// Batch 5 (2026-11-19) invalid-product-slug resolution tests (node:test).
//
// Backend contract: the slug resolver is deterministic (exact slug,
// case-normalized slug, ObjectId, explicit legacySlugs/legacyIds); anything
// else is answered with HTTP 404 and must NOT fall back to fuzzy/ANY-token
// matching that surfaced unrelated products.
//
// Frontend contract: a definitive backend 404 renders the HTTP 404 boundary
// on /products/{slug} (previously a 200 "Loading product…" soft-404 shell);
// legacy ObjectId URLs keep the 200 client-redirect path, and transient
// backend failures keep the 200 fallback.
//
// Behavioral tests exercise the REAL compiled helper
// (dist/lib/productSeoServer.js) through tsc -p tests/seo/tsconfig.seo.json;
// page/layout semantics are pinned structurally (page.tsx is a Next.js
// server component and is not compiled by this harness).
import test from 'node:test';
import assert from 'node:assert/strict';
import Module from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, 'dist');
const src = path.join(here, '..', '..', 'src');
const require = createRequire(import.meta.url);

const stub = (name) => path.join(here, 'stubs', name);
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (request.startsWith('@/')) {
    return originalResolve.call(this, path.join(dist, request.slice(2)), ...rest);
  }
  return originalResolve.call(this, request, ...rest);
};

process.env.REACT_APP_BACKEND_URL = 'http://127.0.0.1:3999';

const { fetchProductSeoPayload } = require(path.join(dist, 'lib', 'productSeoServer.js'));

const SLUG = 'vfd-vfd-plc-hmi-control-equipments-supplier-india';
const FIXTURE = { productName: 'VFD', seoTitle: 'Compare VFD Prices in India (2026) | UdyogConnect' };

async function withFetch(stub, fn) {
  const original = globalThis.fetch;
  globalThis.fetch = stub;
  try {
    return await fn();
  } finally {
    globalThis.fetch = original;
  }
}

// ---------- helper: definitive 404 vs transient failure ----------

test('valid canonical slug resolves the payload (notFound false)', async () => {
  const result = await withFetch(
    (url) => {
      assert.equal(String(url), `http://127.0.0.1:3999/api/products/${SLUG}/seo`);
      return { ok: true, status: 200, json: async () => FIXTURE };
    },
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(result.notFound, false);
  assert.equal(result.payload.productName, 'VFD');
});

test('unknown slug (backend 404) is definitively not found', async () => {
  const result = await withFetch(
    () => ({ ok: false, status: 404, json: async () => ({ detail: 'Product not found' }) }),
    () => fetchProductSeoPayload('this-is-not-a-product'),
  );
  assert.equal(result.payload, null);
  assert.equal(result.notFound, true);
});

test('backend outage/5xx stays transient (page must not 404 on infra failure)', async () => {
  const result = await withFetch(
    () => ({ ok: false, status: 500, json: async () => ({}) }),
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(result.notFound, false);
  assert.equal(result.payload, null);
});

test('network failure stays transient', async () => {
  const result = await withFetch(
    () => { throw new Error('backend down'); },
    () => fetchProductSeoPayload(SLUG),
  );
  assert.equal(result.notFound, false);
});

test('legacy ObjectId URL keeps the 200 client-redirect path (no API call, not a 404)', async () => {
  let calls = 0;
  const result = await withFetch(
    () => { calls += 1; return { ok: true, json: async () => FIXTURE }; },
    () => fetchProductSeoPayload('6a44cd478b430643bfad1873'),
  );
  assert.equal(calls, 0);
  assert.equal(result.payload, null);
  assert.equal(result.notFound, false);
});

// ---------- structural: the 404 boundary is owned by the page shell ----------

const pageSrc = readFileSync(path.join(src, 'app', 'products', '[slug]', '(main)', 'page.tsx'), 'utf8');
const layoutSrc = readFileSync(path.join(src, 'app', 'products', '[slug]', '(main)', 'layout.tsx'), 'utf8');
const helperSrc = readFileSync(path.join(src, 'lib', 'productSeoServer.ts'), 'utf8');

test('page shell renders the 404 boundary only on a definitive backend 404', () => {
  assert.match(pageSrc, /import \{ notFound \} from 'next\/navigation';/);
  assert.match(pageSrc, /notFound: slugNotResolved/);
  assert.match(pageSrc, /if \(slugNotResolved\) notFound\(\);/);
  // hero + client island rendering preserved
  assert.match(pageSrc, /payload && <ProductSeoHero payload=\{payload\} \/>/);
  assert.match(pageSrc, /<ProductPageClient \/>/);
});

test('layout reads .payload and does not own the 404 decision', () => {
  assert.match(layoutSrc, /\(await fetchProductSeoPayload\(slug\)\)\.payload/);
  assert.doesNotMatch(layoutSrc, /notFound\(/);
  // Batch 2 canonical normalization untouched
  assert.match(layoutSrc, /canonicalSelfUrl\(seoData\.canonicalUrl, `\/products\/\$\{slug\}`\)/);
});

test('helper maps exactly the 404 status to notFound (all other failures transient)', () => {
  assert.match(helperSrc, /if \(response\.status === 404\) return \{ payload: null, notFound: true \};/);
  assert.match(helperSrc, /if \(isObjectId\(slug\)\) return \{ payload: null, notFound: false \};/);
  assert.match(helperSrc, /if \(!response\.ok\) return \{ payload: null, notFound: false \};/);
});
