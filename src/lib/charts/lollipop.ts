/**
 * Lollipop chart shape for TanStack Charts v0.11.
 *
 * Mirrors /Users/christopherbelgrave/Documents/signal-fabric-designer/src/charts/caribbean-examples.ts
 * (opportunityLollipop). The designer file uses illustrative data; this file
 * provides the same `defineChart()` shape with a real-data adapter that
 * reads `outbox/dispatch_desk.json` and produces a ranked lollipop of
 * Caribbean markets by opportunity score.
 *
 * The contract: given a CycleOpportunity[] (a flat island-name + score
 * pair), produce a chart definition that renders a barX + ruleX combo
 * with a 60-point "watch" threshold.
 *
 * Use `buildOpportunityLollipop` from the React island on /build. Server-
 * side callers (Astro pages) can use the pure data adapter
 * `opportunitiesFromDesk` to feed it.
 */

import { defineChart, barX, ruleX } from '@tanstack/charts';
import { scaleLinear } from '@tanstack/charts-scales/linear';
import { scalePoint } from '@tanstack/charts-scales/point';
import { caribbeanTheme } from '../caribbean-theme.ts';

export interface CycleOpportunity {
  id: string;
  name: string;
  score: number; // 0-100
  cycle: string;
}

export interface OpportunityLollipopProps {
  opportunities: CycleOpportunity[];
  dataAsOf: string; // ISO timestamp; required freshness label
  watchThreshold?: number; // default 60
}

/**
 * Build a TanStack chart definition for the ranked lollipop.
 *
 * The shape matches the designer's opportunityLollipop: barX for the
 * score bar + ruleX for the watch threshold, with caribbeanTheme applied.
 *
 * The chart definition is serializable (no functions in the output), so
 * it can be passed through Astro's data layer to a React island that
 * imports it from @tanstack/react-charts.
 */
export function buildOpportunityLollipop(props: OpportunityLollipopProps) {
  const watch = props.watchThreshold ?? 60;
  const watchLine: CycleOpportunity[] = props.opportunities.map((o) => ({
    ...o,
    score: watch,
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
      barX(props.opportunities, {
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
      axis: { label: `Opportunity score (0–100) · as of ${props.dataAsOf}` },
      grid: true,
    },
    y: {
      scale: scalePoint().domain(opportunities.map((o) => o.name)),
      axis: { label: '' },
      grid: false,
    },
    theme: caribbeanTheme,
  });
}

/**
 * Build the opportunity list from a `dispatch_desk.json` payload.
 *
 * The desk payload exposes `clusters[]` with `country_cluster`,
 * `confidence_score`, and `signal_kind`. We aggregate clusters by country
 * (max confidence per country) and produce a `CycleOpportunity` per
 * distinct country for the current cycle.
 */
export function opportunitiesFromDesk(desk: {
  cycle_id?: string;
  clusters?: Array<{
    country_cluster?: string;
    confidence_score?: number;
  }>;
}): { opportunities: CycleOpportunity[]; dataAsOf: string; cycle: string } {
  const cycle = desk.cycle_id || 'unknown';
  const dataAsOf = new Date().toISOString();
  const byCountry = new Map<string, number>();
  for (const c of desk.clusters || []) {
    const country = String(c.country_cluster || '').trim();
    if (!country) continue;
    const score = Number(c.confidence_score || 0);
    const prev = byCountry.get(country) ?? 0;
    if (score > prev) byCountry.set(country, score);
  }
  const opportunities: CycleOpportunity[] = [...byCountry.entries()]
    .map(([name, score]) => ({
      id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
      name,
      score,
      cycle,
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 12);
  return { opportunities, dataAsOf, cycle };
}
