// React islands for the homepage brief. Each wraps an interior.dev component
// (src/components/interior, copied from the library unchanged) and adapts it
// to the page; Abeng's paper/ink/teal skin lives in src/pages/index.astro.
import { useEffect, useRef, useState } from "react";
import { TextReveal } from "../interior/text-reveal";
import { ShowMore } from "../interior/show-more";
import { ScrollSpy, type ScrollSpySection } from "../interior/scroll-spy";
import { ReadingProgress } from "../interior/reading-progress";
import { useHideOnScroll } from "../interior/hide-on-scroll";
import { StreamingText } from "../interior/streaming-text";
import { CommandPalette, type CommandItem } from "../interior/command-palette";
import { BlurUpImage } from "../interior/blur-up-image";

export function LeadReveal({ text }: { text: string }) {
  return <TextReveal text={text} startOnView={false} className="bm-reveal" />;
}

export function EvidenceMore({ text }: { text: string }) {
  return (
    <ShowMore lines={4} moreLabel="Show the full evidence" lessLabel="Show less" label="Evidence" className="bm-showmore">
      <p>{text}</p>
    </ShowMore>
  );
}

// ScrollSpy scrolls its active chip into view on mount, which moves the
// browser's Tab starting point (and, where the rail sits below the fold on a
// phone, scrolls the page). So: desktop only, mounted after the first scroll,
// with its row reserved so nothing shifts.
export function BriefSpy({ sections }: { sections: ScrollSpySection[] }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!matchMedia("(min-width: 961px)").matches) return;
    const onScroll = () => { setShow(true); removeEventListener("scroll", onScroll); };
    addEventListener("scroll", onScroll, { passive: true });
    return () => removeEventListener("scroll", onScroll);
  }, []);
  return (
    <div className="bm-spy-slot">
      {show ? <ScrollSpy sections={sections} offset={110} label="On this page" className="bm-spy" /> : null}
    </div>
  );
}

// Progress through the reading column, not the whole page.
export function BriefProgress({ words }: { words: number }) {
  const target = useRef<HTMLElement | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    target.current = document.querySelector<HTMLElement>(".bm-column");
    setReady(true);
  }, []);
  if (!ready) return null;
  return <ReadingProgress target={target} words={words} label="Briefing read" doneLabel="Done" className="bm-readprog" />;
}

// No ref attached → the hook watches the window. Hides the masthead on
// phones only; it is layout state, so reduced motion only drops the slide.
export function MastHider() {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = matchMedia("(max-width: 759px)");
    const sync = () => setNarrow(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  const { hidden } = useHideOnScroll<HTMLElement>({ disabled: !narrow, topGuard: 120 });
  useEffect(() => {
    document.getElementById("bm-mast")?.classList.toggle("is-hidden", narrow && hidden);
  }, [narrow, hidden]);
  return null;
}

// Ask the desk: deterministic answers from /api/ask, paced by StreamingText.
// The ⌘K palette hands questions over with a `bm-ask` event.
export function AskDesk() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const ask = async (question: string) => {
    if (!question || busy) return;
    setBusy(true);
    setAnswer(null);
    try {
      const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setAnswer(String(data.answer || "No answer came back for that."));
    } catch {
      setAnswer("The desk is not reachable from this copy of the page. The full desk has every country and source.");
    }
    setBusy(false);
  };
  useEffect(() => {
    const onAsk = (e: Event) => {
      const text = (e as CustomEvent<string>).detail || "";
      setQ(text);
      input.current?.focus();
      if (text) ask(text);
    };
    addEventListener("bm-ask", onAsk);
    return () => removeEventListener("bm-ask", onAsk);
  });
  return (
    <form className="bm-askbox" id="bm-askbox" onSubmit={(e) => { e.preventDefault(); ask(q.trim()); }}>
      <label className="bm-label" htmlFor="bm-ask-input">Ask the desk</label>
      <div className="bm-ask-row">
        <input id="bm-ask-input" ref={input} value={q} onChange={(e) => setQ(e.target.value)} type="text" autoComplete="off" placeholder="What changed in Guyana?" />
        <button type="submit" aria-label="Ask">›</button>
      </div>
      <p className="bm-fine">Answers come from this cycle's files, with sources.</p>
      {busy ? <p className="bm-answer is-busy">Checking this cycle’s files…</p> : null}
      {answer ? <StreamingText key={answer} text={answer} tokensPerSecond={60} label="The desk's answer" className="bm-answer" /> : null}
    </form>
  );
}

type Country = { name: string; href: string; status: string };

export function Palette({ countries }: { countries: Country[] }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);
  const items: CommandItem[] = [
    { id: "ask", label: "Ask the desk a question", hint: "Answer", keywords: "ask question what why how" },
    { id: "lead", label: "Read the lead briefing", hint: "Brief", keywords: "lead briefing" },
    ...countries.map((c) => ({ id: `c:${c.href}`, label: c.name, hint: c.status, keywords: "country" })),
    { id: "desk", label: "Open the full desk", hint: "Page", keywords: "desk map news wire" },
  ];
  const onSelect = (item: CommandItem) => {
    setOpen(false);
    if (item.id === "ask") { document.getElementById("bm-askbox")?.scrollIntoView({ block: "center" }); dispatchEvent(new CustomEvent("bm-ask", { detail: "" })); }
    else if (item.id === "lead") document.getElementById("brief-lead")?.scrollIntoView();
    else if (item.id === "desk") location.href = "/desk";
    else location.href = item.id.slice(2);
  };
  return (
    <>
      <button type="button" className="bm-ask-btn" id="bm-palette-open" aria-haspopup="dialog" onClick={() => setOpen(true)}>
        Ask or jump <kbd>⌘K</kbd>
      </button>
      <CommandPalette open={open} items={items} onSelect={onSelect} onDismiss={() => setOpen(false)} placeholder="Type a country, or ask the desk" label="Ask the desk or jump to a country" className="bm-palette" />
    </>
  );
}

export function GroundImage({ src }: { src: string }) {
  return <BlurUpImage src={src} alt="" width={400} height={400} className="bm-post-img" />;
}
