import { DISTRICTS, type NodeUnit } from "./types";

// Deterministic pseudo-random so SSR and client agree.
function mulberry(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const CITY_CENTER = { lat: 12.9716, lng: 77.5946 };
export const BOUNDS = { latSpan: 0.16, lngSpan: 0.2 };

export const FLEET: NodeUnit[] = (() => {
  const rnd = mulberry(20260815);
  const nodes: NodeUnit[] = [];
  for (let i = 0; i < 64; i++) {
    const id = 401 + i;
    const personal = i >= 56;
    const tamper = !personal && rnd() < 0.07;
    const offline = !personal && rnd() < 0.08;
    nodes.push({
      id,
      type: personal ? "personal" : "fixed",
      power_mode: personal ? "phone_relay" : rnd() < 0.78 ? "solar" : "grid",
      battery_pct: personal ? null : Math.round(38 + rnd() * 61),
      gsm_signal: personal ? null : Math.round(1 + rnd() * 4),
      last_heartbeat: new Date(
        Date.UTC(2026, 7, 15, 18, Math.round(rnd() * 40), Math.round(rnd() * 59)),
      ).toISOString(),
      tamper_flagged: tamper,
      lat: CITY_CENTER.lat + (rnd() - 0.5) * BOUNDS.latSpan,
      lng: CITY_CENTER.lng + (rnd() - 0.5) * BOUNDS.lngSpan,
      district: DISTRICTS[Math.floor(rnd() * DISTRICTS.length)]!,
      online: !offline,
    });
  }
  return nodes;
})();

export function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toISOString().slice(11, 19) + "Z";
}

export function sinceLabel(iso: string, now = Date.now()) {
  const mins = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h${mins % 60}m`;
}

// ── Analytics (P4) — daily aggregates, not live ──
export const NOISE_TREND = Array.from({ length: 14 }, (_, i) => {
  const rnd = mulberry(900 + i);
  const day = new Date(Date.UTC(2026, 7, 2 + i));
  const row: Record<string, string | number> = {
    day: day.toISOString().slice(5, 10),
  };
  DISTRICTS.forEach((d, k) => {
    row[d] = Math.round(56 + rnd() * 22 + k * 1.6);
  });
  return row;
});

export const HEATMAP = DISTRICTS.map((d, i) => ({
  district: d,
  hours: Array.from({ length: 24 }, (_, h) => {
    const rnd = mulberry(i * 100 + h);
    const rush = h >= 8 && h <= 11 ? 14 : h >= 17 && h <= 21 ? 18 : h <= 5 ? -12 : 0;
    return Math.max(38, Math.min(92, Math.round(58 + rush + rnd() * 12)));
  }),
}));
