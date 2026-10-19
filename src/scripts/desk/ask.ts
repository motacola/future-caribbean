export function initAskDesk(): void {
  if (typeof React === 'undefined' || typeof ReactDOM === 'undefined' || typeof htm === 'undefined') {
    // React and htm come from a CDN. When that load is blocked the panel
    // used to open on an empty box under a heading promising answers. Say
    // what happened and point at the interfaces that still work — the same
    // deterministic engine answers over HTTP and the CLI.
    const root = document.getElementById('ask-desk-root');
    if (root) {
      root.innerHTML =
        '<div class="ask-offline">The ask panel could not load its scripts, so it is unavailable on this page. ' +
        'The same deterministic answers are still available: ' +
        '<code>curl -X POST /api/ask -d \'{"question":"explain lead"}\'</code> ' +
        'or <code>python3 cli/abengctl.py ask "explain lead"</code>.</div>';
    }
    return;
  }
  const html = htm.bind(React.createElement);
  const { useState, useRef, useEffect } = React;
  const CHIPS = [
    'Explain the lead signal', 'What changed this cycle?',
    'Routes for diaspora investor', 'Draft a note for Guyana',
  ];

  function Typewriter({ text }) {
    const [shown, setShown] = useState(0);
    useEffect(() => {
      setShown(0);
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) { setShown(text.length); return; }
      const step = Math.max(2, Math.round(text.length / 90));
      const t = setInterval(() => setShown(s => {
        if (s >= text.length) { clearInterval(t); return s; }
        return s + step;
      }), 13);
      return () => clearInterval(t);
    }, [text]);
    return html`<span>${text.slice(0, shown)}<span class="type-caret ${shown < text.length ? '' : 'done'}"></span></span>`;
  }

  function AskDesk() {
    const [q, setQ] = useState('');
    const [thread, setThread] = useState([]);
    const [busy, setBusy] = useState(false);
    const [offline, setOffline] = useState(false);
    const inputRef = useRef(null);

    async function ask(question) {
      const query = (question || '').trim();
      if (!query || busy) return;
      setBusy(true); setOffline(false); setQ('');
      try {
        const res = await fetch('/api/ask', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: query }),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        setThread(t => [{ q: query, a: humanizeJs(data.answer) || 'No answer returned.', at: data.generated_at }, ...t].slice(0, 3));
      } catch (e) {
        setOffline(true);
      }
      setBusy(false);
    }

    return html`
      <div>
        <div class="ask-chips">
          ${CHIPS.map(c => html`
            <button key=${c} onClick=${() => ask(c)} disabled=${busy} class="ask-chip">
              ${c}
            </button>`)}
        </div>
        <div class="ask-row">
          <input ref=${inputRef} value=${q}
            onInput=${e => setQ(e.target.value)}
            onKeyDown=${e => { if (e.key === 'Enter') ask(q); }}
            placeholder="Ask about a country, a signal, or what to do next…"
            class="ask-input" />
          <button onClick=${() => ask(q)} disabled=${busy} class="btn btn-p ask-send">
            ${busy ? 'Asking…' : 'Ask'}
          </button>
        </div>
        ${busy && html`
          <div class="ask-busy rise-in">
            <span class="ask-dot"></span>
            <span class="ask-dot"></span>
            <span class="ask-dot"></span>
            pulling today's files
          </div>`}
        ${offline && html`
          <div class="ask-offline rise-in">
            The desk can't be reached from this copy of the page — try the live site at abeng.vercel.app.
          </div>`}
        ${thread.map((m, i) => html`
          <div key=${m.at + m.q} class="ask-answer rise-in ${i > 0 ? 'older' : 'ans-sweep'}">
            <div class="ask-q">You asked · ${m.q}</div>
            <div class="ask-a">
              ${i === 0 ? html`<${Typewriter} text=${m.a} />` : m.a}
            </div>
          </div>`)}
        ${!thread.length && !busy && !offline && html`
          <div class="ask-note">Every answer is pulled word-for-word from this cycle's files — so you can always check the receipts.</div>`}
      </div>`;
  }

  const askRoot = document.getElementById('ask-desk-root');
  if (askRoot) ReactDOM.createRoot(askRoot).render(html`<${AskDesk} />`);
}
