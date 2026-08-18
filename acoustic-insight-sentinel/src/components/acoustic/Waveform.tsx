import { useEffect, useRef, useState } from "react";

export function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

const N = 220;

function skylineAt(i: number) {
  // Deterministic city silhouette: blocks of varying height.
  const block = Math.floor(i / 11);
  const h = [0.22, 0.55, 0.35, 0.78, 0.3, 0.62, 0.44, 0.9, 0.28, 0.5][block % 10]!;
  return h;
}

/**
 * The signature element. morph = 0 -> live acoustic waveform,
 * morph = 1 -> city skyline / node-map silhouette.
 */
export function Waveform({
  morph = 0,
  amplitude = 1,
  color = "var(--signal)",
  height = 180,
  idle = false,
  className,
}: {
  morph?: number;
  amplitude?: number;
  color?: string;
  height?: number;
  idle?: boolean;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [t, setT] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (reduced || idle) return;
    let last = 0;
    const loop = (ts: number) => {
      if (ts - last > 33) {
        setT((v) => v + 0.06);
        last = ts;
      }
      raf.current = requestAnimationFrame(loop);
    };
    raf.current = requestAnimationFrame(loop);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [reduced, idle]);

  const w = 1000;
  const mid = height / 2;
  const pts: string[] = [];
  const base: string[] = [];
  for (let i = 0; i < N; i++) {
    const x = (i / (N - 1)) * w;
    const env = Math.sin((i / N) * Math.PI);
    const wave =
      Math.sin(i * 0.22 + t) * 0.5 +
      Math.sin(i * 0.09 - t * 0.7) * 0.32 +
      Math.sin(i * 0.55 + t * 1.7) * 0.18;
    const waveY = mid - wave * env * amplitude * (idle ? 4 : mid * 0.72);
    const skyY = height - skylineAt(i) * height * 0.82;
    const y = waveY * (1 - morph) + skyY * morph;
    pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    base.push(`${x.toFixed(1)},${height}`);
  }

  return (
    <svg
      viewBox={`0 0 ${w} ${height}`}
      preserveAspectRatio="none"
      className={className}
      aria-hidden="true"
      style={{ width: "100%", height }}
    >
      <defs>
        <linearGradient id="ae-wave-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.28} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon points={`${pts.join(" ")} ${w},${height} 0,${height}`} fill="url(#ae-wave-fill)" />
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
