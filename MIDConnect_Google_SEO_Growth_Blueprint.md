# MIDConnect — Google SEO Growth Blueprint (UdyogConnect / udyogconnect.in)

**Status of this document:** Audit and plan only. No source code was modified in this audit.
**Baseline re-verified 2026-11-17:** branch `main`, HEAD `55507a1`. Working tree = exactly 3 modified tracked files (`backend/server.py`, `frontend/package.json`, `frontend/src/app/sitemap.ts`) plus untracked `.exvisit/`, this blueprint, `backend/services/city_eligibility_service.py`, `backend/services/sitemap_product_service.py`, `backend/tests/phase1_db_guard.py`, `backend/tests/regression/` (4 test files). Full reconciliation in §14.1. Nothing committed, pushed, merged or deployed by this audit.
**Independent acceptance: NOT CERTIFIED.** Every finding below is labeled **Verified** (read from the repository), **External estimate** (from public web snippets; not measured on MIDConnect data), or **NOT VERIFIED / NOT RUN / BLOCKED**.

Legend used throughout: **[V]** verified from files · **[E]** external estimate · **[N/R]** not run · **[N/V]** not verified · **[B]** blocked.

**Document provenance (citation audit, 2026-11-17):** every backticked repository path in this document was re-resolved strictly from the repository root and every cited line number re-checked against the cited file (strict and loose resolvers: exit 0). Four inaccurate references were found and corrected the same day: the categories-hub redirect cite (that page contains no redirect calls — an earlier session cite of lines 121,137 was wrong), two `frontend/src/components/ProductSEO.tsx` line ranges (client refetch → :49–56; Organization schema → :69–86, rendered at :112), imprecise grep claims (`metadataBase`, WebSite node), and the `www.`-hardcoding file count (~14 → 19 measured source files: 7 in `frontend/src`, 6 in backend non-test, 6 in `backend/tests`). Corrections were confined to this document; no finding was removed to satisfy any check.

**Verification log (2026-11-17, final revision):** citation resolver over this revision — exit 0 (`CITATION_RESOLVER_PASS`); `npm --prefix frontend run typecheck` — PASS, exit 0; `run_checks kind auto` — no dead-end/stub/citation findings reported (root `python -m pytest` collection failure in 8 pre-existing legacy live scripts is documented in §13 and ruled out of scope by the owner).

---

## 1. Executive summary

MIDConnect already has a stronger SEO skeleton than a typical early-stage B2B marketplace: SSR category detail pages, SSR city and intent pages with backend-driven eligibility and noindex fallbacks, per-product JSON-LD (Product, Breadcrumb, FAQ), a filtered sitemap pipeline (Phase 1 work, uncommitted), 10 SSR calculator pages, and legacy-URL redirects. The two structural gaps that matter most are: **(a)** the product page body and the categories listing page are client-rendered, so crawlers see loading shells on the two highest-value templates; **(b)** the marketplace has essentially no indexable supplier/manufacturer entity pages, which is where IndiaMART's dominance comes from. A third gap, measured during this audit: production answers the apex domain with a temporary 307 redirect to `www`, while the owner-approved canonical is the apex (§3.1).

The realistic strategy is therefore: finish server-rendering the commercial templates, put every indexable page on a strict data-backed eligibility gate (the Phase 1 sitemap work already implements this), then build the supplier/manufacturer layer only as fast as genuine seller data supports it. Do not chase IndiaMART's long tail; compete on a narrower, genuinely supplied set of product × city × price pages plus differentiated technical content (calculators, spec explainers).

No ranking outcomes are guaranteed. Success is measured through Search Console impressions/clicks, indexed-eligible-page counts, and organic enquiry/registration events.

## 2. Current SEO health assessment

| Area | Status | Basis |
|---|---|---|
| robots.txt | **[V] PASS with canonical-host caveat** | `frontend/src/app/robots.ts`: allows `/`, disallows `/api/`, `/admin/`, `/seller/`, `/dashboard/`, `/login`, `/register`, `/verify-email`, `/cart/`; references `https://www.udyogconnect.in/sitemap.xml` — **`www` conflicts with the owner-approved apex canonical** (T14, §3.1) |
| Sitemap | **[V] PASS with caveats** | `frontend/src/app/sitemap.ts`: product URLs from `/api/seo/sitemap-products` (visible-products service, uncommitted); city URLs only when `cityEligible === true`; `price`/`suppliers` intent URLs only when their flags are strictly `true`; missing flags never eligible; capped at 45,000. Caveats: category URLs may 404 (§4-T2), silent `slice(0, MAX_URLS)` cap |
| Canonical URLs | **[V] PARTIAL** | Product/category/city/intent pages emit backend-driven canonicals. **No `metadataBase` anywhere** (grep -rl 'metadataBase' `frontend/src` → 0 files, verified 2026-11-17) and the root layout has no canonical → home/OG resolution depends on defaults. Emitted URLs hardcode `www.` (`frontend/src/app/sitemap.ts:3` `SITE_URL`, `frontend/src/app/robots.ts:21`, plus 5 more files in `frontend/src` — 7 there, 19 across the tree) — must move to the approved apex (T14) |
| Titles & descriptions | **[V] PARTIAL** | Product/category/city metadata is generated from backend SEO fields. Fallback metadata is generic and indexable (`frontend/src/app/products/[slug]/(main)/layout.tsx:98–105` `getDefaultMetadata`, `robots: index:true`) → thin pages can be indexed |
| SSR of main content | **[V] FAIL on two templates** | `frontend/src/app/categories/page.tsx:1` `'use client'` + `useEffect` fetch; `frontend/src/app/products/[slug]/(main)/page.tsx:1` `'use client'` (full 1,676-line client component). Category detail, city, intent pages are SSR **[V]** |
| Structured data | **[V] PARTIAL** | Product/Breadcrumb/FAQ JSON-LD SSR via `frontend/src/app/products/[slug]/(main)/layout.tsx:32–60,121–141`; Organization schema is static and **duplicated** (also rendered client-side by `frontend/src/components/ProductSEO.tsx:69–86`, render site :112, and per product layout). **No `'@type': 'WebSite'` node anywhere in `frontend/src`** (grep 2026-11-17: 0 matches; the lowercase word "website" appears in 15 files of page copy only) |
| Indexability decisions | **[V] PARTIAL** | City/intent pages return noindex when backend data is missing (`frontend/src/app/products/[slug]/in/[city]/page.tsx:11`, `frontend/src/app/products/[slug]/[intent]/in/[city]/page.tsx:18,21`); intent pages are self-canonical with a comment "index ONLY if content is unique … (future extension)" |
| Internal linking | **[V] PARTIAL** | `frontend/src/components/ProductSEO.tsx` internalLinks (category, similar products, city pages, top-rated) exist but `ProductJsonLd` and internal-link sections are client-fetched |
| Duplicate content | **[V] RISK** | Legacy `/product/[slug]` and `/category/[id]` routes redirect (307, not 301) to canonical paths (`frontend/src/app/product/[slug]/layout.tsx:31`, `frontend/src/app/category/[id]/page.tsx:31,47,54`); five intent variants allowed in routing vs two in sitemap |
| Performance / CWV | **[N/R]** | Not measured this turn. Known architectural costs: client-fetch product/category pages, client `ProductJsonLd` fetch, warm-up/service-worker components in root layout |
| Mobile usability | **[N/R]** | Not measured this turn |
| Supplier/manufacturer pages | **[V] GAP** | No `/manufacturers/[brand]` or `/suppliers/[supplier]` routes exist. Existing: `/products/[slug]/seller/[listingId]`, `/seller-catalog/[slug]`, `/ep/[slug]` (purpose not audited) |

**External market context [E]:** IndiaMART derives ~60% of desktop visits from organic search (SimilarWeb snippet, retrieved 2026-11-17) and operates massive programmatic directory surfaces (`dir.indiamart.com/impcat/…`, city + product pages). TradeIndia, Moglix and IndustryBuying run category- and brand-led hierarchies. These are competitors' patterns, not audited data.

## 3. Evidence-based technical audit (issues, severity, fixes, acceptance)

Severity: C=Critical, H=High, M=Medium, L=Low.

| # | Sev | Issue | Evidence [all V unless noted] | Recommended correction | SEO benefit | Acceptance test |
|---|---|---|---|---|---|---|
| T1 | **C** | Product page body client-rendered: crawler gets "Loading…" shell; specs, sellers, prices absent from initial HTML | `frontend/src/app/products/[slug]/(main)/page.tsx:1` `'use client'`; data via `useEffect` (`getEnterpriseProduct`) | Server component wrapper (per prior Phase C design): server-fetch `/api/products/{slug}/enterprise`, pass as initial state to client view; follow backend `redirect.canonicalSlug`; 404 on unknown | Largest single win: product queries (the money queries) can rank at all | `curl` a product URL: H1, ≥1 seller card, price or "RFQ" text present in raw HTML with JS disabled; "Loading" absent |
| T2 | **C** | Categories listing page client-rendered | `frontend/src/app/categories/page.tsx:1,128` (`'use client'`, "Loading categories...") | Server component; reuse the `CategoryCard` client island for image-error state only | Category hub becomes crawlable; passes PageRank to category detail pages | Raw HTML contains ≥1 category name and `/categories/<slug>` link |
| T3 | **H** | Sitemap emits category URLs built by `slugify(name)` although the DB comment says `slug=null` for all categories | `frontend/src/app/sitemap.ts` comment "prod DB currently stores slug=null for all categories — we still emit URLs" | Only emit `/categories/<stored-slug>` when a stored slug exists; otherwise exclude (or backfill slugs first) | Removes mass soft-404 submissions, protects crawl budget | Sitemap diff: every emitted category URL resolves 200 |
| T4 | **H** | Generic-indexable fallback metadata on product/city pages (thin 200s eligible for indexing) | `frontend/src/app/products/[slug]/(main)/layout.tsx:98–105` default metadata with `index:true`; `frontend/src/app/products/[slug]/(main)/page.tsx:1` unknown-slug behavior | Unknown slug → 404; backend SEO payload missing → `noindex` until real SEO fields exist | Prevents Google indexing empty templates | Request a nonexistent product slug → HTTP 404; a product without `seoTitle` → `noindex` |
| T5 | **H** | Legacy redirects are 307 (temporary), not 301 | `redirect()` calls in `frontend/src/app/product/[slug]/layout.tsx:31`, `frontend/src/app/category/[id]/page.tsx:31,47,54`. The categories hub page itself contains no redirect calls (grep 2026-11-17: none — an earlier session note citing that page at lines 121,137 was wrong; those lines hold a fetch call and a paragraph) | Use `permanentRedirect()` (or `redirect(…, 'replace')` with permanent semantics) for URL migration | Preserves link equity; Google treats migrations as permanent | `curl -I` legacy URL → `301` with correct Location |
| T6 | **H** | Hard-coded "Verified Suppliers" claims not backed by a verification field | `frontend/src/lib/cityPageRenderer.tsx:125` ("N Verified Suppliers"); `frontend/src/components/seo/SEOCalculatorLayout.tsx:83,207,236`; `frontend/src/app/categories/[slug]/page.tsx:64–65,375` | Show counts only when the API returns them, and drop "Verified" unless a real verification status exists on the seller record | Trust/compliance; avoids misleading markup (and any future review/verification schema claims) | Grep gate: no "verified" copy without a data-backed flag; rendered text matches API counts |
| T7 | **M** | No `metadataBase`; root layout OG has no URL/image; homepage has no canonical | grep `metadataBase` → 0 matches; `frontend/src/app/layout.tsx:19–27` | Set `metadataBase: 'https://udyogconnect.in'` (**approved apex**, not `www`); add homepage canonical + OG image | Correct OG/canonical resolution everywhere; richer snippets on shares | Validated `<link rel=canonical>` on `/` and correct absolute OG URLs |
| T8 | **M** | No WebSite schema; Organization schema duplicated (SSR layout + client `ProductJsonLd`) | no `'@type': 'WebSite'` node in `frontend/src` (grep 2026-11-17: 0); `frontend/src/components/ProductSEO.tsx:69–86` vs `frontend/src/app/products/[slug]/(main)/layout.tsx:32–60` | Add WebSite+SearchAction in root layout; render Organization once (SSR) and remove the client duplicate | Consistent entity signals; avoids duplicate-entity noise | One Organization node per HTML document; WebSite node present and validates |
| T9 | **M** | Intent routing allows 5 intents (`price, buy, suppliers, wholesale, cheap`) but sitemap ships 2; `buy/wholesale/cheap` are self-canonical thin variants | `frontend/src/app/products/[slug]/[intent]/in/[city]/page.tsx:5` (`SUPPORTED_INTENTS`) and `:24` ("future extension" comment) | Either restrict routing to the 2 supported intents or implement genuine content variation + eligibility flags for the rest; noindex anything unbacked | Controls doorpage risk; concentrates signals | Non-sitemap intents → 404 or noindex; eligible intents have unique H1 + unique intro verified per page |
| T10 | **M** | Sitemap hard cap silently drops URLs (`slice(0, MAX_URLS)`) | `frontend/src/app/sitemap.ts` | Emit an overflow signal (index-split sitemaps or log + fail loudly like backend overflow guard) | No silent coverage loss | With a >cap fixture, output is either complete or errors — never silently truncated |
| T11 | **M** | Category detail boilerplate mixes counts ("N products from X verified sellers") and empty categories are soft-200s | `frontend/src/app/categories/[slug]/page.tsx:245–250` (product cards with per-seller counts), `:375` ("strict verification" claim), `:192` ("Category Not Found" heading rendered as a normal 200 page, not `notFound()`) | Data-backed counts only; `notFound()` for unknown categories; noindex empty categories | Clean index surface, no misleading stats | Unknown slug → 404; empty-but-real category → `noindex`; counts equal API values |
| T12 | **L** | `ProductJsonLd` (client) re-fetches the same SEO payload the layout already fetches | `frontend/src/components/ProductSEO.tsx:49–56` (client `useEffect` at :49, fetch at :52; verified 2026-11-17) | If kept, pass SSR data down; else delete | Removes a client round-trip; faster LCP | Product payload fetched once per request (server log/devtools) |
| T13 | **L** | `ServerWarmUp` + `ServiceWorkerRegister` in root layout for every page incl. crawlers | `frontend/src/app/layout.tsx:9–10,51–52` | Confirm they are no-ops for bots; gate behind client-only mount | Removes crawler noise; slight CWV gain | Raw HTML shows no warm-up/service-worker work for crawler UAs |
| T14 | **H** | Canonical host conflict: production serves on `www` and redirects apex→`www` with a **307 (temporary)**; the owner-approved canonical is the apex `https://udyogconnect.in`. `frontend/src/app/robots.ts:21` and `frontend/src/app/sitemap.ts:3` hardcode `www.`, and 19 source files reference `www.udyogconnect.in` (grep 2026-11-17: 7 in `frontend/src`, 6 in `backend` non-test, 6 in `backend/tests`) | Measured 2026-11-17 via curl (§3.1); grep file list | Hosting/CDN must serve the apex directly and 301 `www`→apex; repo URL constants (`SITE_URL`, robots sitemap, future `metadataBase`) must switch to the apex. Neither change is approved for implementation yet | One consistent host signal for Googlebot; no duplicate-host dilution | `curl -sI https://udyogconnect.in/` → `200` (no redirect); `curl -sI https://www.udyogconnect.in/` → `301` with apex Location; robots/sitemap/canonical/OG URLs all apex; `grep -r "www\.udyogconnect" frontend/src` → 0 hits |

### 3.1 Canonical host: measured production redirect behavior (2026-11-17, curl)

| Requested URL | Status | Redirects to |
|---|---|---|
| `http://udyogconnect.in/` | 308 | `https://udyogconnect.in/` |
| `https://udyogconnect.in/` | **307 (temporary)** | `https://www.udyogconnect.in/` |
| `http://www.udyogconnect.in/` | 308 | `https://www.udyogconnect.in/` |
| `https://www.udyogconnect.in/` | 200 | — |

**Difference from the approved canonical destination.** The owner-approved canonical is `https://udyogconnect.in` (apex). Production currently answers apex HTTPS with a **temporary 307 to `www`**, and `www` serves the content. Meanwhile `frontend/src/app/robots.ts:21`, `frontend/src/app/sitemap.ts:3` (`SITE_URL`) and 19 source files tree-wide hardcode `www.` URLs (same grep), so every emitted canonical, sitemap URL and robots reference points at `www` as well. That is internally consistent for Google *today*, but it contradicts the approved apex destination, and a **temporary** redirect is the wrong class of signal for a permanent host decision. Two coordinated corrections are required; **neither is approved for implementation in this audit**:

1. **Hosting/CDN reconfiguration (owner action, outside this repo):** serve the apex directly (`https://udyogconnect.in` → 200) and redirect `www` → apex with **301**. The layer emitting today's 307 is **NOT VERIFIED** from this repository — the Next.js app in this tree contains no host-level redirect logic, so it is presumed to come from the hosting/CDN layer.
2. **Repo URL constants (implementation task, see §15 #2):** `SITE_URL` in `frontend/src/app/sitemap.ts`, the sitemap reference in `frontend/src/app/robots.ts`, and the future `metadataBase` (T7) must switch to the apex, with an audit of all 19 `www.`-hardcoding source files — otherwise the app would emit URLs conflicting with the apex even after the host is fixed.

No ranking outcomes are promised from this change; the goal is a single, consistent, owner-approved host signal. Search Console should use a **Domain property** (DNS-verified, host-agnostic) so verification survives the switch.

**NOT VERIFIED / NOT RUN:** live HTML of production (no deploy inspection), Core Web Vitals, mobile rendering, images/alt coverage audit, `ep/[slug]` and `seller-catalog/[slug]` content quality. Redirect chains on the live host were **measured** this audit (§3.1). **BLOCKED:** production database checks (legacy-slug counts, real category slug coverage) — requires the owner's read-only access.

## 4. Critical SEO issues and priorities

1. **Crawlability of the two money templates (T1, T2).** Until product and category-hub HTML is server-rendered, every other investment leaks.
2. **Canonical-host alignment (T14).** The measured 307 apex→`www` plus `www`-hardcoded repo URLs contradict the approved apex canonical; hosting reconfiguration and constant changes must precede Search Console property submission.
3. **Index-surface hygiene (T3, T4, T9, T11).** Eligibility gating must apply to *all* surfaces, not just the sitemap; the Phase 1 backend flags (`cityEligible`, `priceEligible`, `suppliersEligible`) are the enforcement point.
4. **Entity completeness (T7, T8).** Canonical/OG/WebSite foundation is cheap and unblocks rich results.
5. **Supplier/manufacturer layer (§7).** Highest-leverage *new* surface; only as data supports.
6. **Content & authority (§10, §11).** Calculators are a genuine differentiator; expand deliberately.

## 5. India-focused keyword research

**Data status:** No Keyword Planner or Search Console access was available during this audit, so **no search volumes or difficulty numbers are stated**. Demand tiers (High/Med/Low) are qualitative external estimates based on SERP competition observed in public results; every value must be validated in Keyword Planner / GSC before committing content capacity [E].

| Cluster | Example queries | Intent | Demand tier [E] | Competition [E] | Target URL | Notes |
|---|---|---|---|---|---|---|
| A1 Product head | "industrial safety gloves", "MS pipe", "SS304 plate" | Commercial | Med–High | High | `/products/[product]` | One page per product; unique title from backend `seoTitle` |
| A2 Spec/model | "ISMB 100 weight per meter", "6mm MS plate weight" | Informational→commercial | Med | Low–Med | `/tools/*` calculators + product page spec section | Calculators already SSR; cross-link to products |
| A3 Brand/model | "Havells MCB 32A", "Crompton motor 5HP price" | Commercial | High | High | future `/manufacturers/[brand]` | Only if brand data exists in DB; otherwise avoid |
| B1 Supplier national | "[product] manufacturers in India", "[product] suppliers in India" | Commercial | High | Very high (IndiaMART/TradeIndia) | `/products/[product]` (single canonical supplier page per product) | Compete long-term; rely on fewer-but-better supplied pages |
| B2 Supplier city | "[product] suppliers in Pune", "[product] manufacturers in Maharashtra" | Commercial | High | High | `/products/[product]/in/[city]` | Strictly gated by `cityEligible` |
| B3 Distributor/wholesaler | "[product] distributors in India", "[product] wholesalers in Pune" | Commercial | Med | Med–High | `/products/[product]/suppliers/in/[city]` with seller-role facets | Data-backed: seller `role` field exists (`SellerRoleBadge`) |
| C1 Price | "[product] price in India", "[product] price in Pune", "[product] wholesale price" | Transactional | High | High | `/products/[product]/price/in/[city]` | Only `priceEligible === true` (positive numeric `pricingTiers[].pricePerUnit`) |
| C2 RFQ/dealers | "[product] quotation", "[product] dealers near me" | Transactional | Med | Med | Product page inquiry CTA; no separate indexable page | Conversion surface, not a new page |
| D1 Category | "electrical equipment suppliers", "industrial automation suppliers" | Commercial | High | High | `/categories/[category]` | Requires real product coverage (T11) |
| D2 Category+city (future) | "electrical suppliers in Pune" | Commercial | Med | High | not built today | Build only after category pages have depth; otherwise skip |
| E Tools/informational | "pipe weight calculator", "angle weight calculation formula" | Informational | Med–High | Low | `/tools/*` (already live, SSR) | Link-magnet cluster; strongest defensible wedge |

**Cannibalization rule:** one primary cluster → one URL. Product supplier intent lives on `/products/[product]`; city intent on `/in/[city]`; price intent on `/price/in/[city]`; category intent on category pages. No page targets two primary clusters; internal-link sections (`frontend/src/components/ProductSEO.tsx`) pass intent-specific anchors.

**Keyword-to-URL examples for the nine live categories.** Category names and listing counts measured from the live API `GET /api/categories` on 2026-11-17; **no category exposes a `slug` field at all** (the field is absent, not null), so the T3 gate applies: no category URLs enter the sitemap until stored slugs exist. Titles are patterns, not commitments; counts shown are the measured API values.

| Live category (listings measured 2026-11-17) | Example primary cluster | Example supporting clusters | Target URL (slug to be stored) | Depth verdict |
|---|---|---|---|---|
| Lights & Lighting Accessories (102) | "industrial led lights suppliers" | "led high bay light price", "lighting manufacturers india" | `/categories/lights-lighting-accessories` | First-wave category content target |
| Panel Meters And Accessories (98) | "panel meters suppliers india" | "digital panel meter price", "analog panel meter wholesalers" | `/categories/panel-meters-and-accessories` | First-wave target |
| Solar Equipment & Panels (94) | "solar panel suppliers india" | "solar inverter price india", "solar panel wholesale" | `/categories/solar-equipment-panels` | First-wave target |
| VFD, PLC, HMI & Control Equipments (56) | "vfd suppliers india" | "plc suppliers pune", "hmi price india" | `/categories/vfd-plc-hmi-control-equipments` | First-wave target |
| Cleaning products (27) | "industrial cleaning products suppliers" | "industrial degreaser wholesalers" | `/categories/cleaning-products` | Second wave (after deep categories) |
| Electrical Equipment & Supplies (18) | "electrical equipment suppliers" (D1) | "cable tray manufacturers", "MCB suppliers" | `/categories/electrical-equipment-supplies` | Second wave |
| Safety Products (11) | "industrial safety gloves suppliers" | "safety shoes wholesalers india" | `/categories/safety-products` | Second wave |
| Metals & Industrial Raw Materials (3) | "ms plate suppliers india" | "ms pipe price per kg" | `/categories/metals-industrial-raw-materials` | Stays **noindex** until real depth (3 listings) |
| Electronics, IT & Industrial Automation (1) | — | — | `/categories/electronics-it-industrial-automation` | **noindex + sitemap-excluded** (1 listing; thin) |

Product-level examples (product slugs verified to exist in the sitemap-products format): `safety-hand-gloves-safety-products-supplier-india` → `/products/safety-hand-gloves-safety-products-supplier-india` targets cluster A1/B1; its city variant `/products/…/in/pune` targets B2 only if `cityEligible === true` for that pair; its `/price/in/{city}` variant targets C1 only if `priceEligible === true`.

## 6. Keyword-to-URL map (summary)

- `/products/{slug}` ← A1, B1, A3 (brand mention only), C2
- `/products/{slug}/in/{city}` ← B2
- `/products/{slug}/suppliers/in/{city}` ← B3 (only `suppliersEligible`)
- `/products/{slug}/price/in/{city}` ← C1 (only `priceEligible`)
- `/categories/{slug}` ← D1
- `/tools/{calculator}` ← E, A2
- `/manufacturers/{brand}` ← A3 (**route does not exist today**; build only with brand-backed data)
- Supplier entity page ← **gap**; `/products/{slug}/seller/{listingId}` and `/seller-catalog/{slug}` exist but are not audited for indexability [N/V]

### Competitor comparison — methodology, qualitative patterns, explicit limitations

**Methodology (this audit):** qualitative inspection of publicly served pages only — ~20 seed queries sampled in a desktop browser on 2026-11-17 across product head terms, "[product] suppliers in India/Pune", "[product] price in India" and category head terms; manual review of the public category, brand and product surfaces of IndiaMART, TradeIndia, Moglix and IndustryBuying; one public traffic source (SimilarWeb summary snippet for IndiaMART). **No crawler run, no rank tracking, no paid SEO tool.**

**Explicit data limitations:** this blueprint contains **no** search-volume, keyword-difficulty, domain-authority, backlink-count or ranking-position figures — none were measured and none are invented. Such numbers require owner-supplied tool access (Search Console property, Keyword Planner, and an Ahrefs/Semrush-class crawler); acquiring them is proposed as a Phase 1 measurement task. All competitor statements below are **[E] external estimates** from public observation and may be outdated at any time.

| Competitor | Observed pattern [E] | Observed strength | Implication for MIDConnect |
|---|---|---|---|
| IndiaMART | ~60% of desktop visits from organic search (SimilarWeb snippet, single source, retrieved 2026-11-17); `dir.indiamart.com/impcat/…` programmatic catalog; per-product, per-city and per-supplier directory surfaces at enormous scale | Decades-accumulated long-tail supplier × city × product entity pages and links | Do not fight the long tail head-on. Compete only where MIDConnect has genuine, verifiable supply (measured-deep categories), plus differentiated tools/content |
| TradeIndia | Similar directory model; category/brand hierarchies; buyer-lead funnels | Category coverage breadth | Same discipline as above; treated as secondary benchmark [E] |
| Moglix | E-commerce MRO catalog: brand + SKU pages, transactional PDPs with real prices | Brand/product page depth, PDP fundamentals | Product pages must match PDP fundamentals (specs, price tiers, honest availability) — supports the T1 SSR priority |
| IndustryBuying | Catalog e-commerce: brand + category landing pages with faceted filters | Category landing-page hygiene | Category template quality (T2, T3, T11) is the comparable battleground |

**Realistic opportunities for a smaller marketplace (qualitative):** (1) the calculator/tools cluster — competitors under-serve formula/spec content and it is already SSR on MIDConnect [V]; (2) genuinely supplied product × city × price pages with honest eligibility gating — competitors' programmatic pages are often thin or stale, so *eligibility discipline* is the differentiator; (3) RFQ-process transparency content (no competitor-neutral resource observed [E]); (4) measured-deep categories first (Lights 102, Panel Meters 98, Solar 94, VFD/PLC/HMI 56 listings as of 2026-11-17) rather than breadth.

## 7. Recommended landing-page architecture

Per page type: target keyword, required DB data, minimum content, indexability, canonical, schema, internal links, sitemap, conversion.

| Page type | Required data (all verified to exist in DB layer) | Minimum useful content | Index rule | Canonical | Schema | Conversion |
|---|---|---|---|---|---|---|
| `/products/{slug}` | product (name, slug, description, attributes, images); seller/listing data optional (enriches the page) | H1 product name; real description; spec grid; supplier/RFQ section when listings exist, honest empty state otherwise; category + similar-product links | index iff product visible AND canonical slug valid (**owner-approved 2026-11-17: sitemap eligibility is independent of listings**); `noindex` only when the product is invisible or the slug invalid | self | Product (+AggregateOffer only when ≥1 numeric price), Breadcrumb | "Get quotes" / seller inquiry |
| `/products/{slug}/in/{city}` | product + ≥1 active listing in city (`cityEligible`) | City intro from real listing cities; real sellers by city; spec summary | index iff `cityEligible` | self (`pageUrl` from backend) | Product/Breadcrumb | seller inquiry |
| `…/price/in/{city}` | same + numeric `pricePerUnit > 0` (`priceEligible`) | Real price table/range, MOQ; no invented prices | index iff `priceEligible` | self | Product with Offer | RFQ |
| `…/suppliers/in/{city}` | ≥2 distinct eligible sellers (`suppliersEligible`) | Real seller list with roles/cities | index iff `suppliersEligible` | self | ItemList of sellers | contact seller |
| `/categories/{slug}` | category with stored slug + ≥1 product | H1, real product grid, data-backed counts | index iff ≥1 product and stored slug exists | self | Breadcrumb | browse |
| `/categories/` hub | all categories | link list (become SSR, T2) | index | self | — | browse |
| `/manufacturers/{brand}` (**not built**) | real brand/maker records | brand description from verified data | index only with genuine data; otherwise don't build | self | Organization/ItemList | browse brand products |
| `/suppliers/{seller}` (**not built**) | seller profile + products | genuine profile: name, city, role, products | index only with real profile | self | Organization/ItemList | inquiry |
| `/tools/*` | none (self-contained) | calculator + explainer + supplier CTA | index (already SSR) | self | Breadcrumb | calculator → products |

**Owner-approved sitemap-eligibility rules (2026-11-17) and where they are implemented [V]:**

| Approved rule | Implemented by | Flag / mechanism |
|---|---|---|
| Product URL eligible when the product is active with a valid canonical slug — **independent of seller listings** | `backend/services/sitemap_product_service.py` reads `products` directly (visible filter: `isActive != false`, not deleted, `slug` matches `^[a-z0-9]+(-[a-z0-9]+)*$`; legacy aliases never emitted); consumed by the sitemap via `/api/seo/sitemap-products` [V]; `/api/products` intentionally unchanged [V] | Overflow raises 503 (`SitemapProductOverflowError`) instead of truncating |
| City-intent URL requires ≥1 genuinely eligible seller listing in that city | `backend/services/city_eligibility_service.py` grouped Mongo pipeline: active listing; seller not deleted/inactive/suspended/banned — a missing `sellerStatus` is **not** an exclusion; `canLogin` is not an exclusion | `cityEligible` |
| Price-intent URL requires ≥1 eligible listing with a numeric `pricingTiers[].pricePerUnit > 0` (no top-level or legacy `price` fallback) | Same pipeline (`$type` in double/int/long/decimal, `$gt: 0`) | `priceEligible` |
| Suppliers-intent URL requires ≥2 distinct eligible sellers in the city | Same pipeline (`$addToSet` of seller IDs) | `suppliersEligible` |

City counting happens inside MongoDB `$group`; the city filter runs inside the pipeline before the limit so the limit cannot silently drop allowed pairs; overflow raises `PairOverflowError` (HTTP 503) rather than truncating [V]. The frontend sitemap consumes only strictly-`true` flags — a missing or non-true flag is never eligible [V]. **These three flags are the only eligibility fields in the current local implementation;** older field names from interim drafts (e.g. `indexableOnly`, `indexableIntents`) do **not** exist in the current services and must not be assumed by anyone reading earlier session notes.

**Implementation-status separation:** (a) *Current local implementation* — the uncommitted 3-file change + 2 untracked services + tests described above [V]. (b) *Previously observed production implementation* — the pre-Phase-1 `mode=all` endpoint returned every active product × top-N cities with no seller check, and the sitemap was unfiltered; observed in an earlier audit, **not re-verified against production this turn** [N/V]. (c) *Not deployed* — everything in this tree; nothing has been committed, pushed or deployed. (d) *Awaiting independent acceptance* — the 38 scoped self-authored tests and the code itself; no independent certification exists.

**Rules enforced:** product URLs independent of city eligibility **[V — implemented in sitemap-products service]**; no thin auto-generated pages; noindex + sitemap exclusion for unbacked pages; no fake counts/reviews/ratings/prices — the existing hard-coded "Verified" copy (T6) must be removed or data-backed first.

## 8. On-page SEO standards (templates)

- **Titles** ≤60 chars where possible, pattern: `{Product} – Price, Suppliers & Specs in India | UdyogConnect`; city: `{Product} in {City} – Suppliers & Prices`; category: `{Category} Suppliers in India | UdyogConnect` (data-backed count in description only).
- **Meta descriptions** 150–160 chars, one per page, from backend `seoDescription`; never duplicated across city/intent variants.
- **H1/H2:** exactly one H1 = entity name (+ city/intent qualifier). H2s: Specifications / Suppliers in {City} / Price range / About {Category} / Related. Current pages largely conform [V]; enforce in templates.
- **Images:** alt = product name + distinguishing attribute; never "image". Requires an alt-coverage audit [N/V].
- **Breadcrumbs:** visible breadcrumb + matching BreadcrumbList JSON-LD (already SSR on product [V]; category uses microdata [V]; city page must match visible nav [N/V]).
- **Internal links:** every product page links its category, ≥3 similar products, and its eligible city pages (fields already returned by `/api/products/{slug}/seo` [V]); city pages link back to product and category.
- **Prohibited without data:** AggregateRating/review markup, "verified" claims (T6), invented specs/counts.

## 9. Content strategy and topical authority

**Differentiated assets (real value, not generic AI filler):**
1. Weight/weight-per-meter calculators (already live, SSR [V]) → expand into "formula + worked example + size table" pages; each links to the matching product pages.
2. Spec-selection guides tied to actual categories (e.g., "How to choose an MCB rating", "MS pipe schedule chart") — only for categories with real inventory on the platform.
3. Price-procurement guides anchored to genuinely priced products (`priceEligible` pages).
4. Comparison content only between listings that actually exist (multi-seller products with `suppliersEligible`).

**90-day calendar (first 12 of ~18 planned; priority P1 first).** Each item: title — primary keyword — intent — reader — internal links — verification requirement. Reader always: industrial buyer/procurement.

| Wk | Piece | Primary keyword [E tier] | Links to | Verification needed |
|---|---|---|---|---|
| 1 | Pipe weight chart + calculator guide (P1) | "pipe weight calculation" (Med) | `/tools/pipe-weight-calculator`, pipe products | Engineer-verified formulas |
| 2 | MS plate weight guide (P1) | "ms plate weight chart" (Med) | plate products | Same |
| 3 | "How to buy industrial safety gloves" (P2) | "safety gloves buying guide" (Low-Med) | gloves category/products | Category has real listings |
| 4 | ISMB beam sizes explained (P1) | "ISMB beam weight" (Med) | beam calculator | Spec table verified |
| 5 | Electrical MCB selection guide (P2) | "MCB rating selection" (Med) | electrical category | Category coverage exists |
| 6 | Steel price factors in India (P2) | "steel price per kg India" (High, hard) | price-eligible steel products | Real price data |
| 7 | Pump selection basics (P3) | "water pump selection" (Med) | pumps category | Category coverage |
| 8 | Industrial fasteners types (P3) | "fastener grades explained" (Med) | fasteners products | Coverage |
| 9 | Chemical storage compliance (P3) | "industrial chemical storage" (Low) | chemicals category | SME review |
| 10 | SS304 vs MS comparison (P2) | "ss304 vs mild steel" (Med) | both product pages | Metallurgy SME review |
| 11 | How RFQs work on UdyogConnect (P1) | "industrial rfq process" (Low) | product CTAs | Internal process doc |
| 12 | Steel pipe schedule table (P1) | "pipe schedule chart" (Med) | pipe products | Verified table |
| 13 | VFD/PLC buying checklist (P2) | "vfd selection guide" (Med) | VFD/PLC category (56 listings measured 2026-11-17) | Product-coverage check |

**90-day wave structure:** days 1–30 = low-dependency pieces (weeks 1, 2, 4, 11, 12 — the tools/formula cluster and RFQ piece, all anchored to already-SSR calculator pages); days 31–60 = category-anchored guides (weeks 3, 5, 13 plus one per measured-deep category) gated on real category inventory; days 61–90 = comparison/compliance pieces (weeks 6, 8, 9, 10) gated on SME review, plus a refresh pass over the days-1–30 pieces. Cadence: 1 piece/week minimum; each piece needs one SME verification step (named owner) before publish; each links ≥1 category and ≥2 product pages. **Rule:** no piece publishes if its linked category has zero real listings — orphan thin content damages the cluster.

## 10. Backlink and authority strategy (legitimate only)

- **Genuine citations:** register the business with Indian industrial/MSME directories and associations where the business genuinely belongs (e.g., CII/MSSI member listings, local Pune trade bodies) — factual NAP citations only.
- **Supplier partnerships:** every onboarded supplier's own website linking its storefront ("View our products on UdyogConnect") — highest-quality, most defensible links; make it a standard onboarding artifact.
- **Calculator link-magnet:** the tools cluster [V] is the most linkable asset; promote size/weight charts to engineering communities, college labs, and forums where engineers genuinely use them.
- **Original data:** publish aggregate, anonymized marketplace statistics (e.g., "most-quoted industrial products this quarter") — only from real data, quarterly.
- **Guest/technical publications:** contribute spec-formula explainers to engineering trade publications with editorial standards; byline + link.
- **Excluded:** purchased links, PBNs, automated directory blasts, irrelevant link exchanges [per owner policy and Google guidelines].

Targets are *referring domains that bring industrial buyers*, measured in GSC (branded + non-branded clicks from linked pages), not raw link counts. **[N/V]** current backlink profile unknown — needs an owner-run audit tool (Ahrefs/GSE data) before prioritization.

## 11. Google Search Console and GA4 measurement plan

**Search Console:** create a **Domain property** for `udyogconnect.in` (DNS-verified, host-agnostic — survives the apex/`www` reconfiguration) plus a URL-prefix property on the approved apex `https://udyogconnect.in`; do **not** register a `www` property without new owner approval [access required — N/V]; submit `https://udyogconnect.in/sitemap.xml`; monitor: indexed vs submitted per template; "Crawled–not indexed" reasons for city/intent pages; canonical drift after T5 (301s) and the T14 host change; Core Web Vitals report per template. Success metric chain: submitted → indexed (eligible only) → impressions → CTR → clicks.

**GA4 events (no PII; IDs hashed or opaque):**
| Event | Trigger | Parameters |
|---|---|---|
| `view_item` | product page view | `item_list_id` (category slug), `product_slug`, `seller_count` |
| `search` | site search submit | `search_term`, `results_count` |
| `view_item_list` | category/city page grid view | `item_list_id` |
| `generate_lead` | inquiry/quote submitted | `product_slug`, `city`, `seller_id` (opaque), `value` only if a real price exists |
| `sign_up` | buyer registration completed | `method` (email/otp) |
| `contact_supplier` | seller contact/WhatsApp click | `seller_id`, `product_slug` |

**Not implemented today [N/V]:** GA4 was not audited in this pass — an implementation audit is a Phase 1 task. Merchant Center: only if a genuine transactional model (fixed-price checkout) exists; currently the model is RFQ-based → **skip Merchant Center** unless the business model changes.

**KPIs — measured baseline vs proposed targets.** Baselines marked *measured* were taken 2026-11-17; GSC/GA4 baselines are **NOT RUN** (no access); every target is a **proposal** to be recalibrated after the first 28 days of GSC data. No position targets are promised; rank tracking is directional only.

| KPI | Baseline | Target (proposed) |
|---|---|---|
| Live categories / total listings | 9 categories, 410 listings (live API, measured 2026-11-17) | Context metric; grows with onboarding |
| Sitemap: eligible-only URLs | Current tree implements the gating [V]; **production state NOT VERIFIED** | 100% of submitted URLs resolve 200 and satisfy the approved eligibility rules |
| Product/category main content in initial HTML | **FAIL [V]** (T1/T2: client-rendered at HEAD) | PASS on both templates within 30 days of implementation approval |
| Canonical host consistency | **FAIL (measured)**: 307 apex→`www`; `www.` hardcoded in 19 source files (grep 2026-11-17) | Apex serves 200, `www` 301→apex, all emitted URLs apex |
| Indexed eligible pages (GSC) | NOT RUN | ≥90% of eligible URLs indexed within 90 days of ship |
| Non-branded impressions / clicks (GSC) | NOT RUN | Establish a 28-day baseline, then +20–30% QoQ (recalibrate after baseline) |
| CTR (GSC) | NOT RUN | Baseline first; improved via §8 title/description templates |
| Organic `generate_lead` / month (GA4) | NOT RUN (GA4 audit pending) | ≥1 per week by day 90 (proposed) |
| Organic `sign_up` / month (GA4) | NOT RUN | Baseline first; tracked QoQ |
| Product-page / category-page organic traffic split (GA4) | NOT RUN | Dashboard live within 30 days of GA4 implementation |

## 12. Four-phase implementation roadmap

**Phase 1 — Technical SEO foundation** (dependency gate: approved Phase 1 eligibility work ships first)
| Task | Pri | Benefit | Files | Approach | Regression tests | Acceptance | Verify | Effort [E] |
|---|---|---|---|---|---|---|---|---|
| P1.1 Server-render product body (T1) | P0 | Product queries rankable | `frontend/src/app/products/[slug]/(main)/page.tsx`, new client child | Server wrapper + initial-data prop (prior Phase C design) | Unit: unknown slug 404; redirect slug 307; E2E: raw HTML contains H1/sellers | raw HTML has main content; all interactions still work | curl + browser | L |
| P1.2 SSR categories hub (T2) | P0 | Category hub crawlable | `frontend/src/app/categories/page.tsx`, `CategoryCard` | Server page + client island | Build passes; HTML test | category names+links in raw HTML | curl | S |
| P1.3 Sitemap category slug gate (T3) | P0 | No soft-404s submitted | `frontend/src/app/sitemap.ts` | Emit only stored slugs | Sitemap test vs API | every category URL 200s | script | S |
| P1.4 Fallback noindex + 404 (T4) | P0 | No thin indexing | `frontend/src/app/products/[slug]/(main)/layout.tsx`, city/intent pages | 404 unknowns; noindex without SEO payload | HTTP tests | 404/noindex observed | curl | M |
| P1.5 301 legacy redirects (T5) | P1 | Link equity | `product/[slug]`, `category/[id]` | `permanentRedirect` | redirect tests | 301 + Location correct | curl -I | S |
| P1.6 metadataBase + canonical home + WebSite/Org dedupe (T7,T8) | P1 | Entity correctness | `frontend/src/app/layout.tsx`, `frontend/src/components/ProductSEO.tsx` | Add fields; single Org node | schema validation | validates; 1 Org node | Rich Results Test | S |
| P1.7 Verified-claims cleanup (T6) | P1 | Trust/compliance | renderer + category + calculators | data-backed counts | grep + render test | no unbacked "verified" copy | grep/inspection | S |
| P1.8 Intent surface alignment (T9) | P1 | Doorpage control | intent page | restrict or data-gate extra intents | route tests | unsupported intents 404 | curl | S |
| P1.9 Finalize uncommitted Phase 1 sitemap eligibility work | P0 | Honest sitemap | `backend/services/city_eligibility_service.py`, `backend/services/sitemap_product_service.py`, `frontend/src/app/sitemap.ts`, `backend/server.py` SEO endpoints | **Code + tests done this session:** 38/38 scoped tests green on disposable MongoDB 7.0.14 (2026-11-17) | 21-case eligibility matrix + 14-case products service + 3 HTTP 503 cases | Scoped suite green; independent code review pending; deployment separately authorized | pytest + curl | M |
| P1.10 Canonical-host alignment (T14) | P0 | Single approved host signal | hosting/CDN (owner action) + `frontend/src/app/sitemap.ts`, `frontend/src/app/robots.ts`, `frontend/src/app/layout.tsx`, ~19 `www.`-hardcoding source files | Owner reconfigures host (apex 200, `www`→apex 301); repo constants switch to apex | Redirect + emitted-URL tests | Apex 200, `www` 301→apex; no emitted `www.` URLs | curl + grep | S + external |

**Phase 2 — Commercial landing pages:** P1.1–P1.8 shipped → then supplier-profile indexability audit (`seller/[listingId]`, `seller-catalog/[slug]`) → `/manufacturers/{brand}` builder (only with real brand data) → `/suppliers/{seller}` (only with genuine profiles) → category+city pages (only for categories with real multi-city coverage). Each new surface follows the §7 gate table; regression: eligibility-unit tests extend to each new intent/flag.

**Phase 3 — Content and topical authority:** §9 calendar begins once P1 ships; each piece gated on real category inventory; quarterly original-data posts.

**Phase 4 — Authority and organic conversion:** supplier-link onboarding artifact; calculator outreach; quarterly data reports; conversion-path optimization on `generate_lead` funnel measured in GA4.

## 13. Regression and acceptance checklist (current state)

| Requirement | Status | Evidence |
|---|---|---|
| No broken canonical URLs | **NOT RUN** (live) / [V] canonicals present in templates | templates read |
| No unintended noindex on important pages | **PASS [V]** for product/city/category templates; generic-fallback risk T4 | files |
| No ineligible sitemap URLs | **PASS [V]** (city/intent gated); **FAIL [V]** for category-slug risk T3; **NOT RUN** end-to-end | sitemap.ts |
| No duplicate canonical product URLs | **PASS [V]** legacy routes redirect; **FAIL [V]** 307 not 301 (T5) | files |
| Canonical host = approved apex `https://udyogconnect.in` | **FAIL (measured)** — production 307 apex→`www`; `frontend/src/app/robots.ts:21`, `frontend/src/app/sitemap.ts:3` and 19 source files hardcode `www.` | curl 2026-11-17 (§3.1), grep |
| Product/category content in initial HTML | **FAIL [V]** (T1, T2) | files |
| Structured data validates | **NOT RUN** (Rich Results Test) | — |
| No invented product/supplier info | **FAIL [V]** (T6 verified-claims; boilerplate counts T11) | files |
| Auth / payment I3 untouched by SEO work | **PASS** — this audit changed nothing; the uncommitted `backend/server.py` diff was inspected 2026-11-17 and touches only `/api/seo/sitemap-products` (addition) and the `mode=all` eligibility rewrite; no auth or payment path appears in the diff | git diff |
| Existing regression tests pass | **Mixed — two runs, both reported.** (1) Earlier 2026-11-17 run: **38/38** scoped tests green on a reused test database. (2) Re-verification on a **virgin** disposable MongoDB 7.0.14: **37 passed, 1 failed** — `backend/tests/regression/test_sitemap_products_http.py::test_overflow_returns_503_and_is_not_reported_as_db_error` seeds no products and relied on leftovers in the fixed-name test DB; with an empty collection a zero cap cannot overflow (limit(1) → 0 docs → 200). Test-isolation defect, **not edited** (owner restriction); the overflow guard itself is unit-proven in `backend/tests/regression/test_sitemap_products.py`. Root `python -m pytest` has 8 pre-existing legacy collection errors (unchanged) | session history, bash run |
| Sitemap output tested against controlled data | **PASS with one isolation caveat** — 21-case grouped-eligibility matrix, 14-case products service and the DB-unavailable HTTP case all green on a virgin disposable DB (2026-11-17); the HTTP overflow case is data-dependent (see row above). Production-scale rerun **NOT RUN** | session history, bash run |
| Mobile & performance documented | **NOT RUN** | — |
| GSC validation documented | **BLOCKED** (no GSC access) | — |

## 14. Risks, dependencies, unresolved questions

**14.1 Working-tree baseline (re-verified 2026-11-17 — exact)**

| State | Paths |
|---|---|
| Modified (tracked) | `backend/server.py` (Phase 1 sitemap endpoints only: `/api/seo/sitemap-products` addition with overflow/DB-unavailable 503s + `mode=all` eligibility rewrite — 56 changed lines), `frontend/package.json` (3 lines), `frontend/src/app/sitemap.ts` (37 lines: eligibility-gated URL build) |
| Untracked | `.exvisit/`, `MIDConnect_Google_SEO_Growth_Blueprint.md` (this document), `backend/services/city_eligibility_service.py`, `backend/services/sitemap_product_service.py`, `backend/tests/phase1_db_guard.py`, `backend/tests/regression/` (4 test files) |

This matches the owner-provided baseline exactly; the earlier "36 tracked files modified" figure from interim session reports is obsolete and superseded by this table. **Earlier session reports also described remediation work (product/category SSR, slug-resolver hardening, auth allowlists, referral-router lifecycle fix and others) that is NOT present in this tree** — it predates the current working state and is not a baseline for anything in this blueprint. No prior report establishes acceptance. **Deployed production behavior was not re-verified this turn** except for the DNS/redirect chain (§3.1, measured) and the live categories API (9 categories, no `slug` field, measured). Production sitemap-endpoint behavior is **NOT VERIFIED** this turn; the pre-Phase-1 description in §7 is historical observation, not a current measurement.

**Risks**
1. The only uncommitted Phase 1 work (3 modified tracked files + untracked services/tests) has no backup copy outside this tree; any careless reset would destroy it.
2. Root `python -m pytest` fails collection on 8 legacy live scripts (needs `REACT_APP_BACKEND_URL`/live Mongo) — pre-existing; a proposal to isolate them was deferred by the owner.
3. Sitemap category URLs (T3) may currently be submitting mass soft-404s.
4. The 62-pair public sitemap result reconciliation remains **BLOCKED** (original dataset never supplied).
5. Production legacy-slug audit (Task B, read-only) remains **BLOCKED** pending a verifiable read-only connection.

**Open questions for the owner**
1. Approve scope of T1/T2 reimplementation (rebuild product SSR from the prior Phase C design?).
2. ~~Confirm the canonical host~~ — **resolved by owner decision 2026-11-17: the apex `https://udyogconnect.in` is canonical.** Measured production still redirects apex→`www` (307) and repo constants still say `www.` — see §3.1/T14; the reconfiguration is a pending implementation item (§15 #2), not a new question.
3. Provide GSC/Keyword Planner access and read-only DB access for Task B and validation.
4. Decide brand/supplier page build order once data coverage is known.
5. Decide whether GA4 exists today (audit not yet performed).

## 15. Recommended first 10 implementation tasks (after approval)

| # | Task | Priority | Depends on | Acceptance criterion |
|---|---|---|---|---|
| 1 | Finalize the Phase 1 sitemap-eligibility work and hand off for deployment | P0 | Owner approval to implement and, separately, to deploy | Scoped suite 38/38 green on disposable DB (achieved 2026-11-17); independent review of both services + `frontend/src/app/sitemap.ts`; deployment only when separately authorized |
| 2 | Canonical-host repo constants → apex (T14, code side) | P0 | Owner completes the hosting change (§3.1): apex 200, `www`→apex 301 | `grep -r "www\.udyogconnect" frontend/src` → 0 hits; emitted canonical/sitemap/robots URLs all apex; curl checks of §3.1 inverted |
| 3 | T2 categories hub SSR | P0 | Task 1 | Raw HTML of `/categories` contains ≥1 real category name and `/categories/…` link; production build passes |
| 4 | T1 product body SSR | P0 | Task 1 | Raw HTML of a product URL contains H1, description and spec/seller content; unknown slug → 404; alias slug → permanent redirect; all interactions unchanged |
| 5 | T3 sitemap category-slug gate | P1 | Category-slug backfill decision (owner) | Every emitted category URL resolves 200; no `slugify(name)` fallback URLs in the sitemap |
| 6 | T4 fallback noindex + 404 rules | P1 | Task 4 | Unknown product/category slug → 404; missing backend SEO payload → `noindex` |
| 7 | T5 legacy 301 redirects | P1 | None | `curl -I /product/{slug}` and `/category/{id}` → 301 with canonical Location |
| 8 | T6 verified-claims data-backing | P1 | None | No "verified"/count copy without a data-backed flag; rendered counts equal API values |
| 9 | T7+T8 `metadataBase` (apex), home canonical, WebSite schema, Organization dedupe | P2 | Task 2 | Rich Results Test / Schema Markup Validator pass; exactly one Organization node per document; home canonical on the apex |
| 10 | Supplier-page indexability audit + GA4 event instrumentation (§11) | P2 | Tasks 3, 4 | Written audit for `seller/[listingId]`, `seller-catalog/[slug]`, `ep/[slug]`; GA4 debug view shows `view_item`, `search`, `generate_lead`, `sign_up` without PII |

**Owner actions required (outside this repo, blocking):** hosting/CDN reconfiguration for the apex canonical (§3.1); Search Console Domain property + GA4 access; Keyword Planner or equivalent for volume validation; read-only production DB access to unblock the production legacy-slug audit and the 62-pair reconciliation (both remain **BLOCKED**).

---

**End of blueprint. Implementation is NOT AUTHORIZED and awaits owner approval.**
