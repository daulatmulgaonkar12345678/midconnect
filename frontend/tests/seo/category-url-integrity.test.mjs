// Batch 6 (2026-11-20) category URL integrity tests (node:test).
//
// Final remediation round (owner corrections 1-7):
// - /category/{id} legacy route: permanentRedirect() (308) and notFound() are
//   NEVER executed inside a try/catch (they abort rendering by throwing — a
//   catch block would swallow them), and every fallback API response is
//   validated (HTTP ok) BEFORE it is parsed as JSON (corrections 4 & 5).
// - /categories/{slug}: slug matching is case-normalized and noncanonical
//   casing is permanently redirected to the canonical slug (correction 6);
//   unresolved addresses still answer a real 404 (notFound()).
// - Sitemap: category entries use ONLY persisted canonical slugs; no
//   independent name-slugify fallback exists anymore (correction 7). The old
//   sitemap fallback test asserted the fallback — it is replaced here.
// - generateStaticParams keeps dynamicParams enabled (owner revision 5).
//
// These are Next.js server components not compiled by the seo tsc harness, so
// — like the page/layout pins in slug-resolution.test.mjs — the semantics are
// pinned structurally against the real source files.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', '..', 'src');
const backend = path.join(here, '..', '..', '..', 'backend');

const read = (rel) => readFileSync(path.join(src, rel), 'utf8');

// ---------------- legacy /category/{id} route ----------------

test('legacy category route uses permanentRedirect (308), not 302/301 redirect()', () => {
  const page = read('app/category/[id]/page.tsx');
  assert.match(page, /permanentRedirect\(/, 'must call permanentRedirect (308)');
  assert.doesNotMatch(
    page.replace(/permanentRedirect\([^)]*\)/g, ''),
    /\bredirect\(/,
    'no temporary redirect() may remain on the legacy route'
  );
});

test('correction 4: redirect/notFound are never executed inside a try/catch', () => {
  const page = read('app/category/[id]/page.tsx');
  // All fallible I/O lives in a helper that returns null on failure...
  assert.match(page, /async function fetchJsonOrNull/, 'lookups are isolated in a null-returning helper');
  const component = page.slice(page.indexOf('export default async function CategoryRedirectPage'));
  assert.ok(component.includes('CategoryRedirectPage'), 'page component found');
  assert.doesNotMatch(
    component,
    /try\s*\{/,
    'the component body must contain no try/catch that could swallow a redirect throw'
  );
  // ...and the redirect/notFound calls sit in that component body.
  assert.match(component, /permanentRedirect\(/);
  assert.match(component, /notFound\(\)/);
});

test('correction 5: fallback API responses are validated before JSON parsing', () => {
  const page = read('app/category/[id]/page.tsx');
  const okIdx = page.indexOf('if (!response.ok)');
  const jsonIdx = page.indexOf('response.json()');
  assert.ok(okIdx !== -1, 'HTTP status must be validated');
  assert.ok(jsonIdx !== -1, 'JSON parsing must happen');
  assert.ok(okIdx < jsonIdx, 'response.ok must be checked BEFORE response.json()');
  assert.match(
    page,
    /if \(!response\.ok\)\s*\{\s*return null;/,
    'non-2xx responses yield null instead of being parsed'
  );
});

test('legacy category route 404s instead of forwarding unresolved ids', () => {
  const page = read('app/category/[id]/page.tsx');
  assert.match(page, /notFound\(\)/, 'unresolved category must 404');
  assert.doesNotMatch(
    page,
    /redirect\(`\/categories\/\$\{id\}`\)/,
    'must never forward the unresolved identifier to /categories/{id}'
  );
});

test('legacy category route never redirects to a null slug target', () => {
  const page = read('app/category/[id]/page.tsx');
  // Only redirect on a concrete slug (resolver: category.slug; mapping API: slug).
  assert.match(page, /resolverData\?\.category\?\.slug/);
  assert.match(page, /mappingData\?\.redirect === true && mappingData\.slug/);
});

// ---------------- canonical /categories/{slug} route ----------------

test('category page answers notFound() when unresolved (no soft-404)', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(page, /if \(!category\) \{\s*notFound\(\);/, 'unresolved category must call notFound()');
  assert.doesNotMatch(
    page,
    /Category Not Found/,
    'the HTTP-200 "Category Not Found" soft-404 render must be gone'
  );
});

test('generateStaticParams keeps dynamicParams enabled for post-deploy categories', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(page, /export async function generateStaticParams\(\)/);
  assert.doesNotMatch(
    page,
    /dynamicParams\s*=\s*false/,
    'dynamicParams=false would 404 newly added categories after deployment (revision 5)'
  );
  assert.doesNotMatch(
    page,
    /dynamicParams\s*=\s*true\s*;\s*[^]*?export async function generateStaticParams/,
  );
});

test('correction 6: slug matching is case-normalized (noncanonical casing resolves)', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(page, /const normalizedSlug = slug\.toLowerCase\(\);/);
  assert.match(
    page,
    /\(c\.slug \|\| ''\)\.toLowerCase\(\) === normalizedSlug/,
    'the slug lookup must be case-insensitive'
  );
});

test('correction 6: noncanonical casing permanently redirects to the canonical slug', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(
    page,
    /if \(category\?\.slug && category\.slug !== slug\)\s*\{\s*redirectTarget = category\.slug;/,
    'a resolved slug that differs from the requested spelling becomes a redirect target'
  );
  assert.match(
    page,
    /permanentRedirect\(`\/categories\/\$\{redirectTarget\}`\)/,
    'canonicalizing redirect is a 308 permanentRedirect'
  );
});

test('correction 4: canonicalizing redirects execute outside any try/catch', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(page, /let redirectTarget: string \| null = null;/, 'redirect targets are resolved into a variable, never thrown from inside try');
  const redirectSite = page.indexOf('if (redirectTarget) {');
  assert.ok(redirectSite !== -1, 'single canonicalizing redirect site exists');
  const before = page.slice(0, redirectSite);
  const opens = (before.match(/\btry\s*\{/g) || []).length;
  const closes = (before.match(/\}\s*catch/g) || []).length;
  assert.equal(opens, closes, 'every try/catch is closed BEFORE the redirect executes');
});

test('ObjectId URLs still redirect to the canonical slug path', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(page, /isObjectId\(slug\)/, 'ObjectId legacy addresses must stay supported');
  assert.match(
    page,
    /if \(resolverData\.category\?\.slug && resolverData\.category\.slug !== slug\)\s*\{\s*redirectTarget = resolverData\.category\.slug;/,
    'redirect only on a canonical slug that DIFFERS from the requested slug'
  );
});

// ---------------- final review correction 1: no canonical self-redirect loop ----------------

test('final review 1: resolver hit whose canonical slug equals the request does NOT redirect (no self-redirect loop)', () => {
  const page = read('app/categories/[slug]/page.tsx');
  // The resolver branch must guard on difference, like the slug branch does.
  assert.match(
    page,
    /if \(resolverData\.category\?\.slug && resolverData\.category\.slug !== slug\)/,
    'resolver redirect must fire only when the canonical slug differs from the requested slug'
  );
  assert.doesNotMatch(
    page,
    /if \(resolverData\.category\?\.slug\)\s*\{\s*redirectTarget/,
    'no unguarded resolver redirect may remain — it would 308 /categories/{slug} to its own address forever'
  );
});

test('final review 1: resolver hit on a legacy ObjectId identifier redirects to the canonical slug', () => {
  const page = read('app/categories/[slug]/page.tsx');
  const component = page.slice(
    page.indexOf('let redirectTarget: string | null = null;'),
    page.indexOf('if (redirectTarget) {')
  );
  assert.match(component, /if \(isObjectId\(slug\)\)/, 'the legacy ObjectId branch is exercised');
  assert.match(
    component,
    /redirectTarget = resolverData\.category\.slug;/,
    'a legacy ObjectId resolved through the resolver becomes a redirect to the canonical slug'
  );
  assert.match(
    page,
    /permanentRedirect\(`\/categories\/\$\{redirectTarget\}`\)/,
    'the canonicalizing redirect is a 308 permanentRedirect'
  );
});

test('final review 1: case-variant slug redirects to the lowercase canonical slug', () => {
  const page = read('app/categories/[slug]/page.tsx');
  assert.match(page, /const normalizedSlug = slug\.toLowerCase\(\);/, 'the requested slug is case-normalized');
  const slugBranch = page.slice(
    page.indexOf('const normalizedSlug'),
    page.indexOf('// Corrections 4 & 6')
  );
  assert.match(
    slugBranch,
    /\(c\.slug \|\| ''\)\.toLowerCase\(\) === normalizedSlug/,
    'a case-variant of the canonical slug still resolves'
  );
  assert.match(
    slugBranch,
    /if \(category\?\.slug && category\.slug !== slug\)\s*\{\s*redirectTarget = category\.slug;/,
    'noncanonical casing redirects to the STORED canonical (lowercase) slug, never to the requested spelling'
  );
});

// ---------------- sitemap: persisted canonical slugs only (correction 7) ----------------

test('correction 7: sitemap emits persisted canonical slugs only (no name fallback)', () => {
  const sitemap = read('app/sitemap.ts');
  assert.match(sitemap, /categoriesWithSlugs = categories\.filter/, 'categories are filtered to slug-bearing docs');
  assert.match(
    sitemap,
    /typeof category\.slug === 'string' && category\.slug\.length > 0/,
    'only non-empty persisted slugs are emitted'
  );
  assert.doesNotMatch(sitemap, /slugify/, 'no independent slug generation may remain in the sitemap');
  assert.match(sitemap, /categories\/\$\{category\.slug\}/, 'URLs are built only from the persisted slug');
  assert.match(
    sitemap,
    /have no persisted slug and were omitted/,
    'categories without a persisted slug are omitted and reported'
  );
});

test('correction 7: V20 persists the slugs the sitemap relies on (no sitemap-side generation)', () => {
  const migration = readFileSync(
    path.join(backend, 'migrations', 'V20_backfill_category_slugs.py'),
    'utf8'
  );
  assert.match(migration, /def build_slug_plan/, 'V20 scans the complete collection');
  assert.match(
    migration,
    /"\$set": \{"slug": item\["slug"\]\}/,
    'V20 persists the deterministic slug per category'
  );
});
