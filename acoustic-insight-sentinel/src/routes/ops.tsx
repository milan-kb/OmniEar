import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Pause, Play } from "lucide-react";
import { AppShell } from "@/components/acoustic/AppShell";
import { AlertFeed } from "@/components/acoustic/AlertFeed";
import { IncidentDrawer } from "@/components/acoustic/IncidentDrawer";
import { SpatialMap } from "@/components/acoustic/SpatialMap";
import { useReducedMotion } from "@/components/acoustic/Waveform";
import { FLEET, sinceLabel } from "@/lib/acoustic/data";
import { CLASS_META } from "@/lib/acoustic/types";
import { useAlertStore } from "@/lib/acoustic/store";

export const Route = createFileRoute("/ops")({
  head: () => ({
    meta: [
      { title: "Operations Command — OmniEar" },
      {
        name: "description",
        content:
          "Live acoustic alert feed over a spatial node map. Distress, explosion, impact and traffic-siren events arrive as JSON over WebSocket.",
      },
      { property: "og:title", content: "Operations Command — OmniEar" },
      {
        property: "og:description",
        content: "Night-ops control room for a city-wide edge-AI acoustic sensor network.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Ops,
});

function Ops() {
  const alerts = useAlertStore((s) => s.alerts);
  const toggleRunning = useAlertStore((s) => s.toggleRunning);
  const running = useAlertStore((s) => s.running);
  const connectionStatus = useAlertStore((s) => s.connectionStatus);
  const lastP0 = useAlertStore((s) => s.lastP0);
  const selectedId = useAlertStore((s) => s.selectedId);
  const select = useAlertStore((s) => s.select);
  const setStatus = useAlertStore((s) => s.setStatus);
  const push = useAlertStore((s) => s.push);
  const reduced = useReducedMotion();
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (!lastP0) return;
    setFlash(true);
    const t = setTimeout(() => setFlash(false), 1600);
    return () => clearTimeout(t);
  }, [lastP0]);

  const active = useMemo(() => alerts.filter((alert) => alert.status !== "resolved"), [alerts]);
  const selectedAlert = useMemo(
    () => alerts.find((alert) => `${alert.node_id}-${alert.timestamp}` === selectedId) ?? null,
    [alerts, selectedId],
  );

  const counts = useMemo(() => {
    const c = { P0: 0, P1: 0, P4: 0 };
    active.forEach((alert) => {
      if (alert.priority === "P0") c.P0++;
      else if (alert.priority === "P1") c.P1++;
      else c.P4++;
    });
    return c;
  }, [active]);

  const fleetStats = useMemo(() => {
    const online = FLEET.filter((n) => n.online).length;
    const tamper = FLEET.filter((n) => n.tamper_flagged).length;
    const offlineNode = FLEET.find((n) => !n.online);
    return { online, total: FLEET.length, tamper, offlineNode };
  }, []);

  const addTestAlert = () => {
    push({
      node_id: "DEMO-01",
      timestamp: new Date().toISOString(),
      class: "P0",
      label: "scream_distress",
      confidence: 0.92,
      lat: 12.9716,
      lng: 77.5946,
      priority: "P0",
    });
  };

  return (
    <AppShell>
      <div className="relative h-[calc(100vh-3.5rem)] w-full">
        <SpatialMap
          nodes={FLEET}
          alerts={active}
          selectedNodeId={null}
          showNodeLabels
          mapPaddingLeft={380}
          className="absolute inset-0 rounded-none border-0"
        />

        <AnimatePresence>
          {flash && !reduced && (
            <motion.div
              key="p0flash"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 1, 0.3, 0] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.6 }}
              aria-hidden
              className="pointer-events-none absolute inset-0 z-40"
              style={{ boxShadow: "inset 0 0 140px 24px var(--p0)" }}
            />
          )}
        </AnimatePresence>

        <div aria-live="assertive" role="status" className="sr-only">
          {lastP0
            ? `P0 distress detected. Node ${lastP0.node_id}. Confidence ${Math.round(
                lastP0.confidence * 100,
              )} percent. Routed to Police PCR.`
            : ""}
        </div>

        <div className="pointer-events-none absolute inset-x-0 top-0 z-30 flex flex-wrap gap-2 p-3 sm:p-4">
          {(
            [
              ["P0", counts.P0, "var(--p0)", "distress → PCR"],
              ["P1", counts.P1, "var(--p1)", "impact / crash"],
              ["P4", counts.P4, "var(--p4)", "traffic monitoring"],
            ] as const
          ).map(([k, v, c, sub]) => (
            <div key={k} className="glass pointer-events-auto rounded-xl px-3 py-2">
              <div className="flex items-baseline gap-2">
                <span className="mono text-lg" style={{ color: c }}>
                  {String(v).padStart(2, "0")}
                </span>
                <span className="mono text-[11px]" style={{ color: c }}>
                  {k}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground">{sub}</p>
            </div>
          ))}
          <button
            type="button"
            onClick={toggleRunning}
            className="glass pointer-events-auto ml-auto flex items-center gap-1.5 rounded-xl px-3 py-2 text-[11px] hover:bg-white/10"
          >
            {running ? <Pause className="size-3" /> : <Play className="size-3" />}
            {running ? `Live feed · ${connectionStatus}` : "Feed paused"}
          </button>
        </div>

        <div className="absolute inset-x-0 bottom-0 z-30 max-h-[48vh] p-3 sm:inset-y-auto sm:bottom-4 sm:left-4 sm:top-24 sm:max-h-none sm:w-[360px] sm:p-0">
          <section className="glass flex h-full max-h-[46vh] flex-col overflow-hidden rounded-xl sm:max-h-full">
            <header className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
              <h2 className="text-xs uppercase tracking-wider text-muted-foreground">
                Live alert feed
              </h2>
              <button
                type="button"
                onClick={addTestAlert}
                className="mono ml-auto rounded-full border border-white/10 px-2 py-1 text-[9px] uppercase tracking-wider text-muted-foreground hover:border-signal/40 hover:text-signal"
              >
                add test alert
              </button>
              <span className="mono text-[11px] text-signal">{active.length} active</span>
            </header>
            <div className="flex-1 overflow-y-auto">
              <AlertFeed
                alerts={active}
                selectedId={selectedId}
                onSelect={(alert) => select(`${alert.node_id}-${alert.timestamp}`)}
              />
            </div>
          </section>
        </div>

        <div className="glass absolute bottom-4 right-4 z-30 hidden items-center gap-4 rounded-xl px-4 py-2.5 lg:flex">
          <div>
            <p className="mono text-sm text-signal">
              {fleetStats.online}/{fleetStats.total}
            </p>
            <p className="text-[10px] text-muted-foreground">demo nodes reporting</p>
          </div>
          <div className="h-8 w-px bg-white/10" />
          <div>
            <p className="mono text-sm text-p1">{fleetStats.tamper}</p>
            <p className="text-[10px] text-muted-foreground">tamper-flagged</p>
          </div>
          {fleetStats.offlineNode && (
            <>
              <div className="h-8 w-px bg-white/10" />
              <p className="mono text-[11px] text-muted-foreground">
                Node {fleetStats.offlineNode.id} — offline{" "}
                {sinceLabel(fleetStats.offlineNode.last_heartbeat, Date.UTC(2026, 7, 15, 18, 45))}
              </p>
            </>
          )}
        </div>
      </div>
      <IncidentDrawer
        alert={selectedAlert}
        onClose={() => select(null)}
        onAck={(id) => setStatus(id, "acknowledged")}
        onResolve={(id) => {
          setStatus(id, "resolved");
          select(null);
        }}
      />
      <p className="sr-only">
        {Object.values(CLASS_META)
          .map((m) => `${m.priority} ${m.label} routes to ${m.routeTo}`)
          .join(". ")}
      </p>
    </AppShell>
  );
}
