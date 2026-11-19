# UdyogConnect — Product SEO Quality & Competitive Gap Audit

**Date of audit:** 2026-11-18 (all live evidence fetched 2026-11-18, 12:57–14:30 UTC)
**Scope:** All product URLs in the live production sitemap. No source files changed.
**Canonical domain (owner-approved):** `https://udyogconnect.in` — production still serves/redirects via `www` (apex 307 → www); all live evidence below reflects the `www` serving state.

## Methodology and evidence basis

Verified live sources (no data fabricated):

1. **Live sitemap** `https://udyogconnect.in/sitemap.xml` (1.09 MB, served after apex→www 307) — full URL inventory extracted and classified.
2. **Live HTML** of base product pages, city pages, price pages and suppliers pages (raw SSR HTML inspected, not rendered JS).
3. **Live backend SEO payload** `GET https://midconnect.onrender.com/api/products/{slug}/seo` for **all 48 products** (fields: seoTitle, seoDescription, seoContent, jsonLd, breadcrumbJsonLd, faqJsonLd, internalLinks, sellerCount, sellersByCity, min/max price, minMoq, availableCities, canonicalUrl).
4. **Live enterprise listing payload** `GET /api/products/{slug}/enterprise` sampled (VFD, panel-fan) — listing-level specs, brands, images, pricing tiers.
5. **Frontend/backend code** (worktree) for page architecture and JSON-LD generation paths.
6. **Competitor SERP evidence**: live searches for VFD and solar on-grid inverter queries; IndiaMART VFD category page fetched; ABB/Schneider/Moglix/TradeIndia/vfds.org/solarcalculators.in snippets captured.

**Not available / NOT EXECUTED (owner must supply):** Google Search Console query, impression and click exports. Therefore **no search volume, ranking position, CPC or traffic figures appear anywhere in this report**. All keyword data is explicitly split into *verified* (fetched from the site itself) and *hypothesis* (unverified).

**Indexation probe:** a live web search for `udyogconnect.in` (2026-11-18) returned: home, /about, /categories, /sell, /contact, and one product page — `https://www.udyogconnect.in/product/connectors-electrical-equipment-supplies-supplier-india` with stale title "Best Connectors Prices in India (2026)". This is a **probe sample, not a full index audit** (a full `site:`/GSC coverage analysis was not possible). It does verify: (a) product pages are being indexed; (b) Google holds **legacy singular `/product/` URLs** that now 307-redirect to `/products/`; (c) Google displays a title format that no longer matches the current template.

## 0. Executive summary

- The live sitemap contains **48 base product pages** (`/products/{slug}`) plus **4,860 city/intent variant URLs** across **81 slugs** (20 cities × 3 intents × 81 slugs). 33 of the 81 slugs have variant URLs in the sitemap but their base page is absent from it — yet those base pages return **HTTP 200** live. Sitemap prioritization is inverted: it lists low-value variant URLs while omitting base pages.
- **Base product pages are client-rendered shells.** Raw SSR HTML contains **zero H1/H2** and a "Loading product..." placeholder; every product content block (listings, prices, suppliers, images, specs, FAQ, enquiry CTA) renders only after JavaScript. The city/intent variant pages **are** server-rendered (2 H1s, ~1,600–2,700 words) but contain templated content and the claim "**0 Verified Suppliers**" for the vast majority of (product, city) pairs — contradicting the same page's FAQ schema ("buy from N verified suppliers").
- **Supplier presence does not support the URL count.** Every product has sellers in only **1–3 cities** (verified from `availableCities` in all 48 SEO payloads), yet the sitemap publishes 20 city pages + 40 price/supplier city pages per slug. ≈95% of the 4,860 variant URLs have no real supply behind them — a doorway-page pattern and crawl-budget sink. (An eligibility-filtering sitemap service already exists uncommitted in the worktree and addresses exactly this; it is **not deployed**.)
- **Structured data has one systematic defect:** Product JSON-LD and Breadcrumb JSON-LD point to `https://www.udyogconnect.in/product/{slug}` (**singular**, from `backend/services/seo_service.py`), while metadata canonical URLs correctly use `/products/` (plural, from `backend/server.py`). The indexed legacy `/product/` URLs corroborate that Google has been fed the singular form.
- **Data depth exists in the backend but never reaches the SERP-visible layer.** Listing-level records contain real brands, model series, specifications, pricing tiers, MOQ, stock and lead times (e.g., VFD listings: "Schneider Electric", "Altivar Process ATV630", IP20, three-phase). The Product JSON-LD, by contrast, emits brand **"Various Manufacturers"** and templated 141–160-character descriptions (one product, panel-fan, emits a **9-character** description).
- **Quality scores: all 48 pages score 35–64/100** (median 52) on the 100-point framework in §5. No product page is currently competitive for high-value Indian industrial queries. The strongest candidates — PLC (21 sellers), VFD (14), industrial meter (42), LED flood light (29), MCPCB lights (24), industrial switches (25), LED panel light (19), solar on-grid inverter (16), electrical boxes (15), energy meter (13) — can realistically compete once content is server-rendered, brand/spec data is surfaced, and the sitemap is pruned.

## 1. Verified live inventory

| Segment | Count | Notes |
|---|---|---|
| Base product pages in sitemap | 48 | `/products/{slug}` |
| Base product pages live (HTTP 200) | 48+ | Variant-only slugs' base pages also return 200 (4 tested) |
| Distinct slugs overall | 81 | 48 in sitemap base list + 33 "variant-only" slugs |
| City/intent variant URLs in sitemap | 4,860 | `/products/{slug}/in/{city}`, `/price/in/{city}`, `/suppliers/in/{city}` × 20 cities |
| Product categories | 9 | Control (VFD/PLC/HMI), Solar, Lighting, Panel Meters, Electrical, Safety, Cleaning, Metals, IT/Office |
| robots.txt | OK | Sitemap referenced; apex serves 307→www |

**Sitemap category mix of the 48:** Solar 11, Lighting 9, Control 8, Panel Meters 8, Cleaning 4, Safety 5, Metals 3, Electrical 2, IT/Office 1 — plus the 33 variant-only slugs (valves, office supplies, tools etc.).

### Key architectural facts (verified from live HTML + code)

| Aspect | Base page `/products/{slug}` | Variant pages `/in/{city}`, `/price/in/{city}`, `/suppliers/in/{city}` |
|---|---|---|
| Rendering | `'use client'` — content CSR only ("Loading product...") | SSR (full content in raw HTML) |
| H1 | **0** | **2 (duplicate)** |
| Title | "Compare {X} Prices in India (2026) \| UdyogConnect" | "Compare/Price of/Top {X} in {City} (2026) \| UdyogConnect" |
| Canonical | self-referencing, `/products/` plural (www) | self-referencing incl. variants (www) |
| JSON-LD | Product, Brand, AggregateOffer, BreadcrumbList, FAQPage, Organization | Product, Brand, City, Country, Offer, PriceSpecification, BreadcrumbList, FAQPage, Organization |
| Supplier claim | "N verified suppliers" (client-side) | **"0 Verified Suppliers"** in SSR for almost all pairs |
| Word count (SSR) | 74 (header/footer only) | 1,544–2,731, heavily templated |

**Missing or inaccurate information found (field-by-field):**

- **Manufacturer/brand:** Product-level JSON-LD says brand **"Various Manufacturers" on 37 of 48** products (the other 11 carry seller-name brands such as "R S ENTERPRISES", "Akash Enterprises"); real OEM brands exist only at listing level in the DB (verified: Schneider Electric on a VFD listing). Not surfaced in metadata or SSR.
- **Model/SKU:** No product-level model/SKU anywhere. Listing-level `product_series` exists for some control listings (e.g., Altivar ATV630). B2B buyers searching "ATV630 price India" find nothing.
- **Technical specifications:** Listing-level `searchableAttributes` are rich for sampled control-equipment listings; **panel-fan's attributes are all zeros/−1** (placeholder data). Spec depth for the other 46 products is unverified at listing level (provisional scores).
- **Description:** Generated, near-identical across products (template with name/category/seller count): **27/48 are 141–160 chars**, 16/48 are longer (≥500 chars at extraction cap), 4/48 are 234–310 chars, and panel-fan's Product JSON-LD description is a broken **9-character** string.
- **Variants:** `variantId` exists per listing; no product-level variant display in SSR/metadata.
- **Images:** 1–2 images per product in JSON-LD (25 products have 1, 23 have 2); base-page SSR contains no product `<img>`; alt-text quality on listing images not verifiable pre-JS.
- **Pricing/availability:** Price ranges and MOQ verified via payload; stock/lead time only in client-rendered listings.
- **FAQ:** 4 templated questions per product, identical structure across all 48.
- **Internal links:** 5 generated links per page + breadcrumb + nav; no category↔product hub linking beyond these.
- **Indexability:** No noindex found; all in sitemap; base pages effectively invisible to crawlers that don't execute JS in the first wave of rendering.

## 2. Rendering & indexability audit (verified counts)

Measured on live raw SSR HTML fetched 2026-11-18:

| Check | Base pages `/products/{slug}` (n=48) | Variant pages `/in/{city}` etc. (sampled) |
|---|---|---|
| HTTP status | 200 (48/48 fetched) | 200 |
| noindex / x-robots | 0 | 0 |
| H1 in raw HTML | **0 on all 48 audited** | 2 (duplicated) |
| SSR word count | **0–76 on all measured** (7/48 captures lacked the counter; all 41 measured <150 words) | 1,544–2,731 |
| Price/enquiry strings in raw HTML | 41/48 — nav/footer-level only; **0 spec tables** | present |
| JSON-LD in raw HTML | Product, Brand, AggregateOffer, BreadcrumbList, FAQPage, Organization | Product, Brand, City, Country, Offer, PriceSpecification, BreadcrumbList, FAQPage, Organization |
| Canonical | self-referencing `/products/` (plural, www) | self-referencing variant URL (www) |

## 3. Search intent map (verified vs hypothesis)

**Verified** = observed on the live site or a fetched competitor page. **Hypothesis** = judged demand; **no volume data exists in this report** (GSC exports were not available).

| # | Query archetype | Example | Verified on UdyogConnect | Competitor owner of the intent today | UC gap |
|---|---|---|---|---|---|
| A1 | `{product} price in India / price list` | "vfd price in india" | Price ranges exist in SEO payload for 48/48 (₹2–₹2,75,000 spans) — but client-rendered only | IndiaMART (1000+ VFD products, ₹8,000–₹35,000), Moglix, solarcalculators.in | SSR prices + price-range copy |
| A2 | `{product} suppliers / manufacturers / dealers in India` | "vfd suppliers india" | sellerCount 1–42 per product (verified payload) | IndiaMART, TradeIndia (548 on-grid inverter listings) | supplier list SSR + count claims consistent |
| A3 | `{product} in {city}` / `{product} price in {city}` | "vfd dealers in pune" | Only **62 real (product, city) pairs** (sum of `cities`, max 3 per product); 1,620 city URLs published | IndiaMART/TradeIndia city-filter pages | publish only cities with real sellers |
| A4 | brand + model queries | "schneider atv630 price", "abb contactor price india" | Listing-level `product_series` exists (e.g. Altivar ATV630); **zero model-level pages** | Moglix (ATV340/310/320 series pages), official ABB/Schneider pages | model/series landing data (**hypothesis demand**) |
| A5 | spec/selection queries | "vfd 2.2 kw price", "5 kw on-grid inverter price" | Listing specs exist in DB for control equipment; not rendered | solarcalculators.in, vfds.org, Moglix kW-filtered listings | spec tables + kW-size anchors (**hypothesis demand**) |
| A6 | how-to / buying-guide | "how to choose a vfd", "on-grid vs off-grid inverter" | Nothing on site | solarcalculators.in, Waaree guides | editorial content (**hypothesis demand**) |

## 4. Competitive gap analysis (live-fetched 2026-11-18)

Evidence: Moglix VFD category page (HTTP 200, full fetch), TradeIndia on-grid solar inverter manufacturers page (HTTP 200, full fetch), IndiaMART VFD category (SERP + snippet), plus official-brand and price-list pages from live search results.

| Competitor | Verified page evidence | What it has that UdyogConnect lacks |
|---|---|---|
| **Moglix** (VFD category) | Brand-shopped Schneider listings with exact model series (ATV340U55N4E 5.5 kW ₹68,788; ATV310HU22N4E 2.2 kW ₹21,310; ATV320U06N4C ₹17,721), discount %, review counts (4.5–4.7 stars), add-to-cart | Model/SKU-level pages, brand navigation, ratings, transparent e-commerce pricing |
| **TradeIndia** (on-grid solar inverter) | 548 products, 11 city filters, brand+model named listings with per-listing spec grids (Input Voltage, Efficiency 97.5%, MOQ), INR prices, "Trusted/Premium Seller" badges, related-category cross-links | Listing spec grids, seller-trust badges, related-category hubs |
| **IndiaMART** (VFD / solar categories) | "1000+ products" VFD category; ₹8,000–₹35,000 VFD ranges; solar on-grid ₹15,032–₹1,67,940 | Listing volume, price-band filtering, buyer-lead network |
| **Official brands** (ABB, Schneider, Waaree shop) | Full product catalogs with datasheets; Waaree sells India-made inverters online | Authoritative spec content UC cannot outrank without differentiation (aggregation + price + city supply) |
| **Niche price-list sites** (solarcalculators.in, vfds.org) | 1 kW on-grid from ₹7,000; 5 kW ₹17,000–₹26,000 (ex-GST); VFD price tables by kW | Size/kW-anchored content that wins A5/A6 queries |

**Net gap:** UdyogConnect can only differentiate on *aggregated verified supplier count + city supply + enquiry funnel*, not on listing volume or e-commerce depth. Today it surfaces none of those differentiators in SERP-visible HTML.

## 5. 100-point quality framework and scored audit table

### 5.1 Framework weights

**Payload/metadata layer (64 pts, scored today):** supply & price depth 15, spec-in-payload 12, payload description quality 3, intent fit 4, seller signals 10, title/meta/canonical 8, schema correctness 3, internal links 4, conversion 3, trust 2.
**Content/SSR layer (36 pts, currently 0 for all 48 pages):** server-rendered content 12, on-page spec table 10, unique editorial copy 8, images & alt text 6.
Every product page scores **0/36 on the content layer** because the base page is client-rendered, so reported totals (35–64) are payload-layer scores only.

### 5.2 Scored audit table — all 48 products (payload layer /100)

| # | Slug | Category | Sellers | Price INR | Score /100 | Dominant gaps |
|---|------|----------|---------|-----------|-----------:|---------------|
| 1 | plc | Control | 21 | 5000–13000 | **64** | CSR-only base page; /product/ JSON-LD bug; 0-supplier city pages |
| 2 | vfd | Control | 14 | 5000–12000 | **64** | CSR-only base page; /product/ JSON-LD bug; 0-supplier city pages |
| 3 | industrial-meter | Panel Meters | 42 | 230–3742 | **58** | spec depth unverified; CSR-only base page; /product/ JSON-LD bug |
| 4 | led-flood-light | Lighting | 29 | 100–12000 | **58** | spec depth unverified; CSR-only base page; /product/ JSON-LD bug |
| 5 | mcpcb | Lighting | 24 | 1–77 | **58** | spec depth unverified; CSR-only base page; /product/ JSON-LD bug |
| 6 | crimping-tool | Panel Meters | 15 | 200–2900 | **58** | spec depth unverified; CSR-only base page |
| 7 | electrical-boxes | Electrical | 15 | 100–2300 | **58** | spec depth unverified; CSR-only base page |
| 8 | solar-fuse | Solar | 12 | 50–1200 | **58** | spec depth unverified; CSR-only base page |
| 9 | hmi | Control | 5 | 4000–7000 | **58** | CSR-only base page; /product/ JSON-LD bug |
| 10 | smsp | Control | 5 | 300–1000 | **58** | CSR-only base page; /product/ JSON-LD bug |
| 11 | industrial-switches | Panel Meters | 25 | 24–895 | **55** | 1 image; spec depth unverified; CSR-only base |
| 12 | led-panel | Lighting | 19 | 40–600 | **55** | 1 image; spec depth unverified; CSR-only base |
| 13 | solar-on-grid-inverter | Solar | 16 | 16500–275000 | **55** | 1 image; spec depth unverified; CSR-only base |
| 14 | dcdb | Solar | 13 | 400–45000 | **55** | 1 image; spec depth unverified; CSR-only base |
| 15 | energy-meter | Solar | 13 | 1000–25000 | **55** | 1 image; spec depth unverified; CSR-only base |
| 16 | surface-cleaner | Cleaning | 12 | 23–189 | **55** | 1 image; spec depth unverified; CSR-only base |
| 17 | acdb | Solar | 11 | 600–80000 | **55** | 1 image; spec depth unverified; CSR-only base |
| 18 | industrial-routers | Control | 4 | 2000–5000 | **53** | thin supply (4 sellers); CSR-only base |
| 19 | switchgear | Control | 4 | 2000–14999 | **53** | thin supply (4 sellers); CSR-only base |
| 20 | network-gateway | Control | 3 | 2449–3000 | **53** | thin supply (3 sellers); CSR-only base |
| 21 | led-bulbs | Lighting | 9 | 1–215 | **52** | spec depth unverified; CSR-only base |
| 22 | led-street-light | Lighting | 7 | 200–1220 | **52** | spec depth unverified; CSR-only base |
| 23 | led-strip-light | Lighting | 7 | 130–165 | **52** | spec depth unverified; CSR-only base |
| 24 | led-batten | Lighting | 6 | 34–148 | **52** | spec depth unverified; CSR-only base |
| 25 | cable-drums | Panel Meters | 9 | 2800–27500 | **49** | 1 image; spec depth unverified |
| 26 | solar-mcb | Solar | 9 | 270–650 | **49** | 1 image; spec depth unverified |
| 27 | cleaning-products | Cleaning | 8 | 29–190 | **49** | 1 image; spec depth unverified |
| 28 | solar-dc-cables | Solar | 7 | 16–82 | **49** | 1 image; spec depth unverified |
| 29 | safety-hand-gloves | Safety | 6 | 14–80 | **49** | 1 image; spec depth unverified |
| 30 | connectors-electrical | Panel Meters | 5 | 20–500 | **49** | 1 image; spec depth unverified |
| 31 | copper-bonded-rod | Solar | 5 | 380–8500 | **49** | 1 image; spec depth unverified |
| 32 | cable-lugs | Solar | 3 | 2–15 | **47** | thin supply (3 sellers) |
| 33 | dc-spd | Solar | 4 | 300–1000 | **44** | thin supply (4 sellers); 1 image |
| 34 | toilet-cleaner | Cleaning | 4 | 21–150 | **44** | thin supply (4 sellers); 1 image |
| 35 | connectors | Electrical | 3 | 20–600 | **44** | thin supply (3 sellers); 1 image |
| 36 | dishwash | Cleaning | 3 | 21–190 | **44** | thin supply (3 sellers); 1 image |
| 37 | safety-apron | Safety | 2 | 150–170 | **44** | thin supply (2 sellers); 1 image |
| 38 | din-rail-connectors | Panel Meters | 1 | 15–15 | **40** | single seller; no price spread |
| 39 | industrial-safety-leg-guard | Safety | 1 | 85–90 | **40** | single seller |
| 40 | laptop-stand | IT/Office | 1 | 230–250 | **40** | single seller |
| 41 | rechargeable-inverter-bulb | Lighting | 1 | 143–143 | **40** | single seller |
| 42 | surge-protection-device | Solar | 1 | 550–550 | **40** | single seller |
| 43 | industrial-nose-mask | Safety | 1 | 12–12 | **37** | single seller; 1 image |
| 44 | industrial-safety-helmet | Safety | 1 | 99–99 | **37** | single seller; 1 image |
| 45 | ms-square-bar | Metals | 1 | 1000–1000 | **37** | single seller; 1 image |
| 46 | raw-material | Metals | 1 | 1000–1000 | **37** | single seller; 1 image |
| 47 | ss302-circular-bar | Metals | 1 | 1000–1000 | **37** | single seller; 1 image |
| 48 | panel-fan | Panel Meters | 1 | 200–200 | **35** | single seller; **broken 9-char JSON-LD description** |

Range 35–64, median 52 (n=48, all payload-fetched, 0 errors). Slugs shown shortened; full slugs end in the category suffix shown in §1.

### 5.3 Structured-data defect detail (verified on 48/48 payloads)

- **Every one of the 48** Product JSON-LD and Breadcrumb JSON-LD blocks carries `url`/`id` on the **legacy singular** path `https://www.udyogconnect.in/product/{slug}` while the metadata canonical uses the plural `/products/{slug}`. Source: `backend/services/seo_service.py` (metadata canonical comes from `backend/server.py`). The indexed legacy `/product/connectors-…` URL in Google confirms the singular form has been fed to Google.
- `AggregateOffer` brand is the literal "Various Manufacturers" on 37/48 (seller names on 11) — not a recognized OEM brand signal.
- FAQPage JSON-LD is 4 templated questions, identical structure across all 48; variant pages contradict their own FAQ claims ("0 Verified Suppliers" in SSR vs "N verified suppliers" in FAQ).

## 6. Top-10 priority product pages and exact fixes

Chosen by score, seller depth and commercial value. Current title template: `Compare {X} Prices in India (2026) | UdyogConnect`.

| # | Product (sellers) | Proposed H1 | Exact missing content (SSR-invisible today) | Metadata/schema fixes |
|---|---|---|---|---|
| 1 | PLC (21) | `PLC Prices, Suppliers & Specifications in India (2026)` | Listing table (brands, series, price ₹5,000–13,000), 100+ word category intro, kW/I/O-point selection guidance | Fix ld_url singular→plural; brand from listings; 2nd image |
| 2 | VFD (14) | `VFD (Variable Frequency Drive) Prices & Verified Suppliers in India` | kW-band price table (0.75–22 kW), brand list (Schneider Altivar etc.), MOQ/lead time | Same as #1; add series anchors (ATV…) |
| 3 | Industrial meter (42) | `Industrial Meters — 42 Verified Suppliers, Prices & Specs` | Spec table (type, accuracy, voltage class), seller list | Fix ld_url; unique desc (157-char template now) |
| 4 | LED flood light (29) | `LED Flood Lights — Prices ₹100–₹12,000, 29 Verified Suppliers` | Wattage/lumen band table, IP ratings | Fix ld_url; add 2nd image + alts |
| 5 | MCPCB (24) | `MCPCB Lights — Prices, Sizes & Suppliers` | Board size/wattage specs; fix ₹1 min-price plausibility | Fix ld_url; dedupe desc |
| 6 | Crimping tool (15) | `Crimping Tools — Prices ₹225–₹2,900 & Suppliers` | Capacity (mm²), type (hydraulic/mechanical) specs | Fix ld_url; desc 288→ unique copy |
| 7 | Electrical boxes (15) | `Electrical Boxes — Prices ₹100–₹2,300 & Suppliers` | Material, size, IP rating specs | Fix ld_url |
| 8 | Solar fuse (12) | `Solar Fuses (DC) — Prices ₹50–₹1,200 & Suppliers` | Rating (A, kV DC), standards | Fix ld_url |
| 9 | HMI (5) | `HMI Panels — Prices, Sizes & Verified Suppliers` | Screen size, protocol, brand list | Fix ld_url; expand thin 5-seller supply copy |
| 10 | SMSP (5) | `SMSP Power Supplies — Prices & Verified Suppliers` | Wattage/output specs; clarify what SMSP means for buyers | Fix ld_url |

## 7. Prioritized implementation backlog (no files changed in this audit)

| ID | Pri | Item | Impact | Effort | Confidence | Evidence |
|---|---|---|---|---|---|---|
| B1 | P0 | **Server-render base product pages** — emit H1, top-listing table, price range, 80–120-word intro in raw HTML (components exist in `frontend/src/components/enterprise/` but are client-gated) | Very high | High | High | §2: 0 H1 / ≤76 words on 48/48 |
| B2 | P0 | **Fix JSON-LD singular `/product/` URLs** in `backend/services/seo_service.py` → `/products/`, matching metadata canonicals | High | Low | High | §5.3: 48/48 |
| B3 | P0 | **Sitemap pruning to real supply** — deploy the (already-coded, uncommitted) eligibility service; drop variant URLs without sellers; add missing base pages for variant-only slugs | High | Medium | High | §1: 62 real pairs vs 4,860 variant URLs |
| B4 | P0 | **Fix variant pages**: single H1, remove "0 Verified Suppliers" claims or gate the page, align FAQ schema with actual counts | High | Low–med | High | §2, §5.3 |
| B5 | P1 | **De-template descriptions** — unique 120–160-char meta + JSON-LD desc per product; fix panel-fan 9-char desc | Med–high | Low–med | High | §1, §5.2 #48 |
| B6 | P1 | **Surface brand & model/series at product level** (11 products already carry seller brands; control listings carry series like Altivar) | High | Medium | Medium | §3 A4, §4 Moglix |
| B7 | P1 | **Spec tables per product** from listing `searchableAttributes` (verify coverage on the 46 unverified products first) | High | Medium–high | Medium | §3 A5 |
| B8 | P1 | **Images**: add 2nd image on the 25 single-image products; descriptive alt text | Medium | Low | High | §1 |
| B9 | P1 | **Internal linking hubs** — category↔product cross-links beyond the 5 generated links; related-categories module like TradeIndia's | Medium | Medium | Medium | §4 TradeIndia |
| B10 | P2 | **Editorial/guide content** for A6 queries (buying guides per category) | Medium | High | Medium (hypothesis demand) | §3 A6 |
| B11 | P2 | **GSC integration** — pull query/impression/CTR data to validate A1–A6 priorities (owner must supply) | Gating | Low | n/a | Methodology |
| B12 | P2 | Review/rating & trust signals on listings (Moglix/TradeIndia both show them) | Medium | Medium | Medium | §4 |

Sequencing: B2 + B4 + B5 are low-effort/high-confidence and should ship first; B1 is the single biggest lever but needs a frontend architecture decision (this audit deliberately changed nothing).

## 8. Risks and items requiring owner confirmation

1. **Google Search Console data was not available** — all keyword demand is hypothesis until the owner supplies GSC query/impression exports (B11).
2. **Listing-level spec/brand coverage was verified only for sampled control-equipment and panel-fan listings**; the other 46 products' listing data depth is unverified (affects B6/B7 sizing).
3. **Supply behind the 33 variant-only slugs** (valves, office supplies, tools…) was not audited at listing level; their base pages return 200 live but are absent from the sitemap.
4. **The eligibility-filtering sitemap service exists uncommitted in the worktree and is not deployed** — shipping B3 requires a deployment decision.
5. **Apex→www 307 redirect** persists (owner-approved canonical is apex `https://udyogconnect.in`); correction is Vercel-side, outside this repository.
6. **Indexation probe was a sample, not a full audit** — one legacy `/product/` URL was observed indexed with a stale title; full coverage needs GSC.
7. **OEM brand usage** (ABB, Schneider, Altivar) in new content has trademark/policy implications — needs owner sign-off before B6/B7 content is written.
8. **Price freshness**: payload prices were live on 2026-11-18; any published price content needs a refresh cadence and seller-side accuracy control.
