import { createFileRoute } from "@tanstack/react-router";
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

const CHART = { width: 1000, height: 300, left: 44, right: 18, top: 14, bottom: 30 };
const DB_MIN = 40;
const DB_MAX = 95;

function chartX(index: number) {
  return CHART.left + (index / (NOISE_TREND.length - 1)) * (CHART.width - CHART.left - CHART.right);
}

function chartY(value: number) {
  const plotHeight = CHART.height - CHART.top - CHART.bottom;
  return CHART.top + ((DB_MAX - value) / (DB_MAX - DB_MIN)) * plotHeight;
}

function NoiseTrendChart() {
  const ticks = [40, 50, 60, 70, 80, 90];

  return (
    <svg
      viewBox={`0 0 ${CHART.width} ${CHART.height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Fourteen-day mean noise trend for six Bengaluru districts"
      className="size-full overflow-visible"
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line
            x1={CHART.left}
            x2={CHART.width - CHART.right}
            y1={chartY(tick)}
            y2={chartY(tick)}
            stroke="rgba(255,255,255,0.07)"
            vectorEffect="non-scaling-stroke"
          />
          <text
            x={CHART.left - 9}
            y={chartY(tick) + 4}
            textAnchor="end"
            fill="var(--muted-foreground)"
            fontSize="11"
          >
            {tick}
          </text>
        </g>
      ))}

      {NOISE_TREND.map((row, index) => (
        <text
          key={String(row["day"])}
          x={chartX(index)}
          y={CHART.height - 7}
          textAnchor="middle"
          fill="var(--muted-foreground)"
          fontSize="10"
        >
          {row["day"]}
        </text>
      ))}

      {DISTRICTS.map((district, districtIndex) => {
        const color = LINE_COLORS[districtIndex % LINE_COLORS.length];
        const points = NOISE_TREND.map(
          (row, index) => `${chartX(index)},${chartY(Number(row[district]))}`,
        ).join(" ");
        return (
          <g key={district}>
            <polyline
              points={points}
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
            {NOISE_TREND.map((row, index) => (
              <circle
                key={String(row["day"])}
                cx={chartX(index)}
                cy={chartY(Number(row[district]))}
                r="7"
                fill="transparent"
              >
                <title>{`${district} · ${row["day"]} · ${row[district]} dB(A)`}</title>
              </circle>
            ))}
          </g>
        );
      })}
    </svg>
  );
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
            <NoiseTrendChart />
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
