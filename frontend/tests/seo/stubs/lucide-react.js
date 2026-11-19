// Test seam: minimal lucide-react double for node-side SSR rendering of the
// compiled ProductSeoHero. Any icon renders as a passive svg placeholder.
// CommonJS by necessity: the tsc-compiled hero loads this via require().
/* eslint-disable @typescript-eslint/no-require-imports */
const React = require('react');

module.exports = new Proxy(
  {},
  {
    get(_target, prop) {
      if (prop === '__esModule') return true;
      return function Icon(props) {
        return React.createElement('svg', props);
      };
    },
  },
);
