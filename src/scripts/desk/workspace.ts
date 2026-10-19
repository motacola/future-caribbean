// Today's call: lead risk, diligence checklist, output tabs, the system audit
// toggle and the quick-answer box.

export function initLeadRisk(): void {
  if (risks.length) {
    document.getElementById('risk-area').innerHTML = '<div class="lead-risk">⚠️ ' + risks[0] + '</div>';
  }
}

export function initChecklist(): void {
  // Keyed by market, not by cycle: diligence on Guyana is still diligence on
  // Guyana next cycle, so progress should survive the desk moving on.
  const checklistCountry = (D.lead && D.lead.country) || 'region';
  const checklistKey = 'future-caribbean:checks:' + checklistCountry;
  const savedChecks = JSON.parse(localStorage.getItem(checklistKey) || '[]');
  const checkItems = [...document.querySelectorAll('#lead-checklist .check-item')];
  const checkProgress = document.getElementById('check-progress');

  function paintChecklist() {
    const done = checkItems.filter(x => x.classList.contains('done'));
    if (checkProgress) checkProgress.textContent = done.length + ' of ' + checkItems.length + ' done for ' + checklistCountry;
    return done.map(x => x.dataset.check);
  }

  checkItems.forEach(item => {
    const on = savedChecks.includes(item.dataset.check);
    item.classList.toggle('done', on);
    item.setAttribute('aria-checked', String(on));
    const toggle = () => {
      const next = !item.classList.contains('done');
      item.classList.toggle('done', next);
      item.setAttribute('aria-checked', String(next));
      localStorage.setItem(checklistKey, JSON.stringify(paintChecklist()));
    };
    item.addEventListener('click', toggle);
    item.addEventListener('keydown', e => {
      if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(); }
    });
  });
  paintChecklist();
}

export function initOutputs(): void {
  const outTabs = [...document.querySelectorAll('.out-tab')];
  const outPanels = [...document.querySelectorAll('.out-panel')];
  const outCopy = document.getElementById('out-copy');

  function selectOut(name: string, focus?: boolean) {
    outTabs.forEach(t => {
      const on = t.dataset.out === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      if (on && focus) t.focus();
    });
    outPanels.forEach(p => { p.hidden = p.dataset.out !== name; });
    if (outCopy) outCopy.textContent = 'Copy to clipboard';
  }

  outTabs.forEach((tab, i) => {
    tab.addEventListener('click', () => selectOut(tab.dataset.out));
    tab.addEventListener('keydown', e => {
      const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!step) return;
      e.preventDefault();
      selectOut(outTabs[(i + step + outTabs.length) % outTabs.length].dataset.out, true);
    });
  });

  if (outCopy) {
    outCopy.addEventListener('click', async () => {
      const panel = outPanels.find(p => !p.hidden);
      if (!panel) return;
      try {
        await navigator.clipboard.writeText(panel.querySelector('.out-body').textContent.trim());
        outCopy.textContent = 'Copied';
      } catch {
        outCopy.textContent = 'Selected — copy it';
        const r = document.createRange();
        r.selectNodeContents(panel.querySelector('.out-body'));
        const sel = getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      }
      setTimeout(() => { outCopy.textContent = 'Copy to clipboard'; }, 2000);
    });
  }
}

export function toggleDeep(): void {
  const c = document.getElementById('dc'); const b = document.getElementById('db');
  if (c.classList.contains('open')) { c.classList.remove('open'); b.textContent = '▸ System audit'; }
  else { c.classList.add('open'); b.textContent = '▾ System audit'; c.scrollIntoView({behavior:'smooth'}); }
}

export function deskAsk(q?: string): void {
  const box = document.getElementById('da');
  if (!q) { box.textContent = 'Select a prompt or ask a question.'; return; }
  const d = D.lead; const l = q.toLowerCase();
  if (l === 'explain' || l.includes('lead') || l.includes('first')) {
    box.textContent = 'Lead: ' + d.title + '\n\n' + D.thesis + '\n\nEvidence: ' + d.evidence + '\nAudiences:\n' + d.personas.slice(0,3).map(p => '• ' + p.persona + ': ' + p.action.substring(0,80) + '…').join('\n');
  } else if (l.includes('investor')) {
    box.textContent = 'Investor receives:\n\n"' + d.title + '.\n\n' + (D.thesis.length > 120 ? D.thesis.substring(0,120) + '…' : D.thesis) + '\n\nNext: Validate ' + d.country + '. Screen sector fit, partners, timing.\n\nScreening signal, not investment advice."';
  } else if (l.includes('what changed') || l.includes('changed')) {
    box.textContent = 'Cycle ' + D.cycle + ':\n\n• ' + D.signals + ' regional signals\n• ' + D.dispatches + ' dispatches routed\n\n' + D.thesis;
  } else if (l.includes('guyana') || l.includes('lead country') || l.includes('why')) {
    box.textContent = d.country + ' leads (High confidence).\n\n' + d.evidence + (d.pct ? ' (' + d.pct + ')' : '') + '\n\nCompare against secondary signals before committing.';
  } else if (l.includes('draft') || l.includes('note')) {
    box.textContent = 'Draft:\n\nSubject: ' + d.country + ' signal worth reviewing\n\n' + d.title + '.\n' + d.evidence + (d.pct ? ' (' + d.pct + ')' : '') + '\n\nNext: Validate sector fit, local partners, timing.\n\nScreening signal, not investment advice.';
  } else {
    box.textContent = 'Try: explain lead · investor view · what changed · why ' + d.country + ' · draft a note';
  }
  box.scrollTop = 0;
}
