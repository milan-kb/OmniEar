import { Link } from "@tanstack/react-router";
import { Activity, Cpu, LineChart, Map, Radio, Smartphone } from "lucide-react";
import type { ReactNode } from "react";

const NAV = [
  { to: "/ops", label: "Operations", icon: Activity },
  { to: "/map", label: "Node network", icon: Map },
  { to: "/analytics", label: "Analytics", icon: LineChart },
  { to: "/fleet", label: "Fleet", icon: Cpu },
  { to: "/personal", label: "Personal node", icon: Smartphone },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-void">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-void/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-4 px-4">
          <Link to="/" className="flex items-center gap-2">
            <Radio className="size-4 text-signal" aria-hidden />
            <span className="font-display text-sm tracking-tight">OmniEar</span>
          </Link>
          <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className="flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground [&.active]:bg-signal/10 [&.active]:text-signal"
              >
                <n.icon className="size-3.5" aria-hidden />
                {n.label}
              </Link>
            ))}
          </nav>
          <span className="mono hidden text-[11px] text-muted-foreground sm:block">
            BBMP · ward ops
          </span>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
