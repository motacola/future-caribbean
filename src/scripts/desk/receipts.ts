// Receipts and engine panels: domain cards, reasoning thesis, verdict filter,
// expandable signal rows and the cycle clock.

export function initEngineCards(): void {
  fetch('/api/domains')
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (!d || !d.ok || !d.domains) return;
      const grid = document.getElementById('eb-instances');
      if (!grid) return;
      grid.innerHTML = d.domains.map(x => {
        const live = x.status === 'live';
        const c = x.counts || {};
        return '<div class="eb-card ' + (live ? 'eb-live' : 'eb-bp') + '">' +
          '<span class="eb-badge ' + (live ? 'on' : 'off') + '">' + (live ? '● Live' : 'Blueprint') + '</span>' +
          '<div class="eb-name">' + x.name + '</div>' +
          '<div class="eb-meta">' + (c.sources_wired || 0) + '/' + (c.sources || 0) + ' sources · ' +
          (c.recipients || 0) + ' roles</div></div>';
      }).join('');
    })
    .catch(() => {});

  fetch('/api/reasoning')
    .then(r => r.ok ? r.json() : null)
    .then(r => {
      if (!r || !r.ok || !r.thesis) return;
      const box = document.getElementById('eb-reason');
      document.getElementById('eb-reason-text').textContent = r.thesis;
      box.style.display = 'block';
    })
    .catch(() => {});
}

function updateFilterCounts() {
  document.getElementById('count-all').textContent = VERDICT_COUNTS.all;
  document.getElementById('count-advance').textContent = VERDICT_COUNTS.advance;
  document.getElementById('count-hold').textContent = VERDICT_COUNTS.hold;
  document.getElementById('count-reject').textContent = VERDICT_COUNTS.reject;
}

let currentVerdictFilter = 'all';

function filterSignals() {
  document.querySelectorAll('#sig-list .sig-row').forEach(row => {
    const verdict = row.dataset.verdict;
    if (currentVerdictFilter === 'all' || verdict === currentVerdictFilter) {
      row.style.display = 'flex';
    } else {
      row.style.display = 'none';
    }
  });
}

export function initReceipts(): void {
  updateFilterCounts();

  document.querySelectorAll('.verdict-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const verdict = btn.dataset.verdict;
      currentVerdictFilter = verdict;
      document.querySelectorAll('.verdict-btn').forEach(b => b.classList.toggle('active', b.dataset.verdict === verdict));
      filterSignals();
    });
  });

  document.querySelectorAll('#sig-list .sig-expand').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const row = btn.closest('.sig-row');
      const open = row.classList.toggle('expanded');
      btn.textContent = open ? '▲' : '▼';
      btn.setAttribute('aria-expanded', String(open));
    });
  });
  // Keep the chevron in sync when the row itself is clicked to toggle.
  document.querySelectorAll('#sig-list .sig-row').forEach(row => {
    row.addEventListener('toggle-signal', () => {
      const btn = row.querySelector('.sig-expand');
      if (btn) btn.textContent = row.classList.contains('expanded') ? '▲' : '▼';
    });
  });

  document.querySelectorAll('#sig-list .sig-row').forEach(row => {
    row.addEventListener('click', (e) => {
      if (!e.target.closest('.sig-expand') && !e.target.closest('a') && !e.target.closest('.sig-validation')) {
        const open = row.classList.toggle('expanded');
        const btn = row.querySelector('.sig-expand');
        if (btn) { btn.textContent = open ? '▲' : '▼'; btn.setAttribute('aria-expanded', String(open)); }
      }
    });
  });
}

// Nothing rolled over past hours, so a cycle three weeks old read as
// "557h 43m 51s ago". Roll up, and drop precision nobody reads at that scale.
function formatDuration(seconds) {
  if (seconds == null) return '—';
  if (seconds <= 0) return 'Now';
  const m = Math.floor(seconds / 60);
  const h = Math.floor(seconds / 3600);
  const d = Math.floor(seconds / 86400);
  if (d >= 7) {
    const w = Math.floor(d / 7);
    return w + (w === 1 ? ' week' : ' weeks');
  }
  if (d >= 1) return d + (d === 1 ? ' day' : ' days');
  if (h >= 1) {
    const rm = Math.floor((seconds % 3600) / 60);
    return rm ? h + 'h ' + rm + 'm' : h + 'h';
  }
  if (m >= 1) return m + 'm ' + (seconds % 60) + 's';
  return seconds + 's';
}

function updateCycleClock() {
  fetch('/api/status')
    .then(r => r.ok ? r.json() : null)
    .then(status => {
      if (!status) return;
      const nextEl = document.getElementById('next-cycle');
      const lastEl = document.getElementById('last-cycle');
      if (status.next_cycle_in != null) {
        nextEl.textContent = formatDuration(status.next_cycle_in);
      }
      if (status.last_cycle_ago != null) {
        lastEl.textContent = formatDuration(status.last_cycle_ago) + ' ago';
      }
    })
    .catch(() => {});
}

export function initCycleClock(): void {
  updateCycleClock();
  setInterval(updateCycleClock, 30000);
}
