/**
 * Human labels for the capability taxonomy.
 *
 * `config/regional_capabilities.json` stores capabilities as slugs, and the
 * pages used to render them straight through: /capability-matches printed
 * `civil_engineering` verbatim, and /regional-connections did
 * `.replace(/_/g, ' ')` under `text-transform: capitalize`, which produced
 * "Ict Integration". Readers should see the trade, not the database key.
 *
 * Keys mirror `capability_taxonomy` in that config. Anything not listed
 * degrades to a readable form rather than showing an underscore.
 */
const LABELS: Record<string, string> = {
  aviation_infrastructure: 'Airports & aviation works',
  civil_engineering: 'Civil engineering',
  climate_resilience: 'Climate resilience',
  construction_delivery: 'Construction',
  digital_services: 'Digital services',
  education_services: 'Education & training',
  engineering_services: 'Engineering services',
  food_processing: 'Food processing',
  ict_integration: 'IT systems',
  industrial_fabrication: 'Industrial fabrication',
  medical_supply: 'Medical supplies',
  professional_services: 'Professional services',
  project_finance: 'Project finance',
  shipping_logistics: 'Shipping & logistics',
  warehousing_distribution: 'Warehousing & distribution',
  water_infrastructure: 'Water infrastructure',
};

/** A capability slug as a reader should see it. */
export function capabilityLabel(id: string | null | undefined): string {
  if (!id) return 'Unspecified';
  const key = String(id).replace(/^capability:/, '').trim();
  if (LABELS[key]) return LABELS[key];
  // Unknown slug: still never show an underscore.
  const words = key.replace(/[_-]+/g, ' ').trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : 'Unspecified';
}

/**
 * Sector labels. `sector` is a separate taxonomy from `capability` and was
 * still rendering raw: a match row read "Bahamas climate_resilience", and the
 * sector filter listed the slugs verbatim.
 */
const SECTORS: Record<string, string> = {
  aviation_infrastructure: 'Airports & aviation',
  climate_resilience: 'Climate resilience',
  construction_and_works: 'Construction & works',
  digital_and_ict: 'Digital & IT',
  education_infrastructure: 'Education facilities',
  medical_supplies: 'Medical supplies',
  transport_and_logistics: 'Transport & logistics',
  water_and_irrigation: 'Water & irrigation',
};

/** A sector slug as a reader should see it. */
export function sectorLabel(id: string | null | undefined): string {
  if (!id) return 'Unsorted';
  const key = String(id).trim();
  if (SECTORS[key]) return SECTORS[key];
  const words = key.replace(/[_-]+/g, ' ').trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : 'Unsorted';
}

/**
 * Tender lifecycle labels. /opportunity-resolution had its own copy of this
 * map; /capability-matches had none and printed the raw token ("UNRESOLVED").
 */
const STATES: Record<string, string> = {
  detected: 'Detected',
  open: 'Open',
  amended: 'Amended',
  closed: 'Closed — awaiting outcome',
  awarded: 'Awarded',
  cancelled: 'Cancelled',
  unresolved: 'Unresolved',
};

/** A tender lifecycle state as a reader should see it. */
export function stateLabel(id: string | null | undefined): string {
  if (!id) return 'Unknown';
  const key = String(id).trim();
  return STATES[key] || key.replace(/[_-]+/g, ' ');
}

export default capabilityLabel;
