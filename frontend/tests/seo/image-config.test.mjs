// Batch 1 (2026-11-19) image-delivery regression tests (node:test).
//
// Vercel's image optimizer answered every uncached /_next/image request with
// HTTP 402 (X-Vercel-Error: OPTIMIZED_IMAGE_REQUEST_PAYMENT_REQUIRED),
// breaking image delivery sitewide. The remediation sets
// images.unoptimized = true in next.config.ts so next/image emits the
// original source URLs directly (Cloudinary URLs already carry f_auto,q_auto
// transformations). These tests lock that configuration in place.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const config = readFileSync(path.join(here, '..', '..', 'next.config.ts'), 'utf8');

test('next.config disables the Vercel image optimizer (unoptimized: true)', () => {
  assert.match(config, /images\s*:\s*\{[\s\S]*?unoptimized\s*:\s*true/);
});

test('image config keeps Cloudinary among the allowed remote patterns', () => {
  assert.match(config, /res\.cloudinary\.com/);
});

test('image config emits no legacy www origin', () => {
  assert.doesNotMatch(config, /www\.udyogconnect\.in/);
});
