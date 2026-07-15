export type Severity = "INFO" | "WARN" | "ERROR" | "CRITICAL";

export type ComponentType =
  | "core_switch"
  | "tor_switch"
  | "firewall"
  | "load_balancer"
  | "web_server"
  | "app_server"
  | "database"
  | "cache"
  | "message_queue"
  | "dns_server";

export type Tier = "edge" | "network" | "web" | "app" | "data";

export type RelationKind = "CONNECTED_TO" | "ROUTES_VIA" | "DEPENDS_ON";

export type EvidenceKind = "confirmed" | "correlated" | "missing";

export type EvidenceSource = "metric" | "log" | "alert" | "config" | "topology" | "counterfactual";

export type FaultType =
  | "config_pool_exhaustion"
  | "bad_config_push"
  | "link_degradation"
  | "nic_failure"
  | "capacity_exhaustion"
  | "ddos_flood"
  | "port_scan";

export type TimelineKind = "config" | "alert" | "anomaly" | "log" | "propagation";

export type TrapKind = "temporal_proximity" | "correlated_signal";

export interface Component {
  component_id: string;
  component_type: ComponentType;
  tier: Tier;
  rack: string;
  capacity_mbps: number;
}

export interface Dependency {
  source_id: string;
  target_id: string;
  relation: RelationKind;
}

export interface TelemetryPoint {
  component_id: string;
  window_start: string;
  latency_ms: number;
  jitter_ms: number;
  packet_loss_pct: number;
  throughput_mbps: number;
  error_rate: number;
  connection_count: number;
  cpu_pct: number;
  mem_pct: number;
}

export interface LogRecord {
  component_id: string;
  ts: string;
  severity: Severity;
  template: string;
}

export interface AlertRecord {
  alert_id: string;
  component_id: string;
  ts: string;
  severity: Severity;
  rule: string;
  metric: string;
  threshold: number;
  observed: number;
}

export interface ConfigChange {
  change_id: string;
  component_id: string;
  ts: string;
  author: string;
  change_type: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  ticket_id: string;
}

export interface Anomaly {
  component_id: string;
  metric: string;
  onset_ts: string;
  severity_score: number;
  window_start: string;
  window_end: string;
  baseline_value: number;
  observed_value: number;
}

export interface EvidenceItem {
  kind: EvidenceKind;
  statement: string;
  source: EvidenceSource;
  ref: string | null;
}

export interface Hypothesis {
  rank: number;
  root_cause_component: string;
  fault_type: FaultType;
  confidence: number;
  causal_score: number;
  topology_path: string[];
  evidence: EvidenceItem[];
  counterfactual: string | null;
  skeptic_verdict: string | null;
}

export interface TimelineEvent {
  ts: string;
  component_id: string;
  description: string;
  kind: TimelineKind;
}

export interface IncidentReport {
  schema_version?: string;
  incident_id: string;
  detected_at: string;
  symptom: string;
  symptom_component: string;
  hypotheses: Hypothesis[];
  timeline: TimelineEvent[];
  narrative: string;
  recommended_steps: string[];
  audit_hash: string;
}

export interface Decoy {
  component_id: string;
  trap_kind: TrapKind;
  reason: string;
}

export interface GroundTruth {
  schema_version?: string;
  incident_id: string;
  scenario: string;
  root_cause_component: string;
  fault_type: FaultType;
  injected_at: string;
  onset_at: string;
  symptom_component: string;
  propagation_path: string[];
  injection_command: string;
  decoys?: Decoy[];
}
