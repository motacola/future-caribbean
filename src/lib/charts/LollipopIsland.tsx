/**
 * Lollipop chart island for /build.
 *
 * Renders the opportunityLollipop (from src/lib/charts/lollipop.ts) inside
 * an Astro page using a React island. The chart definition is built
 * client-side from the serializable props Astro passes in.
 *
 * The chart consumes TanStack Charts v0.11, which is the only TanStack
 * dependency in this repo. Static SVG charts elsewhere on the site do
 * NOT use this — they use src/lib/data.ts -> buildIndexedCandlestickSvg.
 */
import * as React from 'react';
import { Chart } from '@tanstack/charts/react';
import { defineChart, barX, ruleX } from '@tanstack/charts';
import { scaleLinear } from '@tanstack/charts-scales/linear';
import { scalePoint } from '@tanstack/charts-scales/point';
import { caribbeanTheme } from '../caribbean-theme.ts';
import type { CycleOpportunity } from './lollipop.ts';

const WATCH_THRESHOLD = 60;

/**
 * Rebuild the chart definition on the client.
 *
 * The chart definition (with its scale functions) is not serializable, so
 * it must be rebuilt from the same `opportunities` shape the Astro
 * server-side `buildOpportunityLollipop` (in lollipop.ts) used. The two
 * MUST stay in lockstep. If you add a mark to lollipop.ts, add it here.
 */
function clientLollipop(
  opportunities: CycleOpportunity[],
  dataAsOf: string,
) {
  const watchLine: CycleOpportunity[] = opportunities.map((o) => ({
    ...o,
    score: WATCH_THRESHOLD,
  }));
  return defineChart({
    marks: [
      ruleX(watchLine, {
        x: 'score',
        y: 'name',
        stroke: caribbeanTheme.sun,
        strokeOpacity: 0.8,
        strokeWidth: 2,
        strokeDasharray: '6 6',
      }),
      barX(opportunities, {
        x: 'score',
        y: 'name',
        key: 'id',
        fill: caribbeanTheme.reef,
        fillOpacity: 0.85,
        inset: 0.35,
      }),
    ],
    x: {
      scale: scaleLinear().domain([0, 100]),
      axis: { label: `Opportunity score (0–100) · as of ${dataAsOf}` },
      grid: true,
    },
    y: {
      scale: scalePoint(),
      axis: { label: '' },
      grid: false,
    },
    theme: caribbeanTheme,
  });
}

export interface LollipopIslandProps {
  opportunities: CycleOpportunity[];
  dataAsOf: string;
  height?: number;
  emptyMessage?: string;
}

export default function LollipopIsland({
  opportunities,
  dataAsOf,
  height = 420,
  emptyMessage = 'No cycle opportunities yet — the next run will populate this.',
}: LollipopIslandProps): React.JSX.Element {
  const definition = React.useMemo(
    () => clientLollipop(opportunities, dataAsOf),
    [opportunities, dataAsOf],
  );

  if (!opportunities || opportunities.length === 0) {
    return (
      <div
        className="lollipop-empty"
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--border)',
          borderRadius: '0.5rem',
          color: 'var(--muted-foreground)',
          fontSize: '0.875rem',
          padding: '1rem',
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  return (
    <div
      className="lollipop-island"
      style={{
        height,
        border: '1px solid var(--border)',
        borderRadius: '0.5rem',
        background: 'var(--caribbean-bg)',
      }}
    >
      <Chart
        definition={definition}
        ariaLabel="Ranked opportunity score per Caribbean market, with a 60-point watch threshold"
      />
    </div>
  );
}
