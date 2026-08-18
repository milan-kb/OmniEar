import { lazy, Suspense, useEffect, useState } from "react";
import type { NodeUnit, OmniEarAlert } from "@/lib/acoustic/types";
import { cn } from "@/lib/utils";

export type SpatialMapProps = {
  nodes: NodeUnit[];
  alerts?: OmniEarAlert[];
  selectedNodeId?: number | null;
  onSelectNode?: (node: NodeUnit) => void;
  className?: string;
  compact?: boolean;
  showNodeLabels?: boolean;
  mapPaddingLeft?: number;
};

const InteractiveSpatialMap = lazy(() => import("./InteractiveSpatialMap"));

function MapLoadingState({ compact }: { compact: boolean | undefined }) {
  return (
    <div className="city-surface hairline-grid flex size-full items-center justify-center">
      {!compact && (
        <div className="glass mono rounded-full px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          loading interactive map
        </div>
      )}
    </div>
  );
}

export function SpatialMap(props: SpatialMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <div
      className={cn(
        "city-surface relative isolate overflow-hidden rounded-xl border border-white/10",
        props.className,
      )}
    >
      {mounted ? (
        <Suspense fallback={<MapLoadingState compact={props.compact} />}>
          <InteractiveSpatialMap {...props} />
        </Suspense>
      ) : (
        <MapLoadingState compact={props.compact} />
      )}
    </div>
  );
}
