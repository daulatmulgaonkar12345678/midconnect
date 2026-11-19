# UdyogConnect — Product SEO Implementation: First Priority Batch (Implementation Proposal)

**Date:** 2026-11-18
**Status:** PROPOSAL ONLY — no source files modified, nothing staged or committed, `.exvisit` untouched.
**Basis:** `UdyogConnect_Product_SEO_Audit_2026-11-18.md` (accepted) + fresh live evidence fetched for this proposal on 2026-11-18, 16:46–17:05 UTC (enterprise listing payloads for all 10 products, live redirect probe, live SSR HTML of the VFD base page). Audit-day SEO payloads (all 48 products, fetched 2026-11-18) reused as verified baseline.
**Canonical domain (owner-approved):** `https://udyogconnect.in`. Live production still serves via `www`; all "current/live" values below reflect the deployed `www` state. The uncommitted worktree already carries the P1 apex alignment (frontend + backend), so **production currently lags the worktree** — deployment of the existing uncommitted work is a prerequisite for any batch-1 change that emits absolute URLs.

---

## 1. Selected products and why (Step 1)

Selected exactly from the audit's §6 top-10 priority table (ranked by payload score, seller depth and commercial value; audit §5.2/§6). All ten slugs, seller counts and price ranges below are re-verified today from the live SEO payload.

| Rank | Product (page name) | Canonical slug | Sellers | Price range (INR, payload) | Audit score | Why selected |
|---|---|---|---:|---|---:|---|
| 1 | PLC | `plc-vfd-plc-hmi-control-equipments-supplier-india` | 21 | 5,000–13,000 | 64 | Highest score; deepest control-equipment supply; verified brand/series data (Delta DVP, Schneider Modicon) enables model-level content |
| 2 | VFD | `vfd-vfd-plc-hmi-control-equipments-supplier-india` | 14 | 5,000–12,000 | 64 | High-intent price/spec queries ("vfd price in india"); richest listing attributes (kW, IP, series incl. Schneider Altivar) |
| 3 | Industrial Meter | `industrial-meter-panel-meters-and-accessories-supplier-india` | 42 | 230–3,742 | 58 | Largest seller count on the site; price-led intent; real brand data (HTC, SELEC, Fluke…) |
| 4 | LED Flood Light | `led-flood-light-lights-lighting-accessories-supplier-india` | 29 | 100–12,000 | 58 | High-volume lighting category; wattage bands verified in listings; two seller cities |
| 5 | MCPCB | `mcpcb-lights-lighting-accessories-supplier-india` | 24 | 1–77 | 58 | Strong supply (24 sellers, all manufacturers); niche intent competitors are weak; ₹1 minimum price needs plausibility fix before publication |
| 6 | Crimping Tool | `crimping-tool-panel-meters-and-accessories-supplier-india` | 15 | 200–2,900 | 58 | Tooling intent; multiple real brands (Ideal, Kosmos…); contains a title/price inconsistency to fix |
| 7 | Electrical Boxes | `electrical-boxes-electrical-equipment-supplies-supplier-india` | 15 | 100–2,300 | 58 | Spec-rich listings (IP rating, material, dimensions) verified today; two seller cities |
| 8 | Solar Fuse | `solar-fuse-solar-equipment-panels-supplier-india` | 12 | 50–1,200 | 58 | Solar cluster; genuine OEM brands (Mersen, Havells, Finder); DC voltage data verified |
| 9 | HMI | `hmi-vfd-plc-hmi-control-equipments-supplier-india` | 5 | 4,000–7,000 | 58 | Completes the control-equipment cluster; uniform verified spec data (Delta, 4.3"/7" HMI) |
| 10 | SMSP | `smsp-vfd-plc-hmi-control-equipments-supplier-india` | 5 | 300–1,000 | 58 | Completes control cluster; **page name "SMSP" itself needs owner confirmation (likely SMPS)** |

Not selected this batch: `industrial-switches` (25 sellers), `led-panel` (19), `solar-on-grid-inverter` (16), `dcdb`, `energy-meter`, `surface-cleaner`, `acdb` — audit §5.2 rows 11–17. They are the natural batch 2 once the content/SSR pattern is proven on these ten.

### Batch-level verified facts (today, all 10 products)

- **Seller supply:** every top-10 product has real listings; 8 of 10 sellers concentrated in **one city** (PLC/VFD/HMI/SMSP/electrical-boxes → Noida; industrial-meter/crimping-tool → Pune; MCPCB → New Delhi), LED flood light (Delhi+Mumbai), electrical boxes (Noida+Surat), solar fuse (Ahmedabad+Pune). Only these cities may be claimed or linked on any new content.
- **Availability:** all fetched listings for all ten products show `in_stock` with **MOQ 1** and lead times of 1 day (electrical boxes 1–3 days; LED flood 1/5 days; HMI 1/11 days). This is the evidence base for "InStock" schema claims — it must be re-verified at publish time (see §8 risk).
- **Listing images:** every listing carries up to 2 images (Cloudinary/Firebase-hosted); **zero product-level images** in the enterprise payload. The 1–2 images per product in Product JSON-LD come from listing images.
- **Brand coverage:** real brands exist at listing level for 9 of 10 products (electrical-boxes listings carry no brand value). Today the Product JSON-LD brand is the literal placeholder **"Various Manufacturers"** on all ten.
- **Rendering:** live re-verification today — raw HTML of `/products/vfd-…` contains **0 H1**, title `Compare VFD Prices in India (2026) | UdyogConnect`, and 4 JSON-LD blocks (Product, BreadcrumbList, FAQPage, Organization) that **are** server-rendered from the backend SEO payload.

---

## 2. Per-product current vs recommended content (Steps 1–2)

Legend: all "current" values verified live/payload 2026-11-18. Recommendations use only verified data; anything else is flagged **[OWNER/SUPPLIER CONFIRMATION]**. Listings' attribute values are reproduced as currently listed by sellers — a supplier re-check is required before publication (§8).

---

### P1 — PLC

**Identity (verified):**
- Canonical URL (live): `https://www.udyogconnect.in/products/plc-vfd-plc-hmi-control-equipments-supplier-india` (worktree policy: apex, no www)
- JSON-LD Product `url` (live): `https://www.udyogconnect.in/product/plc-vfd-plc-hmi-control-equipments-supplier-india` — **singular `/product/`, mismatched with canonical**
- Manufacturer/model at product level: none ("Various Manufacturers"). Listing-level brands: **Delta (17), Schneider (3)** of 20 listings fetched.
- Current title: `Top PLC Prices in India (2026) | UdyogConnect`
- Current meta: `PLC suppliers in India. Compare verified manufacturers, dealers & distributors on UdyogConnect. Get best deals today. Bulk orders welcome. Free RFQ.`
- Current SSR: 0 H1, "Loading product…" shell (74 words), specs/prices/sellers client-rendered only
- Images: 2 in JSON-LD (listing-sourced); sellers: 21; price ₹5,000–₹13,000; MOQ 1; cities: Noida; FAQ: 4 templated; internal links: 5 (category/similar/city)

**Verified data available:** Delta DVP series — DVP-S Series (4), DVP ES2 (3), DVP EX2 (2), DVP SV2, DVP SM2, DVP TC, DVP AD (1 each); Schneider **Modicon M241** (2). Controller types: Compact (18), Modular (1), Extension Module (1). Ports: 4–60. Programming software: WPLSoft/ISPSoft (16), EcoStruxure (3). Supply: 24 V DC (13), 12 V DC (2), 1-phase AC (5). Mounting: DIN rail/panel (20). Condition: New (20). Seller: United Control Engineers India Private Limited (distributor, Noida); all in stock, lead 1 day.

**Recommended content:**
- **SEO title:** `PLC Prices in India (2026): ₹5,000–₹13,000 from 21 Suppliers`
- **H1:** `PLC Prices, Suppliers & Specifications in India (2026)` *(audit §6 recommendation, unchanged)*
- **Meta description:** `Compare PLC prices in India (2026) — ₹5,000–₹13,000 from 21 verified suppliers. Delta DVP & Schneider Modicon M241 series, MOQ from 1. Send a free RFQ.`
- **Introduction (~110 words, SSR):** "A programmable logic controller (PLC) is the core control device of machine and panel automation: it reads sensor inputs, executes the control program and drives outputs. On UdyogConnect you can compare 21 verified PLC listings from Indian suppliers in one place. Current listings span compact controllers such as the Delta DVP series (DVP-S, DVP-ES2, DVP-EX2, DVP-SV2, DVP-SM2, DVP-TC, DVP-AD) and Schneider Electric's Modicon M241, with supply voltages of 24 V DC, 12 V DC or single-phase AC and DIN-rail or panel mounting. Prices currently range from ₹5,000 to ₹13,000 with a minimum order quantity of 1 unit. Every listing shows the seller, city, stock status and enquiry options, so you can request quotes and confirm programming-software compatibility (WPLSoft/ISPSoft or EcoStruxure) before ordering."
- **Specifications table (from current listings — supplier re-check before publish):** Brand (Delta/Schneider) · Series (DVP-S/ES2/EX2/SV2/SM2/TC/AD; Modicon M241) · Controller type (Compact/Modular/Extension) · I/O ports (4–60) · Supply (24 V DC / 12 V DC / 1-ph AC) · Mounting (DIN rail / panel) · Programming software · Condition (New)
- **Applications & use cases:** machine control panels, production-line automation, process control retrofit, training/lab systems — *category-level framing only; seller-specific claims need supplier confirmation.*
- **Model/variant information:** present as series chips (verified above); link each named series to the seller listing offering it. No product-level SKU exists — keep model data at listing level. **[OWNER CONFIRMATION: allow OEM brand/series names on aggregation pages]**
- **FAQs (draft, all answers from verified data):**
  1. *What is the PLC price range in India on UdyogConnect?* — Current listings range ₹5,000–₹13,000; individual quotes depend on model and quantity.
  2. *Which PLC brands are available?* — Current verified listings include Delta (DVP series) and Schneider (Modicon M241).
  3. *What is the minimum order quantity?* — All current listings have MOQ 1.
  4. *Do suppliers stock PLCs?* — All current listings show in-stock status; re-confirm lead time with the seller when enquiring.
  5. *Which programming software do these PLCs use?* — Listings state WPLSoft/ISPSoft (Delta) or EcoStruxure (Schneider); confirm the exact version with the supplier.
- **Related products (same cluster, all in the verified 48-product inventory):** VFD, HMI, SMSP, industrial routers, network gateway, switchgear.
- **Manufacturer information:** UdyogConnect is a marketplace, not the manufacturer. State: "PLC products listed by verified Indian suppliers; OEM brands Delta and Schneider Electric appear on current listings." **[OWNER CONFIRMATION: OEM-name usage policy]**
- **Seller & enquiry information:** United Control Engineers India Private Limited — distributor, Noida (UP); 21 total listings on page; in stock; MOQ 1; lead time 1 day (as listed); RFQ/enquiry via page CTA, WhatsApp +91 73878 21042 (site-level contact, verified).

**Missing / requires owner or supplier confirmation:** product-level hero image (none exists — JSON-LD reuses listing photos); supplier authorization status for Delta/Schneider; price freshness cadence; per-series prices.

---

### P2 — VFD

**Identity (verified):**
- Canonical URL (live): `https://www.udyogconnect.in/products/vfd-vfd-plc-hmi-control-equipments-supplier-india`
- JSON-LD Product `url` (live): `https://www.udyogconnect.in/product/vfd-…` — **singular mismatch (live-verified today, exact block parsed)**
- Current title: `Compare VFD Prices in India (2026) | UdyogConnect`
- Current meta: `VFD suppliers in India. Compare verified manufacturers, dealers & distributors on UdyogConnect. Get best deals today. Bulk orders welcome. Free RFQ.`
- Current SSR: 0 H1, CSR-only content. Images: 2 (JSON-LD). Sellers: 14. Price ₹5,000–₹12,000. MOQ 1. Cities: Noida. FAQ: 4 templated.

**Verified data available:** Brands: **Schneider Electric (10), Delta Electronics (3)** of 14. Series: Altivar Process ATV630 (3), Easy Altivar 310 (3), Altivar Machine ATV320, ATV320, Altivar Process ATV930, Altivar Machine ATV340, Delta ME300/MS300/MH300, VFD-EL. IP20 on all 14. Input: three-phase (11), single-phase (2). Motor power as listed: 0.5–5 (kW presumed; units not stated in attributes — **flag below**). Supply voltage as listed: ~413–415 V (3-ph), ~229 V (1-ph). Application: motor handling (13), textile (1). Seller: United Control Engineers India Private Limited (distributor, Noida); in stock; lead 1 day.

**Recommended content:**
- **SEO title:** `VFD Price in India (2026): ₹5,000–₹12,000 from 14 Suppliers`
- **H1:** `VFD (Variable Frequency Drive) Prices & Verified Suppliers in India` *(audit §6)*
- **Meta description:** `Compare VFD prices in India (2026) — ₹5,000–₹12,000 from 14 verified suppliers. Schneider Altivar & Delta series, IP20, MOQ 1. Get quotes on UdyogConnect.`
- **Introduction (~110 words, SSR):** "A variable frequency drive (VFD, also called an AC drive or inverter drive) controls an electric motor's speed and torque by varying the supply frequency — cutting energy use in fans, pumps and conveyors and enabling soft starts. UdyogConnect lists 14 verified VFD suppliers in one comparison view. Current listings include Schneider Electric Altivar drives (Altivar Process ATV630/ATV930, Altivar Machine ATV320/ATV340, Easy Altivar 310) and Delta Electronics drives (ME300/MS300/MH300, VFD-EL), rated IP20, in three-phase and single-phase input versions. Listed motor power spans 0.5 to 5 (unit as listed), and prices range from ₹5,000 to ₹12,000 with MOQ 1. Each listing names its seller, city, stock status and lead time, so you can shortlist by series and request exact quotes."
- **Specifications table (verified attributes):** Brand (Schneider Electric/Delta) · Series (per listing) · IP rating (IP20) · Input phase (3-ph/1-ph) · Motor power (as listed 0.5–5) · Supply voltage (~415 V 3-ph / 230 V 1-ph as listed) · Application (motor handling/textile)
- **Applications & use cases:** pump/fan speed control, conveyor and machine drives, textile machinery (verified listing attribute), HVAC retrofits — beyond the two verified attributes, keep category-level. kW-band table (audit A5): build from listed motor-power values only.
- **Model/variant information:** series chips with seller links (Altivar ATV630/ATV930/ATV320/ATV340/Easy 310; Delta ME300/MS300/MH300/VFD-EL). These are the site's only model-level anchors today — highest-value addition for "altivar price" type queries (audit §3 A4).
- **FAQs:** 1. Price range (₹5,000–₹12,000). 2. Brands (Schneider Electric, Delta Electronics). 3. MOQ (1). 4. IP rating (IP20 across current listings). 5. Single-phase input available? (Yes — 2 of 14 current listings.)
- **Related products:** PLC, HMI, SMSP, switchgear, industrial routers (same verified cluster).
- **Manufacturer information:** marketplace positioning + OEM brand statement as P1. **[OWNER CONFIRMATION: Altivar/Modicon trademark usage]**
- **Seller & enquiry information:** United Control Engineers India Private Limited, distributor, Noida; 14 listings; in stock; MOQ 1; lead 1 day; RFQ CTA + site WhatsApp.

**Missing / requires confirmation:** motor-power units ("5" — kW? HP?) **[SUPPLIER]**; one anomalous `motor_power: 425` value must be excluded pending verification **[SUPPLIER]**; per-series pricing; second city supply (none today).

### P3 — Industrial Meter

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/industrial-meter-panel-meters-and-accessories-supplier-india`
- JSON-LD `url` (live): `…/product/industrial-meter-…` — singular mismatch
- Current title: `Top Industrial Meter Prices (2026) | From ₹230.00 | UdyogConnect`
- Current meta: `Industrial Meter suppliers in India. Prices start from ₹230.00. Compare verified manufacturers, dealers & distributors on UdyogConnect. Get best deals today.` (157 chars — the audit's "de-template descriptions" target)
- Current SSR: 0 H1, CSR-only. Images: 2. Sellers: **42** (largest on site). Price ₹230–₹3,742. MOQ 1. City: Pune (only). FAQ: 4 templated.

**Verified data (20 of 42 listings fetched):** Brands: SELEC (5), HTC (4), Yokogawa [listed "Yokogaw"] (3), Fuji, Mextech, Fluke, Multi-Stem, none (3). Meter types: Multimeter (5), clamp meter (4), Timer (3), Temperature meter (3), Ammeter (2), Voltmeter (1)… Accuracy: 0.5% FS (14), 0.3% FS (2). Control: On-Off (17), PID/On-Off (1). Inputs: Universal (7), Current (4), RTD (2), J/K thermocouple, TC. Display: digital (12), analog (4). Voltage as listed: 220/230/240/1000/1100. Sellers: Adinath Electricals, Maharani Sales Corporation (distributors, Pune); in stock; lead 1 day.

**Recommended content:**
- **SEO title:** `Industrial Meter Prices (2026): ₹230–₹3,742 from 42 Suppliers`
- **H1:** `Industrial Meters — 42 Verified Suppliers, Prices & Specs` *(audit §6)*
- **Meta description:** `Compare industrial meter prices (2026) — ₹230–₹3,742 from 42 verified suppliers in India. Multimeters, clamp & temperature meters, 0.5% FS accuracy. RFQ free.`
- **Introduction (~110 words, SSR):** "Industrial meters cover the measurement and control instruments used on panels and production lines: digital multimeters, clamp meters, ammeters, voltmeters, timers and temperature meters. UdyogConnect aggregates 42 verified listings — the deepest single-product supply on the platform. Current listings include SELEC, HTC, Yokogawa, Fuji, Mextech and Fluke instruments, most with 0.5% FS accuracy and On-Off or PID/On-Off control, accepting universal, current, RTD or thermocouple inputs with digital or analog displays. Prices start at ₹230 and reach ₹3,742 with MOQ 1. Suppliers are Pune-based distributors with in-stock listings, so buyers can compare instruments side by side and request exact quotes with one enquiry."
- **Specifications table:** Brand · Meter type (multimeter/clamp/ammeter/voltmeter/timer/temperature) · Accuracy (0.3–0.5% FS as listed) · Control (On-Off/PID) · Input (universal/current/RTD/TC) · Display (digital/analog) · Voltage class (as listed)
- **Applications & use cases:** panel instrumentation, maintenance/testing kits, temperature control loops — category-level only.
- **Model/variant information:** type-level segmentation (multimeter/clamp/timer/temperature/ammeter/voltmeter) verified; no SKUs at product level.
- **FAQs:** price range; brands available (SELEC, HTC, Yokogawa, Fluke…); accuracy (0.5% FS typical); MOQ (1); supplier city (Pune — is that acceptable for dispatch? **[OWNER/SUPPLIER: pan-India shipping confirmation]**).
- **Related products:** crimping tool, connectors-electrical, cable drums, DIN-rail connectors (verified inventory, same panel-adjacent intent); energy meter (solar category).
- **Manufacturer information:** marketplace + listed OEM brands statement.
- **Seller & enquiry information:** Adinath Electricals; Maharani Sales Corporation — distributors, Pune; 42 listings; in stock; MOQ 1; lead 1 day; RFQ + WhatsApp.

**Missing / requires confirmation:** "Yokogaw" spelling in listing data (likely Yokogawa) **[SUPPLIER]**; meter_type values cover ~16/20 fetched listings — remaining listings need attribute coverage; per-type price bands.

---

### P4 — LED Flood Light

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/led-flood-light-lights-lighting-accessories-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Top Led Flood Light Prices in India (2026) | UdyogConnect`. Current meta: templated "Led Flood Light suppliers in India. …Bulk orders welcome." SSR: 0 H1, CSR-only. Images: 2. Sellers: 29. Price ₹100–₹12,000. MOQ 1. Cities: New Delhi (+1 Mumbai). FAQ: 4 templated.

**Verified data (20 listings fetched):** Brands: other/none (12), Be Electronics (4), BPL (3). Body: ABS (9), Aluminium (5), Die-Cast Aluminium (5). Rated power as listed: 5, 6, 13, 15, 30, 50 (W presumed — unit not stated **[SUPPLIER]**). Shape: Rectangular (12), Round (5), Square (3). Colour: Cool White (13), Warm White (2). Mounting: surface (1). Sellers: Sunkip Lighting India Private Limited, Bhagwati Lighting Industries (manufacturers, New Delhi/Mumbai); in stock; lead 1–5 days.

**Recommended content:**
- **SEO title:** `LED Flood Light Price in India (2026): ₹100–₹12,000 | 29 Suppliers`
- **H1:** `LED Flood Lights — Prices ₹100–₹12,000, 29 Verified Suppliers` *(audit §6)*
- **Meta description:** `Compare LED flood light prices in India (2026) — ₹100–₹12,000 from 29 verified suppliers. 5–50 W aluminium & die-cast bodies, cool/warm white. Free RFQ.`
- **Introduction (~105 words, SSR):** "LED flood lights deliver wide-angle outdoor and industrial illumination for facades, yards, sports areas and signage, replacing halogen fittings at a fraction of the power draw. UdyogConnect lists 29 verified suppliers in one comparison. Current listings include Be Electronics and BPL models alongside unbranded manufacturer listings from Sunkip Lighting and Bhagwati Lighting Industries, with aluminium, ABS and die-cast aluminium bodies in rectangular, round and square shapes, mostly cool white. Listed wattages span 5 W to 50 W, and prices range from ₹100 to ₹12,000 with MOQ 1. Filter by wattage, body material or shape, then contact sellers directly for quantity pricing."
- **Specifications table:** Brand · Wattage (5–50 as listed) · Body material (ABS/Aluminium/Die-cast) · Shape · Light colour (cool/warm) · Mounting
- **Applications:** façade/yard lighting, signage, construction sites, sports grounds — category-level.
- **Model/variants:** wattage bands (5/6/13/15/30/50 W) as filter anchors — audit A5.
- **FAQs:** price range; wattage options; body materials; brands (Be Electronics, BPL); MOQ; dispatch cities (Delhi/Mumbai).
- **Related products:** MCPCB, LED panel, LED street light, LED bulbs, LED batten, LED strip (verified lighting inventory).
- **Manufacturer info:** marketplace + manufacturer-seller statement (both named sellers are listed as manufacturers).
- **Seller & enquiry:** Sunkip Lighting India Pvt Ltd, Bhagwati Lighting Industries — manufacturers, New Delhi/Mumbai; 29 listings; in stock; MOQ 1; lead 1–5 days; RFQ + WhatsApp.

**Missing / requires confirmation:** wattage units **[SUPPLIER]**; brand "other" values (unbranded listings — present honestly as unbranded); lumen output/IP ratings not in listing data — do not publish until supplied.

---

### P5 — MCPCB

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/mcpcb-lights-lighting-accessories-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Top MCPCB Prices in India (2026) | UdyogConnect`. Current meta: templated. SSR: 0 H1, CSR-only. Images: 2. Sellers: 24. Price ₹1–₹77. MOQ 1. City: New Delhi. FAQ: 4 templated.

**Verified data (20 listings):** Seller: Bhagwati Lighting Industries (manufacturer, New Delhi) — 20 listings. Brands: "other"/none only — **no real brand names in data; do not invent any.** Body: Aluminium (16), ABS (4). Rated power: 0.5, 2, 3, 5, 9, 12. Shape: Round (16), Square (3), Oval (1). Colour: Cool White (6), 3-in-1 CCT (6), Warm White (2), Natural/Neutral White. In stock; lead 1 day.

**Recommended content:**
- **SEO title:** `MCPCB LED Prices in India (2026): ₹1–₹77 from 24 Suppliers`
- **H1:** `MCPCB Lights — Prices, Sizes & Suppliers` *(audit §6)*
- **Meta description:** `Compare MCPCB (metal-core PCB) LED board prices in India (2026) — ₹1–₹77 from 24 suppliers. Aluminium round boards, 0.5–12 W, cool to warm white. RFQ free.`
- **Introduction (~100 words, SSR):** "An MCPCB (metal-core printed circuit board) is the aluminium substrate that LED chips are mounted on — it spreads heat away from the diodes and is the base component of most LED bulbs and panels. UdyogConnect aggregates 24 MCPCB listings, all from Bhagwati Lighting Industries, a New Delhi manufacturer. Current boards are round, square or oval, in aluminium or ABS bodies, rated from 0.5 W to 12 W, in cool white, warm white, natural white or 3-in-1 CCT. Prices run from ₹1 to ₹77 with MOQ 1. Confirm board diameter, LED type and quantity directly with the manufacturer before ordering."
- **Specifications:** Body (Aluminium/ABS) · Power (0.5–12 W as listed) · Shape (Round/Square/Oval) · Colour (Cool/Warm/Natural/3-in-1 CCT)
- **Applications:** LED bulb/panel/luminaire manufacturing, PCB assembly, repair & retrofit — category-level.
- **FAQs:** price range; shapes/sizes available; power ratings; single-source supply (yes — one manufacturer, 24 listings); MOQ.
- **Related products:** LED flood light, LED panel, LED bulbs, LED batten (verified).
- **Manufacturer info:** Bhagwati Lighting Industries (manufacturer, New Delhi) — supplier role verified.
- **Seller & enquiry:** as above; RFQ + WhatsApp; board diameter/LED-chip type not in listing data — enquire.

**Missing / requires confirmation:** board diameter (mm), LED chip type, thermal data — not in listings **[SUPPLIER]**; the ₹1 minimum price is real listing data but looks implausible for a finished board — **[SUPPLIER: verify it is a genuine unit price, not a data-entry error] before any price-led content publishes**.

### P6 — Crimping Tool

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/crimping-tool-panel-meters-and-accessories-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Best Crimping Tool Prices (2026) | From ₹225.00 | UdyogConnect` — **inconsistency: the title claims ₹225 but the payload minimum is ₹200 (and the JSON-LD lowPrice is 200). Fix the title or re-verify the floor.**
- Current meta: templated (288 chars). SSR: 0 H1, CSR-only. Images: 2. Sellers: 15. Price ₹200–₹2,900. MOQ 1. City: Pune. FAQ: 4 templated.

**Verified data (15 listings — all):** Brands: Ideal (7), Kosmos (3), Stackfine, PowerGrip, Roly-Tray, SIBASS, none. Material: Stainless Steel (6), Metal (6), Carbon Steel (1). Type: Cable (3), Service (2). Crimping capacity as listed: 0 (2), 6 (2) — **zeros are placeholder values, exclude [SUPPLIER]**. Length: 7–12. Warranty: 6 (1 listing). Sellers: Maharani Sales Corporation, Adinath Electricals (distributors, Pune); in stock; lead 1 day.

**Recommended content:**
- **SEO title:** `Crimping Tool Prices in India (2026): ₹200–₹2,900 | 15 Suppliers`
- **H1:** `Crimping Tools — Prices ₹200–₹2,900 & Suppliers` *(audit §6, corrected to the verified ₹200 floor)*
- **Meta description:** `Compare crimping tool prices in India (2026) — ₹200–₹2,900 from 15 verified suppliers. Ideal, Kosmos & more; steel and carbon-steel builds. Free RFQ.`
- **Introduction (~100 words, SSR):** "A crimping tool terminates cable lugs and ferrules by compressing the connector onto the conductor — the standard method for electrical panel wiring and solar DC terminations. UdyogConnect lists 15 verified crimping-tool suppliers, all Pune-based distributors such as Maharani Sales Corporation and Adinath Electricals. Current listings include Ideal, Kosmos, Stackfine, PowerGrip, Roly-Tray and SIBASS tools in stainless-steel, carbon-steel and general metal builds, with cable-crimping and service-tool types and lengths of roughly 7–12 inches. Prices span ₹200 to ₹2,900 with MOQ 1. Compare listings by brand and material, then request the exact crimping-capacity and jaw details when enquiring."
- **Specifications:** Brand (Ideal/Kosmos/…) · Type (Cable/Service) · Material (SS/Carbon steel/Metal) · Length (7–12) · Warranty (where stated)
- **Applications:** panel wiring, solar DC lugs, automotive/battery terminations — category-level; capacity data must come from suppliers.
- **FAQs:** price range; brands; material options; MOQ; capacity on request (values not reliably listed).
- **Related products:** industrial meter, connectors-electrical, cable lugs (verified solar), DIN-rail connectors.
- **Manufacturer/seller info:** distributors, Pune; RFQ + WhatsApp.

**Missing / requires confirmation:** crimping-capacity (mm²) and force values — current listing data contains zeros **[SUPPLIER]**; the ₹225 title vs ₹200 payload mismatch **[OWNER]**.

---

### P7 — Electrical Boxes

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/electrical-boxes-electrical-equipment-supplies-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Compare Electrical Boxes Prices in India (2026) | UdyogConnect`. Meta templated. SSR: 0 H1. Images: 2. Sellers: 15. Price ₹100–₹2,300. MOQ 1–100. Cities: Noida + Surat. FAQ: 4 templated.

**Verified data (15 listings):** Brands: none in data — **do not invent.** Door: single (14), double (1). Material: Mild Steel (12), ABS (2), FRP. IP rating as listed: 65 (2), 66 (9), 63 (1), 55 (2) — attribute key is misspelled `ip_ratong` in the data model **[backend data fix, no content impact]**. Dimensions: L 180–500, W 80–500, H 90–210. Mounting: wall (13), floor-standing (2). Finish: powder-coated (4). Seller: United Control Engineers India Pvt Ltd (distributor, Noida) + 1 Surat seller; in stock; lead 1–3 days.

**Recommended content:**
- **SEO title:** `Electrical Boxes Prices in India (2026): ₹100–₹2,300 | 15 Suppliers`
- **H1:** `Electrical Boxes — Prices ₹100–₹2,300 & Suppliers` *(audit §6)*
- **Meta description:** `Compare electrical box prices (2026) — ₹100–₹2,300 from 15 verified suppliers. IP65/IP66 mild-steel enclosures, wall & floor mount. Free RFQ on UdyogConnect.`
- **Introduction (~100 words, SSR):** "Electrical boxes and enclosures house switches, terminals and control gear, protecting them from dust, water and mechanical damage. UdyogConnect aggregates 15 verified listings from Noida and Surat suppliers. Current enclosures are mostly mild-steel with single doors, powder-coated where stated, rated IP55 to IP66, in wall-mount and floor-standing formats with body sizes from roughly 180×80×90 mm up to 500×500×210 mm as listed; ABS and FRP bodies are also listed. Prices run from ₹100 to ₹2,300, with MOQs from 1 to 100 units depending on the listing. Compare size, material and IP rating, then confirm the exact cut-out and gland requirements with the supplier."
- **Specifications:** Material (MS/ABS/FRP) · Door (single/double) · IP rating (55–66 as listed) · L×W×H ranges · Mounting (wall/floor) · Finish (powder-coated)
- **Applications:** control panels, junction/protection enclosures, outdoor equipment housing — category-level.
- **FAQs:** price range; IP ratings available; materials; size options; MOQ range (1–100); dispatch cities (Noida/Surat).
- **Related products:** connectors, connectors-electrical, industrial meter, switchgear (verified).
- **Seller info:** United Control Engineers India Pvt Ltd (Noida) + Surat supplier; RFQ + WhatsApp.

**Missing / requires confirmation:** brand names (absent); gland/knockout details; data-key typo `ip_ratong` noted for backend cleanup.

---

### P8 — Solar Fuse

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/solar-fuse-solar-equipment-panels-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Top Solar Fuse Prices in India (2026) | UdyogConnect`. Meta templated (145 chars). SSR: 0 H1. Images: 2. Sellers: 12. Price ₹50–₹1,200. MOQ 1. Cities: Ahmedabad + Pune. FAQ: 4 templated.

**Verified data (12 listings — all):** Brands: **Mersen (6), Finder (3), Havells (2), Schutz (1)**. Rated voltage as listed: 1000 V DC (7), 1500 V (1), 600 V (1), 320/220 V. Rated current as listed: 1–50 A. Poles: 2 (2), 3 (3), 4 (2). Sellers: Matrix Green Enterprise Private Limited, Vidya Enterpeises [sic] (distributors, Ahmedabad + 1 Pune); in stock; lead 1 day.

**Recommended content:**
- **SEO title:** `Solar Fuse (DC) Prices in India (2026): ₹50–₹1,200 | 12 Suppliers`
- **H1:** `Solar Fuses (DC) — Prices ₹50–₹1,200 & Suppliers` *(audit §6)*
- **Meta description:** `Compare solar DC fuse prices (2026) — ₹50–₹1,200 from 12 verified suppliers. Mersen, Finder & Havells 1000–1500 V DC fuse links, MOQ 1. Free RFQ.`
- **Introduction (~100 words, SSR):** "Solar fuses protect photovoltaic strings, combiner boxes and inverters from overcurrent on the DC side, where arcs persist far longer than in AC circuits. UdyogConnect lists 12 verified solar-fuse suppliers, led by Ahmedabad distributors Matrix Green Enterprise and Vidya Enterprises. Current fuse links are from Mersen, Finder, Havells and Schutz, rated from roughly 1 A to 50 A and from 220 V up to 1000 V DC (one 1500 V listing), in 2-, 3- and 4-pole formats. Prices span ₹50 to ₹1,200 with MOQ 1. Match the fuse rating to your string current and system voltage, then confirm standards compliance with the supplier."
- **Specifications:** Brand (Mersen/Finder/Havells/Schutz) · Rated current (1–50 A as listed) · Rated voltage (220–1500 V; 1000 V DC typical) · Poles (2/3/4)
- **Applications:** string protection, combiner boxes, inverter DC input protection — category-level.
- **FAQs:** price range; brands; voltage ratings (1000 V DC typical); current range; MOQ; standards/certification **[SUPPLIER]**.
- **Related products:** solar MCB, DC SPD, ACDB, DCDB, solar DC cables, copper-bonded rod (verified solar cluster).
- **Seller info:** Matrix Green Enterprise Pvt Ltd; Vidya Enterpeises (name as listed — spelling to confirm **[OWNER/SUPPLIER]**); RFQ + WhatsApp.

**Missing / requires confirmation:** standards compliance (IS/IEC/UL) and breaking capacity — not in listing data **[SUPPLIER]**; seller name spelling.

### P9 — HMI

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/hmi-vfd-plc-hmi-control-equipments-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Best HMI Prices in India (2026) | UdyogConnect`. Meta templated. SSR: 0 H1. Images: 2. Sellers: 5. Price ₹4,000–₹7,000. MOQ 1. City: Noida. FAQ: 4 templated.

**Verified data (5 listings — all):** Brand: **Delta (5/5)**. Display size: 4.3" (2), 7" (3). Display type: LCD (4), Monochrome (1). Communication: RS-485 (4), port types Serial (2)/Ethernet (1). Touch: True (3), False (2). Seller: United Control Engineers India Pvt Ltd (distributor, Noida); in stock; lead 1–11 days.

**Recommended content:**
- **SEO title:** `HMI Panel Prices in India (2026): ₹4,000–₹7,000 from 5 Suppliers`
- **H1:** `HMI Panels — Prices, Sizes & Verified Suppliers` *(audit §6)*
- **Meta description:** `Compare HMI panel prices in India (2026) — ₹4,000–₹7,000 from 5 verified suppliers. Delta 4.3" & 7" LCD touch panels with RS-485/Ethernet. Free RFQ.`
- **Introduction (~95 words, SSR):** "A human-machine interface (HMI) panel is the touchscreen or button panel operators use to monitor and control a machine or process — displaying alarms, setpoints and trends and issuing commands to the PLC. UdyogConnect lists 5 verified HMI suppliers in one view. Current listings are all Delta Electronics panels: 4.3-inch and 7-inch displays, LCD or monochrome, with RS-485 serial and Ethernet ports and touch or non-touch formats. Prices range from ₹4,000 to ₹7,000 with MOQ 1. Compare display size and interface, then confirm software compatibility and delivery with the supplier."
- **Specifications:** Brand (Delta) · Display size (4.3"/7") · Display type (LCD/Monochrome) · Touch (yes/no) · Ports (Serial RS-485/Ethernet)
- **Applications:** machine operator stations, small automation retrofits, panel building — category-level.
- **FAQs:** price range; brand (Delta); sizes (4.3"/7"); communication (RS-485/Ethernet); MOQ; lead time (1–11 days as listed).
- **Related products:** PLC, VFD, SMSP, industrial routers, network gateway (verified).
- **Seller info:** United Control Engineers India Pvt Ltd, distributor, Noida; RFQ + WhatsApp.

**Missing / requires confirmation:** programming-software compatibility (e.g. Delta DIA — not in data **[SUPPLIER]**); resolution data; supply is thin (5 listings, 1 seller, 1 city) — copy must not overstate depth (audit §6).

---

### P10 — SMSP (name itself needs owner confirmation — likely SMPS)

**Identity (verified):**
- Canonical (live): `https://www.udyogconnect.in/products/smsp-vfd-plc-hmi-control-equipments-supplier-india`
- JSON-LD `url`: singular mismatch. Current title: `Top SMSP Prices in India (2026) | UdyogConnect`. Meta templated. SSR: 0 H1. Images: 2. Sellers: 5. Price ₹300–₹1,000. MOQ 1. City: Noida. FAQ: 4 templated.

**Verified data (5 listings — all):** Input 230 V; output 24 V (5/5) — consistent with switched-mode power supplies. Output current as listed: 30–40 (A presumed — unit unstated **[SUPPLIER]**), one anomalous 0. Input current: 4–5. Brand: Delta (1), none (4). Seller: United Control Engineers India Pvt Ltd (distributor, Noida); in stock; lead 1–2 days.

**⚠️ Owner decision required on the page name:** "SMSP" is almost certainly a data-entry artifact for **SMPS** (switched-mode power supply) — verified specs (230 V in → 24 V out) support that reading, but the slug, page name and title all say SMSP. Renaming the slug is a URL change with redirect/canonical implications — **do not change the route in this batch**; decide whether to (a) keep "SMSP" everywhere, (b) display "SMPS (SMSP)" in H1/title while keeping the slug, or (c) plan a separate slug migration with 301s.

**Recommended content (option b assumed):**
- **SEO title:** `SMPS Power Supply Prices in India (2026): ₹300–₹1,000 | 5 Suppliers`
- **H1:** `SMSP Power Supplies — Prices & Verified Suppliers` *(audit §6 wording kept for this batch; SMPS rename decided separately)*
- **Meta description:** `Compare SMSP/SMPS power supply prices (2026) — ₹300–₹1,000 from 5 verified suppliers. 230 V AC in / 24 V DC out units, MOQ 1. Free RFQ on UdyogConnect.`
- **Introduction (~90 words, SSR):** "Switched-mode power supplies (SMPS) convert 230 V AC mains into the regulated low-voltage DC that control panels, PLCs and HMIs run on. UdyogConnect currently lists 5 verified units under this product page, all from one Noida distributor, United Control Engineers India Pvt Ltd. Listings are 230 V input / 24 V DC output supplies with output currents listed at roughly 30–40 A, including one Delta unit, priced ₹300–₹1,000 with MOQ 1. Because supply depth is limited, exact ratings and DIN-rail fit should be confirmed with the seller before ordering."
- **Specifications:** Input voltage (230 V) · Output voltage (24 V DC) · Output current (30–40 as listed, unit to confirm) · Brand (Delta / unbranded)
- **Applications:** PLC/HMI panel power, machine control cabinets, low-voltage DC distribution — category-level.
- **FAQs:** price range; input/output ratings (230 V / 24 V); brand availability; MOQ; why supply depth is limited (5 listings — honest disclosure).
- **Related products:** PLC, HMI, VFD, switchgear (verified).
- **Seller info:** United Control Engineers India Pvt Ltd, distributor, Noida; RFQ + WhatsApp.

**Missing / requires confirmation:** **SMSP vs SMPS naming [OWNER — blocks title/H1 finalisation]**; output-current unit (A? **[SUPPLIER]**); the `0` output-current listing **[SUPPLIER]**.

---

## 3. Verified vs missing data — batch summary (Step 2 guardrails)

**Verified today and safe to publish (after supplier re-check at publish time):** seller counts and company names/roles/cities; price ranges and MOQ; stock status and lead times; listing brands and series (9/10 products); listing spec attributes; image availability (2 per product via listings); FAQ answer facts derived from the above.

**Missing entirely — never fabricate:** product-level model/SKU; product-level hero images (only listing images exist); lumen output, luminaire efficacy, IP ratings for lighting beyond electrical-boxes data; fuse standards/breaking capacity; crimping capacities (zeros in data); board diameters for MCPCB; brand names for electrical-boxes and most MCPCB listings ("other"); any price outside payload ranges; any seller authorization/OEM relationship.

**Explicitly requiring owner or supplier confirmation before implementation:**
1. SMSP → SMPS naming decision (P10) — blocks title/H1 finalisation.
2. OEM brand/series usage policy on aggregation pages (P1–P4, P8, P9: Delta, Schneider, Altivar, Modicon, Mersen, Finder, Havells, Fluke, HTC, SELEC, Ideal, Kosmos, BPL, Be Electronics…).
3. Motor-power/wattage/current units as listed (P2, P4, P10) and the `motor_power: 425`, `output_current: 0` anomalies (P2, P10).
4. MCPCB ₹1 minimum price plausibility (P5); crimping-tool ₹225 title vs ₹200 payload mismatch (P6).
5. Pan-India shipping/lead-time claims (all pages state single-city supply today).
6. Per-series and per-wattage price bands (need listing-level price join at implementation time).
7. Price freshness cadence and seller-side accuracy control (audit risk §8.8).

## 4. `/product/` JSON-LD URL discrepancy — investigation result (Step 3)

**Live verification (2026-11-18, exact block parsed from served HTML of the VFD base page):**

| Surface | Live value | Status |
|---|---|---|
| `<link rel=canonical>` | `https://www.udyogconnect.in/products/vfd-…` | plural, self-referencing (www because prod lags the apex worktree) |
| Product JSON-LD `url` | `https://www.udyogconnect.in/product/vfd-…` | **singular — mismatch** |
| BreadcrumbList last `item` | `https://www.udyogconnect.in/product/vfd-…` | **singular — mismatch** |
| FAQPage / Organization | correct (no product URL / apex) | OK |
| H1 in raw HTML | 0 | unchanged (batch's separate SSR problem) |

**Route resolution (verified in code + live):**
- `frontend/src/app/product/[slug]/layout.tsx` redirects to `/products/{slug}` via Next.js `redirect()` → **serves HTTP 307 (Temporary), live-probed today**; its own comment and docstrings claim "301/SEO authority preserved" — that claim is false. Client `page.tsx` adds a JS fallback `router.replace` for browsers that escape the server redirect. No `middleware.ts` exists; no `next.config.ts` redirects entry exists (config carries only rewrites/headers).
- Because the legacy URL returns 307, not 301, Google continues treating `/product/…` as a live temporary redirect — consistent with the audit's finding that a legacy `/product/connectors-…` URL remains indexed. The Breadcrumb/Product JSON-LD carrying `/product/…` reinforces the same legacy identity.

**Root cause (code, exact locations):** `backend/services/seo_service.py` builds absolute URLs from a single `SITE_URL` class attribute plus a **hard-coded singular path segment**:
- line 1092 — internal link `"url": f"{cls.SITE_URL}/product/{slug}"` (similarProducts)
- line 1181 — Product JSON-LD `"url": f"{cls.SITE_URL}/product/{product_slug}"`
- lines 1277 and 1284 — BreadcrumbList `"item"` for the product node
- line 1525 — payload `"canonicalUrl": f"{cls.SITE_URL}/product/{product.get('slug','')}"`
(`SITE_URL` itself is line 105: `https://udyogconnect.in` — the apex, already correct in the worktree; production payloads emitted before that change carry the www prefix.)

**Why canonical is nonetheless plural live:** `backend/server.py` overrides the field when serving `/api/products/{slug}/seo` — line 5501: `"canonicalUrl": f"https://udyogconnect.in/products/{product_slug}"` (plus the redirect-info variant at line 5509). The frontend product layout (`frontend/src/app/products/[slug]/(main)/layout.tsx`) uses that payload for `alternates.canonical` and injects `seoData.jsonLd` verbatim — so the canonical tag is correct while the embedded JSON-LD keeps the singular URL. Two independent URL builders, one fixed, one not.

**Also affected (same file, singular emitters):** similar-product internal links (line 1092) and category links (`/category/{slug}`, lines 1078–1083) — note `/category/…` exists as a real frontend route and is out of scope here; only the product-path segments are in this batch's scope. `backend/routers/enterprise_products.py` (line 337) and `backend/server.py` lines 5268/13000 already emit plural `/products/` — consistent.

**Fix (proposed, one-line-per-site, no route changes):** replace the four singular f-string path segments in `seo_service.py` with `/products/`, matching the existing canonical override and the deployed Next.js route. **No route paths are changed; the legacy `/product/[slug]` route stays exactly as-is in this batch.** The singular→plural change touches only strings inside JSON-LD payloads and generated link lists — no DB data, no slugs, no redirects.

**Post-fix verification targets:** payload `canonicalUrl`, `jsonLd.url`, `breadcrumbJsonLd` final item, and `internalLinks.*.url` all resolve to `/products/{slug}` under the apex host; live page re-crawl shows Product `@id`/`url` == canonical == Breadcrumb final item; Google Rich Results test passes Product + BreadcrumbList + FAQPage on a deployed page.

**Deferred, owner-decision (NOT in this batch):** upgrade `frontend/src/app/product/[slug]/layout.tsx` from `redirect()` (307) to a true permanent redirect (`permanentRedirect` or `next.config.ts` redirects entry) so legacy URLs consolidate as 301s. Recommended after batch-1 ships because it alters crawler-visible status codes; today's 307 keeps legacy URLs permanently re-crawled.

---

## 5. Technical implementation assessment (Step 4)

Inspected this turn (worktree + live):

- **SSR / rendering:** base page content is `'use client'` (`(main)/page.tsx`, 1,676 lines — filters, compare modal, calculators, enquiry flow, all client-side). Only the layout's metadata + 4 JSON-LD blocks are server-rendered. Enterprise components (`frontend/src/components/enterprise/`: IdentityBlock, SellerCard, ComparisonTable, FilterPanel, InquiryModal, EmptyState…) already model the content that should be server-rendered.
- **Metadata generation:** `generateMetadata` in `(main)/layout.tsx` (revalidate 3600) fetches the SEO payload; title/description/OG/twitter/canonical/robots all derive from the backend payload — one fix in `seo_service.py` propagates to the whole metadata layer. `frontend/src/lib/siteUrl.ts` is the worktree's single source of truth (`SITE_URL` apex; `LEGACY_WWW_URL` only for transition parsing).
- **Canonical tags:** correct and self-referencing (plural) live; `getDefaultMetadata` fallback exists for ObjectId/failed fetches.
- **Internal links:** generated 5-link payload (category, similar ×3, city) — all currently singular-emitted; city links already use real `/products/{slug}/in/{city}` URLs. City claims must be limited to the verified 1–2 cities per product (batch facts in §1).
- **Product schema:** see §4. Additional gaps: brand placeholder ("Various Manufacturers") on all 10; aggregate `lowPrice` fidelity (P6 mismatch shows payload joins can drift from listing data).
- **Image alt text:** no product images in enterprise payload; listing images up to 2 per product with no audited alt text — an alt pass belongs to batch 2 once SSR lands (matches audit B8).
- **Mobile presentation:** the client shell renders a spinner-first experience; all interactive components are present (FilterPanel, MobileFilterDrawer, FloatingCompareBar) but invisible to crawlers. No mobile-specific defect beyond the CSR shell itself.
- **Page performance:** payload fetch is revalidate-cached; the CSR shell is the dominant SEO cost, not payload latency. (No Lighthouse run this turn — no deployed change to measure yet; recommendation section below covers what to measure after implementation.)

**Smallest safe changes that materially improve product quality (ranked):**
1. **Singular→plural URL fix in `seo_service.py`** (4 lines) — makes JSON-LD self-consistent with canonical; zero route/behavior change.
2. **Description de-templating for the 10 batch products** — replace placeholder brand + template copy with the per-product verified copy in §2 (data-driven: a small verified-content map keyed by slug, falling back to the current template for unlisted slugs — no behavior change for the other 38).
3. **Brand field from listing data** — populate Product JSON-LD brand from verified listing brands ("Delta; Schneider Electric" style) or omit rather than "Various Manufacturers" when none (electrical-boxes).
4. **Legacy redirect 307→301** — deliberately deferred (owner decision; §4) although it is itself a two-line change.
5. **SSR for the base page** — the big lever (audit B1) but a frontend architecture decision; out of this batch's safe-change scope, patterned in §6 as phase 2.

---

## 6. Exact source files that would change (Step 4 output — nothing modified yet)

**Batch 1 (proposed, small):**

| File | Change | Lines today |
|---|---|---|
| `backend/services/seo_service.py` | singular `/product/` → plural `/products/` at the 4 URL emitters (1092, 1181, 1277, 1284, 1525) | ~5 lines |
| `backend/services/seo_service.py` | per-product verified content map (10 slugs: description, title adjustments where inconsistent e.g. P6) with template fallback | +~80–120 lines data |
| `backend/services/seo_service.py` | brand derivation from listing brands (replace "Various Manufacturers" where listing data exists; omit/neutral when none) | ~15 lines |
| `backend/tests/test_seo_marketplace_v2.py` | update the existing assertion at line 566 (`…/product/` → `…/products/`) + add brand/description assertions for batch slugs | ~20 lines |
| `frontend/tests/seo/canonical-domain.test.mjs` | add assertion: no emitted product JSON-LD/internal-link URL may contain `/product/` (singular) — guards the fix permanently | ~10 lines |

**Explicitly NOT changed:** route files (`frontend/src/app/product/[slug]/*`, `frontend/src/app/products/**`), `backend/server.py`, `frontend/src/lib/siteUrl.ts`, `next.config.ts`, any sitemap service, `.exvisit/`.

**Phase 2 (owner decision after batch 1):** `(main)/page.tsx` SSR wrapper + enterprise components; `(main)/layout.tsx` H1 injection; legacy route `permanentRedirect`; `frontend/src/app/product/[slug]/layout.tsx` docstring correction; `backend` data-key fix `ip_ratong` → `ip_rating` (P7) with supplier re-verification.

---

## 7. Expected benefit and implementation risk

**Benefit (mechanistic, no traffic estimates):**
- JSON-LD/canonical consistency removes the only systematic structured-data defect (48/48 payloads); Google currently holds legacy `/product/` URLs (audit probe) — consistency plus the existing (307) redirect is the prerequisite for clean consolidation.
- Ten highest-scoring pages gain unique, price- and brand-anchored titles/descriptions/intros matching the audit's §6 plan — the exact surfaces competitors (Moglix/TradeIndia/IndiaMART) win with today; the site's differentiators (verified seller counts, MOQ, city supply, RFQ) finally appear in SERP-visible text without touching rendering architecture.
- FAQ copy moves from 4 identical templated questions to verified per-product facts — eligible content for FAQ rich results alongside the existing FAQPage schema.
- Model/series anchors (Altivar, DVP, Modicon M241…) create the site's first brand+model landing surface (audit intent A4).

**Risk:**
- **Low** — string changes inside generated payloads; no routes, slugs, DB or rendering changes; frontend unchanged.
- Named risks: (1) regex/substring tests that assert the old singular path will fail by design (test updates included in §6); (2) stale-price publication — mitigated by the publish-time re-verification step and payload revalidate(3600); (3) OEM trademark exposure — gated on owner confirmation (§3.2) before any brand names go live; (4) production deployment lag — the apex-host changes already in the worktree must deploy first or payloads will mix apex JSON-LD with www canonicals again; (5) brand field omissions could reduce schema "completeness" scoring tools' output for electrical-boxes — acceptable versus emitting a false brand.

---

## 8. Test plan (to run when the owner approves implementation)

1. **Backend regression (existing gate, scoped):** `PHASE1_TEST_MONGO_URL=… PHASE1_TEST_DB_NAME=… python -m pytest backend/tests/regression -q` — must stay 44/44 (baseline standing; audit-approved bare `python -m pytest` has 8 pre-existing collection-error files — unchanged scope).
2. **Updated SEO tests:** `python -m pytest backend/tests/test_seo_marketplace_v2.py -q` with the line-566 assertion flipped to plural + new batch assertions (brand != "Various Manufacturers" for the 9 brand-verified slugs; description != template marker; payload canonicalUrl plural).
3. **Frontend SEO guard:** `npm --prefix frontend run test:seo` (13/13 baseline) + new singular-URL guard assertion.
4. **Frontend typecheck:** `npm --prefix frontend run typecheck` (PASS baseline) — proves no frontend change broke anything (none should).
5. **Payload spot-check against live shape:** after change, generate the 10 payloads (local seed or production once deployed) and diff `jsonLd.url`, `breadcrumbJsonLd`, `internalLinks`, `canonicalUrl`, `brand`, `seoDescription` against the expected values listed in §2 — scripted assertion, not eyeball.
6. **Structured-data validation (deployed):** Google Rich Results test / schema.org validator on one deployed batch page — Product + BreadcrumbList + FAQPage, `url` == canonical, no `/product/` strings.
7. **Live crawl sanity:** `curl` the deployed page: canonical plural + apex, 4 JSON-LD blocks parse, all Product/Breadcrumb URLs plural; legacy `/product/{slug}` still 307s (unchanged behavior).
8. **Data gate before content publication:** supplier re-verification of every §2 "[SUPPLIER]/[OWNER]" flag; publish-time re-fetch confirming price ranges still match payload.

---

## 9. Deliverable summary for owner review

- 10 products selected exactly per the audit's §6 priority; every value in §1–§2 is verified live/payload 2026-11-18 and items needing confirmation are flagged inline (7 grouped confirmations in §3).
- `/product/` JSON-LD discrepancy fully root-caused (4 emitter lines in `seo_service.py`; server.py canonical override masks it at the metadata layer; legacy route serves 307 not the documented 301) with a minimal, route-preserving fix proposed.
- Technical assessment (§5) identifies the smallest safe changes; SSR remains phase 2 pending owner architecture decision.
- Nothing modified: proposal file is the only workspace change; no staging, no commits, `.exvisit` untouched.

*Prepared for owner review. Implementation starts only on explicit approval; the SMSP naming decision (§3.1) and OEM-brand policy (§3.2) gate parts of the content plan.*

---

## Addendum (2026-11-18, Round-1 implementation) — citation re-anchoring

The line numbers cited above were a snapshot of `backend/services/seo_service.py` before
Round 1. Round 1 **implemented** the fixes below (plus B4/B5), which shifted line numbers.
Historical citations above are preserved verbatim; the current, verified locations are:

| What this document cited (historical) | Historical line | Current location (2026-11-18, post-Round-1) | Status |
|---|---|---|---|
| Internal link `"url": …/product/{slug}` (similarProducts) | 1092 | `seo_service.py:1218` — now plural `/products/{slug}` | ✅ implemented |
| Category internal links `/category/{slug}` | 1078–1083 | `seo_service.py:1204` — now plural `/categories/{slug}` | ✅ implemented |
| Product JSON-LD `"url": …/product/{product_slug}` | 1181 | `seo_service.py:1312` — now plural | ✅ implemented |
| BreadcrumbList product `"item"` (two nodes) | 1277, 1284 | `seo_service.py:1408` and `1415` — now plural (category node at 1402) | ✅ implemented |
| Payload `"canonicalUrl": …/product/{slug}` | 1525 | `seo_service.py:1657` — now plural | ✅ implemented |
| City/intent internal links | — | `seo_service.py:1227` (city), `1247` (intent+city) — plural, real routes | ✅ implemented |
| `server.py` canonical override at 5501 (+ redirect variant 5509) | 5501 / 5509 | `server.py:5513` / `5521` (also 5268, 13012, 13063) — plural | ✅ verified |
| `test_seo_marketplace_v2.py:566` pinning the **singular** path | 566 | Assertion now at `568–569` and asserts the **plural** `/products/` contract (B2 correction; redirect-layer pins in `test_seo_v21_enforcement.py`, `test_seo_v2_migration*.py` intentionally preserved) | ✅ updated |

Also delivered in Round 1 (see `UdyogConnect_B1_ServerRendering_Architecture_Proposal_2026-11-18.md` for the B1
architecture proposal awaiting review): B4 supply-gated city pages (real distinct-seller counts, zero-supply
404, no "0 Verified Suppliers", visible FAQ), B5 distinct per-product descriptions (`SEO_VERSION` 8, panel-fan
fix), B3 sitemap verification (live 4,925 URLs → intended ≈187), regression suite
`backend/tests/regression/test_seo_product_seo_round1.py` (16 tests, 60/60 directory pass).
