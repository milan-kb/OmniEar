import { create } from "zustand";
import type { AcousticAlert, AcousticLabel, Alert, AlertPriority, OmniEarAlert } from "./types";

const WS_URL = import.meta.env["VITE_WS_URL"] || "ws://localhost:8765";
const MAX_HISTORY = 120;
const MIN_RECONNECT_DELAY_MS = 1_000;
const MAX_RECONNECT_DELAY_MS = 30_000;

export type ConnectionStatus = "connecting" | "open" | "closed" | "error";

let reconnectTimer: number | null = null;
let reconnectAttempt = 0;
let shouldReconnect = false;

const LABEL_PRIORITIES: Record<AcousticLabel, AlertPriority> = {
  scream_distress: "P0",
  explosion: "P0",
  impact_crash: "P1",
  siren_traffic: "P4",
};

function alertId(alert: Pick<AcousticAlert, "node_id" | "timestamp">) {
  return `${alert.node_id}-${alert.timestamp}`;
}

function parseAlert(raw: unknown): Alert | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;

  const alert = raw as Partial<AcousticAlert>;
  const expectedPriority =
    typeof alert.label === "string" ? LABEL_PRIORITIES[alert.label as AcousticLabel] : undefined;
  const validClass = alert.class === "P0" || alert.class === "P1" || alert.class === "P4";

  if (
    typeof alert.node_id !== "string" ||
    alert.node_id.trim() === "" ||
    typeof alert.timestamp !== "string" ||
    !Number.isFinite(Date.parse(alert.timestamp)) ||
    !validClass ||
    !expectedPriority ||
    expectedPriority !== alert.class ||
    typeof alert.confidence !== "number" ||
    alert.confidence < 0 ||
    alert.confidence > 1 ||
    typeof alert.lat !== "number" ||
    !Number.isFinite(alert.lat) ||
    alert.lat < -90 ||
    alert.lat > 90 ||
    typeof alert.lng !== "number" ||
    !Number.isFinite(alert.lng) ||
    alert.lng < -180 ||
    alert.lng > 180
  ) {
    return null;
  }

  return {
    ...alert,
    label: alert.label as AcousticLabel,
    priority: alert.class,
    status: "new",
  } as Alert;
}

function prependAlert(alerts: Alert[], incoming: Alert) {
  const id = alertId(incoming);
  const existing = alerts.find((alert) => alertId(alert) === id);
  const alert = existing ? { ...incoming, status: existing.status } : incoming;
  return [alert, ...alerts.filter((item) => alertId(item) !== id)].slice(0, MAX_HISTORY);
}

type State = {
  alerts: Alert[];
  running: boolean;
  connectionStatus: ConnectionStatus;
  socket: WebSocket | null;
  selectedId: string | null;
  lastP0: Alert | null;
  setAlerts: (alerts: Alert[]) => void;
  push: (alert: OmniEarAlert) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  select: (id: string | null) => void;
  setStatus: (id: string, status: Alert["status"]) => void;
  toggleRunning: () => void;
};

function scheduleReconnect(get: () => State) {
  if (reconnectTimer !== null || !shouldReconnect || typeof window === "undefined") return;
  const delay = Math.min(MAX_RECONNECT_DELAY_MS, MIN_RECONNECT_DELAY_MS * 2 ** reconnectAttempt);
  reconnectAttempt += 1;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    get().connectWebSocket();
  }, delay);
}

export const useAlertStore = create<State>((set, get) => ({
  alerts: [],
  running: true,
  connectionStatus: "closed",
  socket: null,
  selectedId: null,
  lastP0: null,
  setAlerts: (alerts) => set({ alerts }),
  push: (incoming) =>
    set((state) => {
      const alert: Alert = { ...incoming, status: "new" };
      const isNew = !state.alerts.some((item) => alertId(item) === alertId(alert));
      const alerts = prependAlert(state.alerts, alert);
      return {
        alerts,
        lastP0: isNew && alert.priority === "P0" ? alerts[0]! : state.lastP0,
      };
    }),
  select: (id) => set({ selectedId: id }),
  setStatus: (id, status) =>
    set((state) => ({
      alerts: state.alerts.map((alert) =>
        `${alert.node_id}-${alert.timestamp}` === id ? { ...alert, status } : alert,
      ),
    })),
  toggleRunning: () => set((state) => ({ running: !state.running })),
  connectWebSocket: () => {
    if (typeof window === "undefined") return;
    shouldReconnect = true;
    const existing = get().socket;
    if (
      existing &&
      (existing.readyState === WebSocket.CONNECTING || existing.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    let socket: WebSocket;
    try {
      socket = new WebSocket(WS_URL);
    } catch (error) {
      console.error(`Could not open the OmniEar alert feed at ${WS_URL}.`, error);
      set({ connectionStatus: "error", socket: null });
      scheduleReconnect(get);
      return;
    }
    set({ socket, connectionStatus: "connecting" });

    socket.addEventListener("open", () => {
      reconnectAttempt = 0;
      set({ connectionStatus: "open" });
    });

    socket.addEventListener("message", (event) => {
      if (!get().running) return;
      try {
        if (typeof event.data !== "string") {
          console.warn("Dropping WebSocket alert: expected one JSON text frame.");
          return;
        }
        const alert = parseAlert(JSON.parse(event.data));
        if (!alert) {
          console.warn("Dropping malformed WebSocket alert.");
          return;
        }
        set((state) => {
          const isNew = !state.alerts.some((item) => alertId(item) === alertId(alert));
          const alerts = prependAlert(state.alerts, alert);
          return {
            alerts,
            lastP0: isNew && alert.priority === "P0" ? alerts[0]! : state.lastP0,
          };
        });
      } catch (error) {
        console.warn("Dropping WebSocket alert: invalid JSON.", error);
      }
    });

    socket.addEventListener("close", () => {
      if (get().socket === socket) set({ connectionStatus: "closed", socket: null });
      scheduleReconnect(get);
    });

    socket.addEventListener("error", () => {
      if (get().socket === socket) set({ connectionStatus: "error" });
    });
  },
  disconnectWebSocket: () => {
    shouldReconnect = false;
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    const socket = get().socket;
    if (socket) {
      socket.close();
    }
    set({ socket: null, connectionStatus: "closed" });
  },
}));

export function startSimulator() {
  useAlertStore.getState().connectWebSocket();
}
