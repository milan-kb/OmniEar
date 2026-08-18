import { useEffect, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
  ZoomControl,
} from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import { CITY_CENTER } from "@/lib/acoustic/data";
import type { NodeUnit, OmniEarAlert } from "@/lib/acoustic/types";
import type { SpatialMapProps } from "./SpatialMap";

const COLORS = {
  signal: "#43dbc1",
  offline: "#738093",
  tamper: "#f0ae58",
  P0: "#ff4e78",
  P1: "#f0ae58",
  P4: "#6c92f6",
};

function priorityColor(priority: OmniEarAlert["priority"]) {
  return COLORS[priority];
}

function nodeColor(node: NodeUnit, alert?: OmniEarAlert) {
  if (!node.online) return COLORS.offline;
  if (node.tamper_flagged) return COLORS.tamper;
  if (alert) return priorityColor(alert.priority);
  return COLORS.signal;
}

function MapCoordinator({
  nodes,
  selectedNodeId,
  mapPaddingLeft = 0,
}: {
  nodes: NodeUnit[];
  selectedNodeId: number | null | undefined;
  mapPaddingLeft: number | undefined;
}) {
  const map = useMap();

  useEffect(() => {
    if (!nodes.length) return;
    const bounds: LatLngBoundsExpression = nodes.map((node) => [node.lat, node.lng]);
    const left = map.getSize().x >= 640 ? mapPaddingLeft : 0;
    map.fitBounds(bounds, {
      paddingTopLeft: [left + 34, 90],
      paddingBottomRight: [34, 54],
      maxZoom: 14,
      animate: false,
    });
  }, [map, mapPaddingLeft, nodes]);

  useEffect(() => {
    const selected = nodes.find((node) => node.id === selectedNodeId);
    if (selected) map.flyTo([selected.lat, selected.lng], Math.max(map.getZoom(), 15));
  }, [map, nodes, selectedNodeId]);

  return null;
}

export default function InteractiveSpatialMap({
  nodes,
  alerts = [],
  selectedNodeId,
  onSelectNode,
  compact,
  showNodeLabels = false,
  mapPaddingLeft,
}: SpatialMapProps) {
  const activeByNode = useMemo(() => {
    const result = new Map<string, OmniEarAlert>();
    alerts.forEach((alert) => {
      if (!result.has(String(alert.node_id))) result.set(String(alert.node_id), alert);
    });
    return result;
  }, [alerts]);

  return (
    <MapContainer
      center={[CITY_CENTER.lat, CITY_CENTER.lng]}
      zoom={12}
      minZoom={10}
      maxZoom={19}
      zoomControl={false}
      scrollWheelZoom
      className="size-full bg-[#111827]"
      attributionControl={!compact}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <div className="leaflet-map-tint" aria-hidden="true" />
      <MapCoordinator
        nodes={nodes}
        selectedNodeId={selectedNodeId}
        mapPaddingLeft={mapPaddingLeft}
      />
      {!compact && <ZoomControl position="topright" />}

      {nodes.map((node) => {
        const alert = activeByNode.get(String(node.id));
        const color = nodeColor(node, alert);
        const selected = selectedNodeId === node.id;
        return (
          <CircleMarker
            key={node.id}
            center={[node.lat, node.lng]}
            radius={selected ? 9 : node.type === "personal" ? 7 : 6}
            pathOptions={{
              color: selected ? "#ffffff" : color,
              fillColor: color,
              fillOpacity: node.online ? 0.95 : 0.45,
              opacity: 1,
              weight: selected ? 3 : 2,
            }}
            eventHandlers={{ click: () => onSelectNode?.(node) }}
          >
            <Tooltip
              permanent={showNodeLabels && !compact}
              direction="bottom"
              offset={[0, 8]}
              className="omniear-node-label"
            >
              {node.id}
            </Tooltip>
            <Popup className="omniear-node-popup" closeButton={false}>
              <div className="min-w-36">
                <strong>Node {node.id}</strong>
                <span>{node.district}</span>
                <span>
                  {node.type === "personal" ? "Personal relay" : `${node.power_mode} fixed node`}
                </span>
                <span className={node.online ? "is-online" : "is-offline"}>
                  {node.online ? (node.tamper_flagged ? "Tamper flagged" : "Online") : "Offline"}
                </span>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {alerts.map((alert) => {
        const color = priorityColor(alert.priority);
        return (
          <CircleMarker
            key={`${alert.node_id}-${alert.timestamp}`}
            center={[alert.lat, alert.lng]}
            radius={11}
            pathOptions={{ color: "#ffffff", fillColor: color, fillOpacity: 0.9, weight: 3 }}
            className="omniear-alert-marker"
          >
            <Tooltip direction="top" offset={[0, -10]}>
              {alert.priority} · {alert.label.replaceAll("_", " ")}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
