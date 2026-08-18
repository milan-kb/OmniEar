export type AlertPriority = "P0" | "P1" | "P4";
export type AcousticLabel = "scream_distress" | "explosion" | "impact_crash" | "siren_traffic";

/** The exact JSON alert emitted by omniear_pipeline.py. */
export interface AcousticAlert {
  node_id: string;
  timestamp: string;
  class: AlertPriority;
  label: AcousticLabel;
  confidence: number;
  lat: number;
  lng: number;
}

/** Wire alert enriched only with presentation metadata used by the dashboard. */
export interface OmniEarAlert extends AcousticAlert {
  priority: AlertPriority;
}

export type AlertClass = AlertPriority;

export type Alert = OmniEarAlert & {
  id?: string;
  status: "new" | "acknowledged" | "resolved";
};

export type NodeUnit = {
  id: number;
  type: "fixed" | "personal";
  power_mode: "solar" | "grid" | "phone_relay";
  battery_pct: number | null;
  gsm_signal: number | null;
  last_heartbeat: string;
  tamper_flagged: boolean;
  lat: number;
  lng: number;
  district: string;
  online: boolean;
};

export const CLASS_META: Record<
  AlertClass,
  { label: string; routeTo: string; color: string; priority: string; token: string }
> = {
  P0: {
    label: "Critical incident",
    routeTo: "Emergency dispatch",
    color: "var(--p0)",
    priority: "P0",
    token: "p0",
  },
  P1: {
    label: "Impact / crash",
    routeTo: "EMS / Traffic Dispatch",
    color: "var(--p1)",
    priority: "P1",
    token: "p1",
  },
  P4: {
    label: "Traffic siren",
    routeTo: "Monitoring only",
    color: "var(--p4)",
    priority: "P4",
    token: "p4",
  },
};

export const LABEL_META: Record<
  AcousticLabel,
  { label: string; routeTo: string; priority: AlertPriority }
> = {
  scream_distress: {
    label: "Distress / scream",
    routeTo: "Police PCR / Campus Security",
    priority: "P0",
  },
  explosion: {
    label: "Explosion",
    routeTo: "Police / Fire / EMS",
    priority: "P0",
  },
  impact_crash: {
    label: "Impact / crash",
    routeTo: "EMS / Traffic Dispatch",
    priority: "P1",
  },
  siren_traffic: {
    label: "Traffic siren",
    routeTo: "Monitoring only",
    priority: "P4",
  },
};

export const DISTRICTS = [
  "Shivajinagar",
  "Indiranagar",
  "Koramangala",
  "Yeshwanthpur",
  "Jayanagar",
  "Whitefield",
];
