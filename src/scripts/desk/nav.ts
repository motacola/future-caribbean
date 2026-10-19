// Several destinations are collapsed accordions now. An anchor that lands on a
// closed panel looks like a dead link, so opening the target is part of going
// there — for nav clicks, for the desk guide, and for a pasted #hash on load.
export function revealTarget(id: string): HTMLElement | null {
  const target = id && document.getElementById(id);
  if (!target) return null;
  const panel = target.closest('details') || (target.tagName === 'DETAILS' ? target : target.querySelector('details'));
  if (panel) panel.open = true;
  return target;
}

export function initAnchorReveal(): void {
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;
    revealTarget(decodeURIComponent(link.getAttribute('href').slice(1)));
  });

  if (location.hash) {
    const landed = revealTarget(decodeURIComponent(location.hash.slice(1)));
    if (landed) setTimeout(() => landed.scrollIntoView({ block: 'start' }), 60);
  }
}
