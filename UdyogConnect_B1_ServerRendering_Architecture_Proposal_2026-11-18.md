# UdyogConnect — B1: Server-Rendered Product Pages
## Architecture & Data-Flow Proposal (for owner review — no code changed in this proposal)

**Date:** 2026-11-18
**Status:** PROPOSAL — awaiting owner review. Nothing in this document has been implemented.
**Source of truth:** `UdyogConnect_Product_SEO_Audit_2026-11-18.md` (B1 finding)
**Scope guard:** routes, redirects, APIs, seller permissions and pricing-visibility rules are NOT changed.

---

## 1. Current state (verified in source)

| Surface | File | Rendering |
|---|---|---|
| Product page | `frontend/src/app/products/[slug]/(main)/page.tsx` | `'use client'` — entire page renders in the browser; data fetched client-side |
| Layout / metadata | `frontend/src/app/products/[slug]/(main)/layout.tsx` | Server component; generates `<title>`/meta/JSON-LD via `ProductSEO.tsx` |
| SEO content | `backend/server.py` → `GET /api/products/{id}/seo` | Public, DB-backed payload: `seoTitle`, `seoDescription`, `seoContent`, `jsonLd`, `breadcrumbJsonLd`, `faqJsonLd`, `internalLinks`, `sellersByCity`, `minPrice/maxPrice/minMoq`, `availableCities`, `canonicalUrl` |
| Enterprise data | `getEnterpriseProduct`, `getProductFacets` (`frontend/src/lib/api.ts`) | Client-side, auth-aware, pricing-visibility enforced by backend |
| Enterprise UI parts | `frontend/src/components/enterprise/` (`SellerCard`, `InquiryModal`, `FilterPanel`, `ComparisonTable`, `IdentityBlock`, `EmptyState`, `FloatingCompareBar`, `MobileFilterDrawer`) | Client components mounted inside the client page |

**SEO consequence (audit B1):** the first HTML byte stream contains no H1, no product
introduction, no price, no supplier count, no specs and no images. Everything the
ranking systems and crawlers see at first paint is metadata only. Google does render
JS, but delayed/failed hydration, Core-Web-Vitals cost and partial rendering put
UdyogConnect behind competitors (IndiaMART, Moglix, TradeIndia) whose product pages
are fully server-rendered.

---

## 2. Target architecture: server-first shell + preserved client island

Keep the URL, the route, the file locations and every interactive behavior. Convert
**only** the page entry from a client component into a **server component shell**
that renders the SEO-critical section and mounts the existing interactive page as a
client island below it.

```
frontend/src/app/products/[slug]/(main)/page.tsx   ← becomes server component (RSC)
├── fetchProductSeoPayload(slug)                   ← new server-only helper
│     GET {API}/api/products/{slug}/seo  (next: { revalidate: 3600 })
├── <ProductSeoHero payload={...} />               ← NEW server-rendered section (RSC, zero JS)
│     H1 + product title
│     unique product introduction (B5 description / seoContent lead)
│     verified price range  (payload.minPrice–maxPrice, "from ₹X" only when priced)
│     verified supplier count (payload.sellerCount, only when > 0 — B4 rule)
│     seller listing info    (payload.sellersByCity — public fields only)
│     technical specifications (payload.specifications, when available)
│     product images + alt   (payload images, alt = "{Product Name} — {index}")
│     FAQ (visible Q&A)       (payload.faqJsonLd.mainEntity — visible = marked-up)
│     Enquiry CTA             (anchor to the existing client enquiry island)
├── <ProductPageClient slug={slug} />              ← EXISTING page, moved to a new file
│     'use client'; unchanged internals: getEnterpriseProduct, facets,
│     filters, InquiryModal, SellerCard, calculators, auth context
└── ProductSEO.tsx JSON-LD stays in layout (already server-rendered)
```

### 2.1 New files (total new code ≈ 250–350 lines)

1. `frontend/src/lib/productSeoServer.ts` — *(proposed file — does not exist yet)* server-only payload fetch + narrow
   TypeScript mapping (mirrors `cityPageRenderer.fetchCityData` pattern already in
   the codebase: plain `fetch`, `next: { revalidate: 3600 }`, `null` on failure).
2. `frontend/src/components/product/ProductSeoHero.tsx` — *(proposed file — does not exist yet)* the RSC hero section.
   No `'use client'`, no hooks, no event handlers → ships **zero JavaScript**.
3. `frontend/src/app/products/[slug]/(main)/ProductPageClient.tsx` — *(proposed file — does not exist yet)* the current
   `page.tsx` body moved verbatim (rename only; no logic edits).
4. Rewritten `page.tsx` (≈ 30 lines): `fetch` payload → `<ProductSeoHero/>` →
   `<ProductPageClient/>`; `notFound()` when the payload says the product does not
   exist (matches B4 semantics); graceful client-only fallback when the payload is
   unavailable (render current behavior — never block the page).

### 2.2 Why this shape is safe

- **Route contract unchanged:** `/products/[slug]` stays; the legacy singular
  `/product/[slug]` redirect is untouched; canonical stays `/products/{slug}`.
- **No API changes:** the hero consumes the *existing* public `/seo` endpoint —
  the same payload the frontend already requests and the same data Googlebot
  already receives. Zero new backend surface.
- **Permissions & pricing visibility preserved:** the hero renders only fields the
  public `/seo` endpoint already exposes to anonymous visitors (companyName, city,
  badgeType, lowestPrice). Seller contact details, full price tiers, MOQ breaks and
  admin data remain behind the existing auth-aware client calls — the server shell
  never sees or renders them. **No private seller information can leak** because
  the RSC renders exactly the public payload subset.
- **Interactivity preserved:** every event handler, filter, modal, calculator and
  comparison bar lives in the unchanged client island.
- **Reversible:** the change is 4 files in one directory; reverting restores the
  current page byte-for-byte.

---

## 3. Data flow (end-to-end)

```
Browser/Googlebot  ──GET /products/{slug}──▶  Next.js server (RSC)
                                                │
                                                ├─ (server) GET /api/products/{slug}/seo
                                                │     revalidate 3600 — cached at the edge,
                                                │     one upstream call/hour/slug
                                                │     payload: name, seoTitle, seoDescription,
                                                │     seoContent, sellerCount, min/maxPrice,
                                                │     sellersByCity, specifications,
                                                │     images (ld_images), faqJsonLd,
                                                │     internalLinks, canonicalUrl
                                                │
                                                ├─ render <ProductSeoHero> (static HTML)
                                                └─ stream <ProductPageClient> island
                                                      │  (browser only)
                                                      ├─ getEnterpriseProduct(slug)   — auth-aware
                                                      ├─ getProductFacets(...)        — auth-aware
                                                      ├─ /redirect/product/{id}       — canonical id
                                                      └─ calculators, InquiryModal, filters
```

Content-freshness guarantee: the `/seo` endpoint returns data regenerated by
`seo_service` (SEO_VERSION v8). When sellers/prices change, the backend payload
changes; the 1-hour ISR window is the only staleness bound — identical to the
city pages and the sitemap lastmod discipline.

## 4. Section-by-section content rules (anti-fabrication, matches B4/B5 rules)

| Hero element | Source | Rule |
|---|---|---|
| H1 | `seoTitle` → falls back to `{name} — Price, Suppliers & Specs` | exactly one H1 per page |
| Introduction | `usable_stored_description()` or B5 seed via `generate_product_description()` | never invents manufacturer/model/specs/certifications |
| Price range | `minPrice–maxPrice` | rendered only when numeric; otherwise "Request quote" — never a fabricated number |
| Supplier count | `sellerCount` | chip only when > 0 (same rule as city pages) |
| Seller listings | `sellersByCity` (companyName, city, badgeType) | public fields only; "top N by listing count", max 6 shown |
| Specifications | `specifications` / `normalizedSpecs` | rendered only when non-empty; raw passthrough, no synthesis |
| Images | product/seller images from payload | `alt="{Product name} — {variant/index}"`, `loading` via `width/height` attrs |
| FAQ | `faqJsonLd.mainEntity` | visible Q&A rendered from the same JSON — markup always equals visible content |
| Enquiry CTA | anchor `#enquire` | scrolls to the existing client `InquiryModal` trigger; no duplicated enquiry logic |

## 5. Test plan (defined now, executed at implementation time)

1. **RSC render tests (vitest + jsdom, pattern of `frontend/tests/seo`):**
   hero renders H1/intro/price/supplier-count/FAQ from a fixture payload;
   renders NO price chip when `minPrice` null; NO supplier chip when count 0;
   FAQ visible text equals `faqJsonLd` text; alt attributes present on images.
2. **Contract test:** `ProductSeoHero` props type vs actual live `/seo` payload
   (snapshot of 3 representative products: priced multi-seller, unpriced,
   single-seller).
3. **Fallback test:** payload fetch failure → client island still renders
   (current behavior), page does not 500.
4. **Frontend typecheck + `test:seo`** green; backend regression untouched
   (no backend change required by B1).
5. **Manual smoke:** enquiry modal opens; filters/calculators function; seller
   cards identical to current; auth-gated sections unchanged for anonymous
   vs seller vs admin sessions.

## 6. Rollout order (smallest safe increments)

1. Land `productSeoServer.ts` + `ProductSeoHero.tsx` with tests (no route change).
2. Move `page.tsx` → `ProductPageClient.tsx` (pure rename; typecheck proof).
3. Rewrite 30-line `page.tsx` shell; keep client-only fallback flag `NEXT_PUBLIC_SEO_HERO=off`
   as a kill-switch rendered at build time.
4. Verify with built output (`next build` + view-source check: H1 present in HTML
   without JS), Lighthouse before/after, then remove flag.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Payload contract drift breaks hero | mapped types + contract test against live payload; hero degrades to client-only fallback on any error |
| Duplicate H1/content between hero and client island | client island's own H1/SEO text block is removed in the same PR (single source) |
| ISR serving stale price after seller edits | 1-hour bound, same as city pages; backend `SEO_VERSION` bump forces regeneration on deploy |
| Hydration mismatch between RSC hero and client island | hero and island render disjoint DOM sections; no shared state |
| Googlebot double-render cost | hero is zero-JS; island hydrates below the fold as today |

## 8. Explicitly out of scope (unchanged)

- Frontend routes, `next.config.ts` redirects, middleware, sitemap, robots.
- Backend APIs, schemas, permissions, pricing-visibility rules.
- Legacy `/product/[slug]` → `/products/[slug]` redirect behavior.
- Enterprise components' internals (only their mount point moves).

---

**Decision requested from owner:** approve the server-shell + client-island design
and the 4-file rollout order above. On approval, implementation lands in the next
round with the test plan in §5 executed before delivery.
