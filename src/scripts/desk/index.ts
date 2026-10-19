// Entry for the /desk page. Every module only declares; the inits run here in
// the order the page's former inline script ran them, so listener order and
// first paint are unchanged.
import { initTheater } from './theater.ts';
import { initNewsFilters, initNewsCountryToggle } from './news.ts';
import { initAnchorReveal } from './nav.ts';
import { initGuide } from './guide.ts';
import { initLensSelect, paintLens, paintFollows } from './prefs.ts';
import { initRegionalMovement } from './movement.ts';
import { initMap, openCountryDrill } from './map.ts';
import { initLeadRisk, initChecklist, initOutputs, toggleDeep, deskAsk } from './workspace.ts';
import { initChartReadouts } from './market.ts';
import { initAskDesk } from './ask.ts';
import { initEngineCards, initReceipts, initCycleClock } from './receipts.ts';
import { initMotion } from './motion.ts';

// Reached from markup (onclick="toggleDeep()") and from e2e tests.
window.toggleDeep = toggleDeep;
window.ask = deskAsk;
window.openCountryDrill = openCountryDrill;

initTheater();
initNewsFilters();
initAnchorReveal();
initGuide();
initLensSelect();
initRegionalMovement();
initMap();
initLeadRisk();
initChecklist();
paintLens();
paintFollows();
initChartReadouts();
initNewsCountryToggle();
initOutputs();
initAskDesk();
initEngineCards();
initReceipts();
initCycleClock();
initMotion();
