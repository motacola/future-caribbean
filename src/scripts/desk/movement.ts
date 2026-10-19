import { openCountryDrill } from './map.ts';

export function initRegionalMovement(): void {
  // Regional movement strip: tapping a country chip opens the same map-drill
  // that the leaflet marker click does. We scroll into view so the user lands
  // on the relevant triage panel.
  document.querySelectorAll('.rmv-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const country = chip.dataset.country;
      if (!country) return;
      openCountryDrill(country);
      document.getElementById('map-drill')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  });

  // Track filter: show only chips matching the selected Opportunity vs
  // Dislocation/Risk track. The track is a pure function of the signal kind,
  // carried on each chip as data-track, so filtering never reclassifies.
  const trackBtns = document.querySelectorAll('.track-btn');
  trackBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const filter = btn.dataset.trackFilter || 'all';
      trackBtns.forEach(b => b.classList.toggle('is-active', b === btn));
      document.querySelectorAll('.rmv-chip').forEach(chip => {
        const t = chip.dataset.track || 'unclassified';
        chip.hidden = !(filter === 'all' || t === filter);
      });
    });
  });
}
