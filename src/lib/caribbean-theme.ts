/**
 * Caribbean editorial chart theme for TanStack Charts.
 *
 * Mirrors /Users/christopherbelgrave/Documents/signal-fabric-designer/src/charts/caribbean-theme.ts
 * so chart definitions are interchangeable between the designer and the live
 * site. Both must use the same palette tokens.
 *
 * Freshness rule: any chart fed live data must show a `dataAsOf` label.
 *
 * Imported by src/lib/charts/*.ts and any React island that renders
 * TanStack Charts. Tokens are also consumed as CSS custom properties so the
 * Astro site's static SVG charts (see src/lib/data.ts) can stay in sync.
 */

export const caribbeanTheme = {
  // Surface — read from the page's CSS variables so the chart inherits
  // the live site's design tokens. The defaults match the designer's
  // palette; the build page sets :root tokens that override these.
  background: 'var(--caribbean-bg, #FFFCF4)',
  foreground: 'var(--caribbean-fg, #18251F)',
  // Axis + grid
  grid: 'color-mix(in oklab, var(--caribbean-fg, #18251F) 12%, transparent)',
  axis: 'color-mix(in oklab, var(--caribbean-fg, #18251F) 60%, transparent)',
  tick: 'color-mix(in oklab, var(--caribbean-fg, #18251F) 75%, transparent)',
  // Marks — Caribbean palette (sea, reef, sand, sun, storm)
  sea: 'var(--caribbean-sea, #1dbdd3)',
  reef: 'var(--caribbean-reef, #36c98a)',
  sand: 'var(--caribbean-sand, #f2d94c)',
  sun: 'var(--caribbean-sun, #ff8a3d)',
  storm: 'var(--caribbean-storm, #315cff)',
  // Accent for focus / selection
  accent: 'var(--caribbean-accent, #0c8ce9)',
  inspect: 'var(--caribbean-inspect, #B57A22)',
} as const;

export type CaribbeanTheme = typeof caribbeanTheme;
