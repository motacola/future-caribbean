// Page data written by desk.astro's inline data <script> (from loadDashboardData)
// and the libraries it loads from CDNs. Payload shapes are owned by
// src/lib/data.ts, so they stay loose here.
declare const D: any;
declare const MAP_DISPATCHES: Record<string, any[]>;
declare const MAP_MARKERS: any[];
declare const MAP_MARKER_BY_COUNTRY: Record<string, any>;
declare const NEWS_BY_COUNTRY: Record<string, any[]>;
declare const THEATER_EVENTS: { event: string; data?: any }[];
declare const MAP_COLORS: Record<string, string>;
declare const REPLAY_JSONL_URL: string;
declare const VERDICT_COUNTS: Record<'all' | 'advance' | 'hold' | 'reject', any>;
declare const risks: string[];
declare function humanizeJs(text: string): string;

declare const L: any;
declare const React: any;
declare const ReactDOM: any;
declare const htm: any;

interface Window {
  ask: (q?: string) => void;
  toggleDeep: () => void;
  openCountryDrill: (country: string) => void;
}
