import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { CLASS_META, LABEL_META, type Alert } from "@/lib/acoustic/types";
import { FLEET, fmtTime } from "@/lib/acoustic/data";
import { SpatialMap } from "./SpatialMap";
import { useReducedMotion } from "./Waveform";

export function IncidentDrawer({
  alert,
  onClose,
  onAck,
  onResolve,
}: {
  alert: Alert | null;
  onClose: () => void;
  onAck: (id: string) => void;
  onResolve: (id: string) => void;
}) {
  const reduced = useReducedMotion();
  const node = alert ? FLEET.find((n) => String(n.id) === alert.node_id) : null;
  const meta = alert ? CLASS_META[alert.class] : null;
  const labelMeta = alert ? LABEL_META[alert.label] : null;
  const alertId = alert ? (alert.id ?? `${alert.node_id}-${alert.timestamp}`) : "";

  const payload = alert
    ? {
        node_id: alert.node_id,
        timestamp: alert.timestamp,
        class: alert.class,
        label: alert.label,
        confidence: alert.confidence,
        lat: alert.lat,
        lng: alert.lng,
      }
    : null;

  return (
    <AnimatePresence>
      {alert && meta && labelMeta && (
        <motion.aside
          role="dialog"
          aria-label={`Incident ${alertId}`}
          initial={reduced ? { opacity: 0 } : { x: "100%" }}
          animate={reduced ? { opacity: 1 } : { x: 0 }}
          exit={reduced ? { opacity: 0 } : { x: "100%" }}
          transition={{ type: "tween", duration: 0.24, ease: "easeOut" }}
          className="glass-raised fixed inset-y-0 right-0 z-[60] flex w-full max-w-[420px] flex-col overflow-y-auto"
        >
          <header className="flex items-start gap-3 border-b border-white/10 p-4">
            <span
              className="mt-1 size-2.5 shrink-0 rounded-full"
              style={{ background: meta.color, boxShadow: `0 0 12px ${meta.color}` }}
            />
            <div className="min-w-0 flex-1">
              <p className="mono text-[11px]" style={{ color: meta.color }}>
                {meta.priority} · {labelMeta.label}
              </p>
              <h2 className="mono truncate text-sm">{alertId}</h2>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                Routed to {labelMeta.routeTo}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close incident"
              className="rounded-md p-1.5 text-muted-foreground hover:bg-white/10 hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </header>

          <dl className="mono grid grid-cols-2 gap-px bg-white/5 text-[11px]">
            {[
              ["node", `#${alert.node_id}`],
              ["confidence", alert.confidence.toFixed(2)],
              ["lat", alert.lat.toFixed(5)],
              ["lng", alert.lng.toFixed(5)],
              ["timestamp", fmtTime(alert.timestamp)],
              ["status", alert.status],
            ].map(([k, v]) => (
              <div key={k} className="bg-void/40 px-4 py-2.5">
                <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{k}</dt>
                <dd className="mt-0.5 text-foreground">{v}</dd>
              </div>
            ))}
          </dl>

          <div className="p-4">
            <p className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
              Node vicinity
            </p>
            <SpatialMap
              compact
              nodes={FLEET.filter(
                (n) => Math.abs(n.lat - alert.lat) < 0.03 && Math.abs(n.lng - alert.lng) < 0.035,
              )}
              alerts={[alert]}
              selectedNodeId={node?.id ?? null}
              className="h-40"
            />
          </div>

          <div className="px-4 pb-4">
            <p className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
              Exact structured payload received — no audio
            </p>
            <pre className="mono overflow-x-auto rounded-lg border border-white/10 bg-void/70 p-3 text-[11px] leading-relaxed text-signal">
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>

          <div className="mt-auto flex gap-2 border-t border-white/10 p-4">
            <button
              type="button"
              onClick={() => onAck(alertId)}
              disabled={alert.status !== "new"}
              className="flex-1 rounded-md border border-white/15 bg-white/5 px-3 py-2 text-xs hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {alert.status === "new" ? "Acknowledge" : "Acknowledged"}
            </button>
            <button
              type="button"
              onClick={() => onResolve(alertId)}
              disabled={alert.status === "resolved"}
              className="flex-1 rounded-md bg-signal px-3 py-2 text-xs font-medium text-void hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {alert.status === "resolved" ? "Resolved" : "Resolve"}
            </button>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
