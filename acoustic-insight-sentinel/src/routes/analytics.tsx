import { createFileRoute } from "@tanstack/react-router";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/acoustic/AppShell";
import { HEATMAP, NOISE_TREND } from "@/lib/acoustic/data";
import { DISTRICTS } from "@/lib/acoustic/types";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "Smart City Analytics — OmniEar" },
      {
        name: "description",
        content:
          "A demonstration of planned noise-pollution analytics using a local synthetic district dataset.",
      },
      { property: "og:title", content: "Smart City Analytics — OmniEar" },
      {
        property: "og:description",
        content: "The calm register — aggregated ambient noise, not incidents.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "/analytics" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [{ rel: "canonical", href: "/analytics" }],
  }),
  component: Analytics,
});

const LINE_COLORS = [
  "var(--signal)",
  "var(--p4)",
  "var(--p1)",
  "var(--p0)",
  "oklch(0.8 0.09 320)",
  "oklch(0.75 0.02 260)",
];

function heatColor(db: number) {
  const t = Math.max(0, Math.min(1, (db - 40) / 52));
  return `color-mix(in oklab, var(--p0) ${Math.round(t * 100)}%, var(--p4))`;
}

function Analytics() {
  return (
    <AppShell>
      <div className="mx-auto max-w-[1400px] px-4 py-8">
        <header>
          <p className="mono text-[11px] uppercase tracking-[0.24em] text-p4">
            calm register · demonstration dataset
          </p>
          <h1 className="font-display mt-2 text-3xl tracking-tight">Smart city analytics</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            A preview of planned daily and hourly aggregates using local synthetic values. The
            current live pipeline does not emit decibel readings or district aggregates.
          </p>
        </header>

        <section className="glass mt-8 rounded-2xl p-4 sm:p-6">
          <h2 className="font-display text-lg tracking-tight">14-day noise trend by district</h2>
          <p className="mono mt-1 text-[11px] text-muted-foreground">dB(A) · daily mean</p>
          <div className="mt-4 h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={NOISE_TREND} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={[40, 95]}
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                />
                {DISTRICTS.map((d, i) => (
                  <Line
                    key={d}
                    type="monotone"
                    dataKey={d}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-4 flex flex-wrap gap-3">
            {DISTRICTS.map((d, i) => (
              <li
                key={d}
                className="mono flex items-center gap-1.5 text-[11px] text-muted-foreground"
              >
                <span
                  className="size-2 rounded-full"
                  style={{ background: LINE_COLORS[i % LINE_COLORS.length] }}
                  aria-hidden
                />
                {d}
              </li>
            ))}
          </ul>
        </section>

        <section className="glass mt-6 overflow-x-auto rounded-2xl p-4 sm:p-6">
          <h2 className="font-display text-lg tracking-tight">24-hour noise heatmap</h2>
          <p className="mono mt-1 text-[11px] text-muted-foreground">
            hour of day · dB(A) mean · blue calm → red loud
          </p>
          <div className="mt-4 min-w-[640px]">
            <div className="mono grid grid-cols-[110px_repeat(24,1fr)] gap-[3px] text-[9px] text-muted-foreground">
              <span />
              {Array.from({ length: 24 }, (_, h) => (
                <span key={h} className="text-center">
                  {h}
                </span>
              ))}
            </div>
            {HEATMAP.map((row) => (
              <div
                key={row.district}
                className="mono mt-[3px] grid grid-cols-[110px_repeat(24,1fr)] items-center gap-[3px] text-[10px]"
              >
                <span className="truncate text-muted-foreground">{row.district}</span>
                {row.hours.map((db, h) => (
                  <span
                    key={h}
                    title={`${row.district} ${h}:00 — ${db} dB(A)`}
                    className="h-6 rounded-[3px]"
                    style={{ background: heatColor(db) }}
                  />
                ))}
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
