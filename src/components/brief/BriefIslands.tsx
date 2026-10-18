// React islands for the homepage brief: the three interior.dev components that
// earn their weight (Jev, 18 Oct). Each wraps a library component
// (src/components/interior, copied from the library unchanged) and adapts it
// to the page; Abeng's paper/ink/teal skin lives in src/pages/index.astro.
import { useEffect, useRef, useState } from "react";
import { ShowMore } from "../interior/show-more";
import { StreamingText } from "../interior/streaming-text";
import { CommandPalette, type CommandItem } from "../interior/command-palette";

export function EvidenceMore({ text }: { text: string }) {
  return (
    <ShowMore lines={4} moreLabel="Show the full evidence" lessLabel="Show less" label="Evidence" className="bm-showmore">
      <p>{text}</p>
    </ShowMore>
  );
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
