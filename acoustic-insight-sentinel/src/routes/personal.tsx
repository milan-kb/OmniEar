import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { BluetoothConnected, ShieldCheck, Waves } from "lucide-react";
import { AppShell } from "@/components/acoustic/AppShell";
import { Waveform } from "@/components/acoustic/Waveform";
import { FLEET, fmtTime } from "@/lib/acoustic/data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/personal")({
  head: () => ({
    meta: [
      { title: "Personal Node — OmniEar" },
      {
        name: "description",
        content:
          "A simulated companion view for the proposed pocket acoustic node and its privacy-preserving JSON alert.",
      },
      { property: "og:title", content: "Personal Node — OmniEar" },
      {
        property: "og:description",
        content: "A pocket-sized relay for the city acoustic network.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "/personal" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [{ rel: "canonical", href: "/personal" }],
  }),
  component: Personal,
});

function Personal() {
  const node = FLEET.find((n) => n.type === "personal")!;
  const [armed, setArmed] = useState(true);
  const [now, setNow] = useState("--:--:--");

  useEffect(() => {
    const t = window.setInterval(() => setNow(fmtTime(new Date().toISOString())), 1000);
    setNow(fmtTime(new Date().toISOString()));
    return () => window.clearInterval(t);
  }, []);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-[420px] px-4 py-8">
        <header className="flex items-baseline justify-between">
          <div>
            <p className="mono text-[10px] uppercase tracking-[0.2em] text-p4">concept demo</p>
            <h1 className="font-display mt-1 text-2xl tracking-tight">Personal node</h1>
          </div>
          <span className="mono text-[11px] text-muted-foreground">{now}</span>
        </header>

        <section className="glass mt-5 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
                relay status
              </p>
              <p
                className={cn(
                  "font-display mt-1 text-xl",
                  armed ? "text-signal" : "text-muted-foreground",
                )}
              >
                {armed ? "Listening on-device" : "Paused"}
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={armed}
              aria-label="Arm personal node"
              onClick={() => setArmed((v) => !v)}
              className={cn(
                "neo-inset h-8 w-14 rounded-full p-1 transition-colors",
                armed && "shadow-[inset_0_0_12px_rgba(63,224,197,0.35)]",
              )}
            >
              <span
                className={cn(
                  "block size-6 rounded-full transition-transform",
                  armed ? "translate-x-6 bg-signal" : "bg-muted-foreground/60",
                )}
              />
            </button>
          </div>
          <Waveform idle={!armed} amplitude={armed ? 1 : 0.2} height={90} className="mt-4" />
        </section>

        <section className="mt-4 grid grid-cols-2 gap-3">
          <div className="neo rounded-xl p-4">
            <p className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
              simulated link
            </p>
            <p className="mono mt-1 flex items-center gap-1.5 text-sm text-signal">
              <BluetoothConnected className="size-3.5" aria-hidden /> BLE ready
            </p>
          </div>
          <div className="neo rounded-xl p-4">
            <p className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
              node id
            </p>
            <p className="mono mt-1 text-sm">{node.id}</p>
          </div>
        </section>

        <section className="glass mt-4 rounded-2xl p-5">
          <h2 className="flex items-center gap-2 text-sm font-medium">
            <ShieldCheck className="size-4 text-signal" aria-hidden /> What your phone would send
          </h2>
          <pre className="mono mt-3 overflow-x-auto rounded-lg bg-black/40 p-3 text-[11px] leading-relaxed text-muted-foreground">
            {JSON.stringify(
              {
                node_id: `AE-P-${node.id}`,
                timestamp: "2026-08-16T18:41:02Z",
                class: "P0",
                label: "scream_distress",
                confidence: 0.94,
                lat: +node.lat.toFixed(5),
                lng: +node.lng.toFixed(5),
              },
              null,
              2,
            )}
          </pre>
          <p className="mt-3 flex gap-2 text-[11px] leading-relaxed text-muted-foreground">
            <Waves className="mt-0.5 size-3 shrink-0 text-p4" aria-hidden />
            Classification happens in the pocket unit. The phone is a radio, not a microphone.
          </p>
        </section>
      </div>
    </AppShell>
  );
}
