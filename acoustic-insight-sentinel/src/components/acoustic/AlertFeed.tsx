import { AnimatePresence, motion } from "framer-motion";
import { fmtTime } from "@/lib/acoustic/data";
import { useAlertStore } from "@/lib/acoustic/store";
import { LABEL_META, type Alert } from "@/lib/acoustic/types";
import { cn } from "@/lib/utils";
import { Waveform, useReducedMotion } from "./Waveform";

const PRIORITY_STYLES = {
  P0: { color: "var(--p0)", accent: "Critical", label: "P0" },
  P1: { color: "var(--p1)", accent: "High", label: "P1" },
  P4: { color: "var(--p4)", accent: "Info", label: "P4" },
} as const;

function getPriorityStyle(priority: Alert["priority"]) {
  return PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.P4;
}

export function AlertRow({
  alert,
  onSelect,
  selected,
}: {
  alert: Alert;
  onSelect?: (a: Alert) => void;
  selected?: boolean;
}) {
  const reduced = useReducedMotion();
  const style = getPriorityStyle(alert.priority);
  const label = LABEL_META[alert.label].label;

  return (
    <motion.li
      layout={!reduced}
      initial={reduced ? false : { opacity: 0, x: -18, filter: "blur(6px)" }}
      animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
      transition={{ duration: alert.priority === "P0" ? 0.45 : 0.22, ease: "easeOut" }}
    >
      <button
        type="button"
        onClick={() => onSelect?.(alert)}
        className={cn(
          "glass group relative w-full overflow-hidden rounded-lg px-3 py-2.5 text-left transition-all hover:translate-y-[-1px] hover:bg-white/[0.1]",
          selected && "ring-1 ring-signal/60",
        )}
      >
        <span
          className="absolute inset-y-0 left-0 w-[3px]"
          style={{ background: style.color }}
          aria-hidden
        />
        <div className="flex items-center gap-2">
          <span className="relative flex size-2.5 items-center justify-center">
            {!reduced && alert.priority === "P0" && (
              <span
                className="ping-ring absolute size-2.5 rounded-full"
                style={{ background: style.color }}
                aria-hidden
              />
            )}
            <span className="size-2 rounded-full" style={{ background: style.color }} />
          </span>
          <span className="mono text-[11px] font-semibold" style={{ color: style.color }}>
            {style.label}
          </span>
          <span className="truncate text-xs text-foreground">{label}</span>
          <span className="mono ml-auto text-[11px] text-muted-foreground">
            {fmtTime(alert.timestamp)}
          </span>
        </div>
        <div className="mono mt-1.5 flex flex-wrap gap-x-3 text-[11px] text-muted-foreground">
          <span>NODE {alert.node_id}</span>
          <span>
            {alert.lat.toFixed(4)}, {alert.lng.toFixed(4)}
          </span>
          <span>conf {alert.confidence.toFixed(2)}</span>
          <span className="text-foreground/60">→ {style.accent}</span>
          <span
            className={cn(
              "ml-auto uppercase",
              alert.status === "new"
                ? "text-p0"
                : alert.status === "acknowledged"
                  ? "text-p1"
                  : "text-signal",
            )}
          >
            {alert.status}
          </span>
        </div>
      </button>
    </motion.li>
  );
}

export function AlertFeed({
  alerts,
  onSelect,
  selectedId,
}: {
  alerts?: Alert[];
  onSelect?: (a: Alert) => void;
  selectedId?: string | null;
}) {
  const storeAlerts = useAlertStore((state) => state.alerts);
  const connectionStatus = useAlertStore((state) => state.connectionStatus);
  const feed = alerts ?? storeAlerts;

  if (feed.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 px-4 py-10 text-center">
        <Waveform idle height={40} color="rgba(255,255,255,0.35)" />
        <p className="max-w-[24ch] text-xs text-muted-foreground">
          {connectionStatus === "open"
            ? "No alerts this session — all nodes reporting normal ambient baseline."
            : `No alerts this session — feed ${connectionStatus}; reconnecting automatically.`}
        </p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2 p-2">
      <AnimatePresence initial={false}>
        {feed.map((alert) => {
          const key = `${alert.node_id}-${alert.timestamp}`;
          return (
            <AlertRow
              key={key}
              alert={alert}
              {...(onSelect ? { onSelect } : {})}
              selected={selectedId === key}
            />
          );
        })}
      </AnimatePresence>
    </ul>
  );
}
