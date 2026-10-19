// Watch the desk work: live SSE feed when a local API is up, otherwise a
// replay of the recorded cycle.
import { escapeMapText } from './util.ts';

let theaterSource = null;
let theaterPaused = false;
let theaterReplayAttempted = false;
let theaterReplayMode = false;
let theaterBuffer = [];

function theaterTime(ts) {
  return new Date((ts || Date.now() / 1000) * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}

function renderTheaterEvent(type, data) {
  if (theaterPaused) {
    theaterBuffer.push([type, data]);
    return;
  }
  const feed = document.getElementById('theater-feed');
  const row = document.createElement('div');
  const eventClass = {source_check:'source', signal_found:'signal', dispatch_routed:'dispatch', cycle_complete:'cycle'}[type] || 'source';
  row.className = 'theater-event event-' + eventClass;
  const time = '<span class="theater-time">' + theaterTime(data.ts) + '</span>';
  if (type === 'source_check') {
    const sourceState = { polling: 'checking now', complete: 'checked', error: 'no answer',
                          failed: 'no answer', skipped: 'skipped' }[data.status] || data.status;
    row.innerHTML = time + '<p><span>' + escapeMapText(data.source) + ' ↻</span> ' + escapeMapText(sourceState) + '</p>';
  } else if (type === 'signal_found') {
    const color = MAP_COLORS[data.kind] || MAP_COLORS.none;
    row.innerHTML = time + '<p><span style="background:' + color + '">' + escapeMapText(data.label || data.kind) + '</span><strong>' + escapeMapText(data.country) + '</strong> · ' + escapeMapText(data.confidence) + '% · ' + escapeMapText(humanizeJs(data.summary)) + '</p>';
  } else if (type === 'dispatch_routed') {
    row.innerHTML = time + '<p><strong>' + escapeMapText(data.recipient) + '</strong> · ' + escapeMapText(data.country) + ' <code>' + escapeMapText(data.dispatch_id) + '</code></p>';
  } else {
    row.innerHTML = '<p>Done — ' + escapeMapText(data.signals) + ' signals found this cycle</p>';
  }
  feed.appendChild(row);
  while (feed.children.length > 50) feed.firstElementChild.remove();
  feed.scrollTop = feed.scrollHeight;
}

function setTheaterMode(mode) {
  const badge = document.getElementById('stream-mode');
  badge.textContent = mode;
  badge.className = 'stream-mode ' + mode.toLowerCase();
}

async function runReplayFromJsonl(jsonlUrl) {
  setTheaterMode('Replay (recorded cycle)');
  theaterReplayMode = true;
  try {
    const res = await fetch(jsonlUrl);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    const lines = text.trim().split('\n').filter(l => l);
    const events = lines.map(l => JSON.parse(l));
    if (!events.length) {
      setTheaterMode('PAUSED');
      return;
    }
    const firstTs = events[0].data?.ts * 1000;
    const startWall = Date.now();
    for (const ev of events) {
      if (theaterPaused) break;
      const evTs = ev.data?.ts * 1000;
      const targetWall = startWall + (evTs - firstTs) / 10;
      const delay = Math.max(0, targetWall - Date.now());
      if (delay > 0) await new Promise(r => setTimeout(r, delay));
      if (theaterPaused) break;
      renderTheaterEvent(ev.event, ev.data);
    }
    setTheaterMode('Replay (recorded cycle)');
  } catch (e) {
    console.warn('Replay failed:', e);
    runReplayFromEmbeddedEvents();
  }
}

async function runReplayFromEmbeddedEvents() {
  if (!Array.isArray(THEATER_EVENTS) || !THEATER_EVENTS.length) {
    setTheaterMode('PAUSED');
    return;
  }
  theaterReplayMode = true;
  setTheaterMode('Replay (recorded cycle)');
  const feed = document.getElementById('theater-feed');
  if (feed) feed.innerHTML = '';
  for (let i = 0; i < THEATER_EVENTS.length; i++) {
    if (theaterPaused) break;
    const ev = THEATER_EVENTS[i];
    renderTheaterEvent(ev.event, ev.data || {});
    await new Promise(r => setTimeout(r, i < 6 ? 420 : 650));
  }
  if (!theaterPaused) setTheaterMode('Replay (recorded cycle)');
}

function connectTheater(replay) {
  if (theaterSource) theaterSource.close();
  const hasLocalApi = ['localhost', '127.0.0.1', '::1'].includes(location.hostname) && location.port !== '4321';
  if (!hasLocalApi) {
    runReplayFromEmbeddedEvents();
    return;
  }
  setTheaterMode(replay ? 'REPLAY' : 'LIVE');
  theaterSource = new EventSource('/api/pipeline/stream' + (replay ? '?replay=1' : ''));
  ['source_check','signal_found','dispatch_routed','cycle_complete'].forEach(type => {
    theaterSource.addEventListener(type, event => {
      try { renderTheaterEvent(type, JSON.parse(event.data)); } catch (_) {}
    });
  });
  theaterSource.onerror = () => {
    theaterSource.close();
    if (!replay && !theaterReplayAttempted) {
      theaterReplayAttempted = true;
      connectTheater(true);
      return;
    }
    if (REPLAY_JSONL_URL && REPLAY_JSONL_URL !== "") {
      runReplayFromJsonl(REPLAY_JSONL_URL);
    } else {
      fetch('/data/history/index.json')
        .then(r => r.ok ? r.json() : null)
        .then(idx => {
          if (idx?.cycles?.length) {
            const latest = idx.cycles[0];
            const dateStr = latest.cycleId.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3');
            runReplayFromJsonl('/data/history/' + dateStr + '.jsonl');
          } else {
            runReplayFromEmbeddedEvents();
          }
        })
        .catch(() => runReplayFromEmbeddedEvents());
    }
  };
}

export function initTheater(): void {
  document.getElementById('theater-toggle').addEventListener('click', event => {
    theaterPaused = !theaterPaused;
    event.currentTarget.textContent = theaterPaused ? 'Resume' : 'Pause';
    if (theaterPaused) {
      setTheaterMode(theaterReplayMode ? 'Replay (recorded cycle)' : 'PAUSED');
    } else {
      if (theaterReplayMode) {
        setTheaterMode('Replay (recorded cycle)');
        if (REPLAY_JSONL_URL && REPLAY_JSONL_URL !== "") {
          runReplayFromJsonl(REPLAY_JSONL_URL);
        }
      } else {
        setTheaterMode(theaterReplayAttempted ? 'REPLAY' : 'LIVE');
        const pending = theaterBuffer.splice(0);
        pending.forEach(([type, data]) => renderTheaterEvent(type, data));
      }
    }
  });
  connectTheater(false);
}
