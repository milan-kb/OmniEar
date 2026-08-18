import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/acoustic/AppShell";
import { SpatialMap } from "@/components/acoustic/SpatialMap";
import { FLEET, fmtTime } from "@/lib/acoustic/data";
import { useAlertStore } from "@/lib/acoustic/store";
import type { NodeUnit } from "@/lib/acoustic/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/map")({
  head: () => ({
    meta: [
      { title: "Node Network Map — OmniEar" },
      {
        name: "description",
        content:
          "A simulated OmniEar fleet map with live WebSocket alert overlays from the working acoustic pipeline.",
      },
      { property: "og:title", content: "Node Network Map — OmniEar" },
      {
        property: "og:description",
        content: "A proposed city sensing layer with live structured alert overlays.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: NetworkMap,
});

type Filters = {
  fixed: boolean;
  personal: boolean;
  solar: boolean;
  grid: boolean;
  online: boolean;
  tamper: boolean;
  offline: boolean;
};

function Toggle({
  on,
  onClick,
  label,
  dot,
}: {
  on: boolean;
  onClick: () => void;
  label: string;
  dot?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[11px] transition-colors",
        on ? "bg-white/10 text-foreground" : "text-muted-foreground hover:bg-white/5",
      )}
    >
      {dot && <span className="size-2 rounded-full" style={{ background: dot }} />}
      {label}
    </button>
  );
}

function NetworkMap() {
  const alerts = useAlertStore((s) => s.alerts);
  const liveAlerts = useMemo(() => alerts.filter((alert) => alert.status !== "resolved"), [alerts]);
  const [f, setF] = useState<Filters>({
    fixed: true,
    personal: true,
    solar: true,
    grid: true,
    online: true,
    tamper: true,
    offline: true,
  });
  const [sel, setSel] = useState<NodeUnit | null>(null);

  const nodes = useMemo(
    () =>
      FLEET.filter((n) => {
        if (n.type === "fixed" && !f.fixed) return false;
        if (n.type === "personal" && !f.personal) return false;
        if (n.power_mode === "solar" && !f.solar) return false;
        if (n.power_mode === "grid" && !f.grid) return false;
        if (!n.online) return f.offline;
        if (n.tamper_flagged) return f.tamper;
        return f.online;
      }),
    [f],
  );

  const t = (k: keyof Filters) => () => setF((p) => ({ ...p, [k]: !p[k] }));

  return (
    <AppShell>
      <div className="relative h-[calc(100vh-3.5rem)]">
        <SpatialMap
          nodes={nodes}
          alerts={liveAlerts}
          showNodeLabels
          mapPaddingLeft={230}
          selectedNodeId={sel?.id ?? null}
          onSelectNode={setSel}
          className="absolute inset-0 rounded-none border-0"
        />

        <aside className="glass absolute left-3 top-3 z-30 w-[210px] rounded-xl p-2">
          <h2 className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
            Layers · demo fleet
          </h2>
          <Toggle on={f.fixed} onClick={t("fixed")} label="Fixed pole nodes" dot="var(--signal)" />
          <Toggle
            on={f.personal}
            onClick={t("personal")}
            label="Personal / keychain"
            dot="var(--p4)"
          />
          <h2 className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
            Power mode
          </h2>
          <Toggle on={f.solar} onClick={t("solar")} label="Solar" />
          <Toggle on={f.grid} onClick={t("grid")} label="Grid" />
          <h2 className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
            Status
          </h2>
          <Toggle on={f.online} onClick={t("online")} label="Online" dot="var(--signal)" />
          <Toggle on={f.tamper} onClick={t("tamper")} label="Tamper-flagged" dot="var(--p1)" />
          <Toggle
            on={f.offline}
            onClick={t("offline")}
            label="Offline"
            dot="rgba(255,255,255,.3)"
          />
          <p className="mono px-2 pb-1 pt-3 text-[10px] text-muted-foreground">
            {nodes.length}/{FLEET.length} shown
          </p>
        </aside>

        {sel && (
          <aside className="glass-raised absolute bottom-3 right-3 z-30 w-[280px] rounded-xl p-4">
            <div className="flex items-start justify-between">
              <h2 className="mono text-sm">NODE {sel.id}</h2>
              <button
                type="button"
                onClick={() => setSel(null)}
                className="text-[11px] text-muted-foreground hover:text-foreground"
              >
                close
              </button>
            </div>
            <dl className="mono mt-3 space-y-1.5 text-[11px] text-muted-foreground">
              <div className="flex justify-between">
                <dt>coords</dt>
                <dd className="text-foreground">
                  {sel.lat.toFixed(4)}, {sel.lng.toFixed(4)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt>power</dt>
                <dd className="text-foreground">{sel.power_mode}</dd>
              </div>
              <div className="flex justify-between">
                <dt>battery</dt>
                <dd className="text-foreground">
                  {sel.battery_pct === null ? "—" : `${sel.battery_pct}%`}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt>heartbeat</dt>
                <dd className="text-foreground">{fmtTime(sel.last_heartbeat)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>status</dt>
                <dd className="text-foreground">
                  {!sel.online ? "offline" : sel.tamper_flagged ? "tamper-flagged" : "online"}
                </dd>
              </div>
            </dl>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
