// Test seam: minimal next/link double for node-side SSR rendering of the
// compiled ProductSeoHero (the real next/link pulls router runtime pieces the
// render-to-string harness does not need). Renders a plain anchor.
// CommonJS by necessity: the tsc-compiled hero loads this via require().
/* eslint-disable @typescript-eslint/no-require-imports */
const React = require('react');

module.exports = {
  __esModule: true,
  default: function Link(props) {
    return React.createElement('a', { href: props.href }, props.children);
  },
};
