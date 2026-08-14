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
import { buildOpportunityLollipop, type CycleOpportunity } from './lollipop.ts';

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
    () => buildOpportunityLollipop({ opportunities, dataAsOf }),
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
