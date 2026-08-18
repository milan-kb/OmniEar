import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/acoustic/AppShell";
import { NodeCard } from "@/components/acoustic/NodeCard";
import { FLEET } from "@/lib/acoustic/data";
import type { NodeUnit } from "@/lib/acoustic/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/fleet")({
  head: () => ({
    meta: [
      { title: "Hardware Admin — OmniEar" },
      {
        name: "description",
        content:
          "A simulated fleet-health view for the OmniEar hardware concept, including battery, GSM, tamper and power-mode states.",
      },
      { property: "og:title", content: "Hardware Admin — OmniEar" },
      {
        property: "og:description",
        content: "Tactile hardware console for the acoustic node fleet.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "/fleet" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [{ rel: "canonical", href: "/fleet" }],
  }),
  component: Fleet,
});

const FILTERS = ["all", "online", "offline", "tamper", "low battery"] as const;
type Filter = (typeof FILTERS)[number];

function Fleet() {
  const [nodes, setNodes] = useState<NodeUnit[]>(FLEET);
  const [filter, setFilter] = useState<Filter>("all");

  const shown = useMemo(
    () =>
      nodes.filter((n) => {
        if (filter === "online") return n.online;
        if (filter === "offline") return !n.online;
        if (filter === "tamper") return n.tamper_flagged;
        if (filter === "low battery") return (n.battery_pct ?? 100) < 45;
        return true;
      }),
    [nodes, filter],
  );

  const stats = useMemo(() => {
    const fixed = nodes.filter((n) => n.type === "fixed");
    return {
      total: nodes.length,
      online: nodes.filter((n) => n.online).length,
      solar: fixed.filter((n) => n.power_mode === "solar").length,
      tamper: nodes.filter((n) => n.tamper_flagged).length,
    };
  }, [nodes]);

  const toggle = (id: number) =>
    setNodes((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, power_mode: n.power_mode === "solar" ? "grid" : "solar" } : n,
      ),
    );

  return (
    <AppShell>
      <div className="mx-auto max-w-[1400px] px-4 py-8">
        <header>
          <p className="mono text-[11px] uppercase tracking-[0.24em] text-signal">
            hardware admin · simulated telemetry
          </p>
          <h1 className="font-display mt-2 text-3xl tracking-tight">Node fleet</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Demonstration data for the proposed pole fleet. The current Python pipeline does not
            emit battery, GSM, heartbeat or tamper telemetry.
          </p>
        </header>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["nodes", stats.total],
            ["online", stats.online],
            ["on solar", stats.solar],
            ["tamper flags", stats.tamper],
          ].map(([label, v]) => (
            <div key={label as string} className="neo rounded-xl p-4">
              <p className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {label}
              </p>
              <p className="mono mt-1 text-2xl">{v}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Filter nodes">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              aria-pressed={filter === f}
              className={cn(
                "mono rounded-full px-3 py-1.5 text-[11px] transition-colors",
                filter === f ? "neo-inset text-signal" : "neo text-muted-foreground",
              )}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {shown.map((n) => (
            <NodeCard key={n.id} node={n} onToggle={toggle} />
          ))}
        </div>
        {shown.length === 0 && (
          <p className="mono mt-10 text-center text-xs text-muted-foreground">
            no nodes match this filter
          </p>
        )}
      </div>
    </AppShell>
  );
}
