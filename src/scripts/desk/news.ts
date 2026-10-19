export function initNewsFilters(): void {
  document.querySelectorAll('[data-news-filter]').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('[data-news-filter]').forEach(b => b.classList.toggle('active', b === button));
    const filter = button.dataset.newsFilter || 'all';
    document.querySelectorAll('.news-card').forEach(card => {
      const [kind, value] = filter.split(':');
      card.hidden = filter !== 'all' && !(kind === 'topic' ? (card.dataset.newsTopics || '').split('|').includes(value) : (card.dataset.newsCountries || '').split('|').includes(value));
    });
  }));
}

// Bridge from the map drill to the news desk: apply the country filter, open
// the country chip row if it is collapsed, and scroll the reader to the board.
export function showCountryInNewsDesk(country: string): void {
  const button = document.querySelector(`[data-news-filter="country:${CSS.escape(country)}"]`);
  const wrap = document.getElementById('news-countries');
  const toggle = document.getElementById('news-country-toggle');
  if (wrap && wrap.hasAttribute('hidden')) {
    wrap.removeAttribute('hidden');
    toggle?.setAttribute('aria-expanded', 'true');
  }
  if (button) button.click();
  document.getElementById('regional-news')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function initNewsCountryToggle(): void {
  const countryToggle = document.getElementById('news-country-toggle');
  const countryWrap = document.getElementById('news-countries');
  if (countryToggle && countryWrap) {
    countryToggle.addEventListener('click', () => {
      const open = countryWrap.hasAttribute('hidden');
      if (open) countryWrap.removeAttribute('hidden'); else countryWrap.setAttribute('hidden', '');
      countryToggle.setAttribute('aria-expanded', String(open));
    });
  }
}
