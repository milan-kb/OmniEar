import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, Cpu, Lock, Radio, Sun, Waves } from "lucide-react";
import { AppShell } from "@/components/acoustic/AppShell";
import { Waveform } from "@/components/acoustic/Waveform";
import { CLASS_META, LABEL_META, type AcousticLabel } from "@/lib/acoustic/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "OmniEar — A city doesn't just need eyes." },
      {
        name: "description",
        content:
          "An edge-AI acoustic safety prototype that classifies screams, explosions, impacts and traffic sirens, then sends structured JSON alerts without transmitting audio.",
      },
      { property: "og:title", content: "OmniEar — A city doesn't just need eyes." },
      {
        property: "og:description",
        content:
          "Edge-AI acoustic sensing for cities. On-device classification, JSON-only alerts, zero raw audio.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "/" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [{ rel: "canonical", href: "/" }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Organization",
          name: "OmniEar",
          description:
            "Solar-powered edge-AI acoustic sensor network for municipal safety and noise analytics.",
        }),
      },
    ],
  }),
  component: Landing,
});

const PIPELINE = [
  { k: "capture", t: "16 kHz ring buffer", d: "A short in-memory window; never uploaded." },
  { k: "trigger", t: "Energy trigger", d: "A rolling baseline gates heavier inference." },
  {
    k: "features",
    t: "YAMNet embeddings",
    d: "Pretrained audio features from the loudest window.",
  },
  { k: "infer", t: "Classifier head", d: "Five classes with per-class alert thresholds." },
  { k: "emit", t: "WebSocket JSON", d: "Node, time, class, confidence and coordinates only." },
];

const EVIDENCE = [
  ["training clips", "10,138"],
  ["test accuracy", "89%"],
  ["macro F1", "0.89"],
  ["raw audio transmitted", "0 B"],
];

const LIMITS = [
  "Real-world false positives have not yet been validated in chaotic Indian streetscapes.",
  "Impact/crash and traffic-siren classes have less training data than the strongest classes.",
  "Pole hardware, cellular backhaul and solar power are product targets, not this laptop demo.",
  "No speech recognition, no speaker ID, no raw audio egress — by construction.",
];

function Landing() {
  const [morph, setMorph] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      setMorph(Math.max(0, Math.min(1, y / 520)));
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <AppShell>
      <section className="city-surface relative overflow-hidden">
        <div className="hairline-grid absolute inset-0 opacity-60" aria-hidden />
        <div className="relative mx-auto max-w-[1100px] px-4 pb-4 pt-20 sm:pt-28">
          <p className="mono text-[11px] uppercase tracking-[0.24em] text-signal">
            edge-ai acoustic sensing
          </p>
          <h1 className="font-display mt-4 text-4xl leading-[1.05] tracking-tight sm:text-6xl">
            A city doesn't just need eyes.
            <br />
            <span className="text-signal">It needs ears</span>
          </h1>
          <p className="mt-5 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            The working laptop prototype classifies distress screams, explosions, impacts and
            traffic sirens at the edge. Only a small structured alert leaves the device — never the
            waveform. Pole-mounted, solar hardware is the next deployment step.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/ops"
              className="inline-flex items-center gap-2 rounded-full bg-signal px-5 py-2.5 text-sm font-medium text-primary-foreground transition-transform hover:-translate-y-0.5"
            >
              Open operations <ArrowRight className="size-4" aria-hidden />
            </Link>
            <Link
              to="/map"
              className="glass inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm"
            >
              <Radio className="size-4 text-signal" aria-hidden /> See the node network
            </Link>
          </div>
        </div>
        <Waveform morph={morph} height={200} className="relative" />
      </section>

      <section className="mx-auto max-w-[1100px] px-4 py-16">
        <h2 className="font-display text-2xl tracking-tight">Detection pipeline</h2>
        <ol className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {PIPELINE.map((s, i) => (
            <li key={s.k} className="glass rounded-xl p-4">
              <span className="mono text-[10px] text-signal">0{i + 1}</span>
              <h3 className="mt-2 text-sm font-medium">{s.t}</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-[1100px] px-4 pb-16">
        <h2 className="font-display text-2xl tracking-tight">Routing table</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Each detected label has an explicit operator destination. Raw audio is never included.
        </p>
        <div className="glass mt-6 overflow-x-auto rounded-xl">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr className="border-b border-white/10">
                <th className="px-4 py-3">priority</th>
                <th className="px-4 py-3">class</th>
                <th className="px-4 py-3">routes to</th>
                <th className="px-4 py-3">payload</th>
              </tr>
            </thead>
            <tbody>
              {(Object.keys(LABEL_META) as AcousticLabel[]).map((k) => {
                const m = LABEL_META[k];
                const priority = CLASS_META[m.priority];
                return (
                  <tr key={k} className="border-b border-white/5 last:border-0">
                    <td className="px-4 py-3">
                      <span
                        className="mono rounded-full px-2 py-0.5 text-[10px]"
                        style={{
                          background: `color-mix(in oklab, ${priority.color} 18%, transparent)`,
                          color: priority.color,
                        }}
                      >
                        {m.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3">{m.label}</td>
                    <td className="px-4 py-3 text-muted-foreground">{m.routeTo}</td>
                    <td className="mono px-4 py-3 text-[11px] text-muted-foreground">
                      JSON · ~280 B
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mx-auto grid max-w-[1100px] gap-6 px-4 pb-24 lg:grid-cols-2">
        <div className="neo rounded-2xl p-6">
          <h2 className="font-display flex items-center gap-2 text-xl tracking-tight">
            <Cpu className="size-4 text-signal" aria-hidden /> Prototype evidence
          </h2>
          <ul className="mt-4 space-y-2">
            {EVIDENCE.map(([item, value]) => (
              <li key={item} className="mono flex justify-between text-xs">
                <span className="text-muted-foreground">{item}</span>
                <span>{value}</span>
              </li>
            ))}
          </ul>
          <p className="mono mt-4 flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Sun className="size-3" aria-hidden /> Solar pole hardware remains a deployment target
          </p>
        </div>
        <div className="glass rounded-2xl p-6">
          <h2 className="font-display flex items-center gap-2 text-xl tracking-tight">
            <Lock className="size-4 text-signal" aria-hidden /> Honest limitations
          </h2>
          <ul className="mt-4 space-y-3">
            {LIMITS.map((l) => (
              <li key={l} className="flex gap-2 text-xs leading-relaxed text-muted-foreground">
                <Waves className="mt-0.5 size-3 shrink-0 text-p4" aria-hidden />
                {l}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </AppShell>
  );
}
