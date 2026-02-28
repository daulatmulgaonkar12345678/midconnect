// Central configuration - Single source of truth for app-wide constants
// Change here = change everywhere

export const APP_NAME = "UdyogConnect";
export const APP_TAGLINE = "India's Industrial Marketplace";
export const APP_DESCRIPTION = "Connect with verified manufacturers, dealers, and distributors. Buy industrial products - Steel, Electrical, Chemicals, Building Materials and more.";
export const APP_KEYWORDS = "B2B marketplace, industrial products, manufacturers, dealers, steel, electrical equipment, chemicals, India";

// SEO metadata
export const SEO = {
  title: `${APP_NAME} - ${APP_TAGLINE}`,
  description: APP_DESCRIPTION,
  keywords: APP_KEYWORDS,
  ogTitle: `${APP_NAME} - ${APP_TAGLINE}`,
  ogDescription: "Connect with verified manufacturers, dealers, and distributors.",
  twitterCard: "summary" as const,
};

// Footer content
export const FOOTER = {
  tagline: "India's trusted B2B marketplace for industrial products. Connect with verified manufacturers, dealers, and distributors.",
  copyright: (year: number) => `© ${year} ${APP_NAME}. All rights reserved.`,
};
