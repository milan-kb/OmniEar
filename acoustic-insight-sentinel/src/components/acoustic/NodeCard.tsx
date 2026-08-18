import { BatteryMedium, Signal, Sun, Zap, ShieldAlert } from "lucide-react";
import type { NodeUnit } from "@/lib/acoustic/types";
import { sinceLabel } from "@/lib/acoustic/data";
import { cn } from "@/lib/utils";

function PowerSwitch({
  mode,
  onChange,
  disabled,
}: {
  mode: NodeUnit["power_mode"];
  onChange: () => void;
  disabled?: boolean;
}) {
  const solar = mode === "solar";
  return (
    <button
      type="button"
      role="switch"
      aria-checked={solar}
      aria-label="Power mode: solar or grid"
      disabled={disabled}
      onClick={onChange}
      className="neo-inset flex items-center gap-1 rounded-full p-1 disabled:opacity-50"
    >
      <span
        className={cn(
          "flex items-center gap-1 rounded-full px-2 py-1 text-[10px] transition-all",
          solar ? "neo text-signal" : "text-muted-foreground",
        )}
      >
        <Sun className="size-3" aria-hidden /> solar
      </span>
      <span
        className={cn(
          "flex items-center gap-1 rounded-full px-2 py-1 text-[10px] transition-all",
          !solar ? "neo text-p1" : "text-muted-foreground",
        )}
      >
        <Zap className="size-3" aria-hidden /> grid
      </span>
    </button>
  );
}

function Meter({ value, color }: { value: number; color: string }) {
  return (
    <div className="neo-inset h-2 w-full overflow-hidden rounded-full">
      <div
        className="h-full rounded-full transition-[width]"
        style={{ width: `${value}%`, background: color, boxShadow: `0 0 10px ${color}` }}
      />
    </div>
  );
}

export function NodeCard({ node, onToggle }: { node: NodeUnit; onToggle: (id: number) => void }) {
  const dead = !node.online || node.tamper_flagged;
  const battery = node.battery_pct ?? 0;
  const batteryColor = battery > 60 ? "var(--signal)" : battery > 30 ? "var(--p1)" : "var(--p0)";

  return (
    <article
      className={cn(
        "rounded-2xl p-4 transition-transform",
        dead ? "neo-dead" : "neo hover:-translate-y-0.5",
      )}
    >
      <header className="flex items-center justify-between">
        <div>
          <h3 className="mono text-sm">NODE {node.id}</h3>
          <p className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {node.district} · {node.type}
          </p>
        </div>
        <span
          className={cn(
            "mono rounded-full px-2 py-0.5 text-[10px]",
            !node.online
              ? "bg-white/10 text-muted-foreground"
              : node.tamper_flagged
                ? "bg-p1/15 text-p1"
                : "bg-signal/15 text-signal",
          )}
        >
          {!node.online ? "offline" : node.tamper_flagged ? "tamper" : "online"}
        </span>
      </header>

      <div className="mt-4 space-y-3">
        <div>
          <div className="mono mb-1 flex justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <BatteryMedium className="size-3" aria-hidden /> battery
            </span>
            <span className="text-foreground">
              {node.battery_pct === null ? "—" : `${node.battery_pct}%`}
            </span>
          </div>
          <Meter value={battery} color={batteryColor} />
        </div>
        <div>
          <div className="mono mb-1 flex justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <Signal className="size-3" aria-hidden /> gsm
            </span>
            <span className="text-foreground">
              {node.gsm_signal === null ? "phone relay" : `${node.gsm_signal}/5`}
            </span>
          </div>
          <Meter value={(node.gsm_signal ?? 0) * 20} color="var(--p4)" />
        </div>
      </div>

      <footer className="mt-4 flex items-center justify-between gap-2">
        <span className="mono text-[10px] text-muted-foreground">
          hb {sinceLabel(node.last_heartbeat, Date.UTC(2026, 7, 15, 18, 45))} ago
        </span>
        {node.type === "personal" ? (
          <span className="mono text-[10px] text-muted-foreground">BLE → phone</span>
        ) : (
          <PowerSwitch
            mode={node.power_mode}
            onChange={() => onToggle(node.id)}
            disabled={!node.online}
          />
        )}
      </footer>

      {node.tamper_flagged && (
        <p className="mono mt-3 flex items-center gap-1.5 text-[10px] text-p1">
          <ShieldAlert className="size-3" aria-hidden /> enclosure tamper flag raised — dispatch
          maintenance
        </p>
      )}
    </article>
  );
}
