// Minimal wrapper layout for all /products/[slug]/* routes.
// Route-specific metadata & JSON-LD are handled in deeper layouts:
//   - (main)/layout.tsx         → main product page SEO + JSON-LD
//   - in/[city]/page.tsx        → city-scoped SEO + JSON-LD
//   - seller/[listingId]/page.tsx → seller-scoped SEO (if any)
export default function ProductLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
