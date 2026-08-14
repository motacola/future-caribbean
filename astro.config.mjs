import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// We render TanStack Charts as small React islands inside Astro pages
// (specifically /build). Static SVG paths stay in pure Astro (see
// src/lib/data.ts -> buildIndexedCandlestickSvg). The split matches the
// design decision in src/styles.css notes: static/deterministic charts in
// Astro, interactive islands in /build via React.
export default defineConfig({
  integrations: [react()],
});
