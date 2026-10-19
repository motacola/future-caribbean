export function initChartReadouts(): void {
  // Chart bars carry their reading in an SVG <title>, which touch devices never
  // surface. Mirror it into a live readout under the chart.
  document.querySelectorAll('.market-chart-card').forEach(card => {
    const readout = card.querySelector('.activity-readout');
    const cols = [...card.querySelectorAll('.activity-col')];
    if (!readout || !cols.length) return;
    const show = col => {
      cols.forEach(c => c.classList.toggle('picked', c === col));
      // The card already carries the "not a price" disclosure; no need to repeat it here.
      readout.textContent = (col.querySelector('title')?.textContent || '').replace(/\s*Not a price\.\s*$/, '');
      readout.classList.add('on');
    };
    cols.forEach(col => {
      col.addEventListener('click', () => show(col));
      col.addEventListener('focus', () => show(col));
    });
  });
}
