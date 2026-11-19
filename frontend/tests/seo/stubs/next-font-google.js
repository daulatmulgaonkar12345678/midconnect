// Stub for `next/font/google` in the SEO metadata tests: the font loader is a
// build-time Next.js concern and has no bearing on metadata resolution. Any
// named font export resolves to the same inert factory.
const font = () => ({ className: 'stub-font', style: { fontFamily: 'stub' } });
module.exports = new Proxy(
  {},
  { get: (_target, prop) => (prop === '__esModule' ? false : font) },
);
