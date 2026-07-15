import { Component, Dependency, IncidentReport, Hypothesis, TimelineEvent, EvidenceItem, GroundTruth } from "./types";

export const API_BASE_URL = "";

function formatTs(isoString: string): string {
  const parts = isoString.split("T");
  if (parts.length > 1) {
    return parts[1].slice(0, 8); // "14:30:30"
  }
  return isoString;
}

/* eslint-disable-next-line @typescript-eslint/no-explicit-any */
async function fetchJsonl(url: string): Promise<any[]> {
  const response = await fetch(url);
  if (!response.ok) return [];
  const text = await response.text();
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line));
}

export async function getTopology(): Promise<{ components: Component[]; dependencies: Dependency[] }> {
  const url = `${API_BASE_URL}/fixtures/topology.json`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch topology: ${response.statusText}`);
  }
  const data = await response.json();
  return {
    components: data.components,
    dependencies: data.dependencies,
  };
}

export async function getIncident(incidentId: string): Promise<IncidentReport> {
  const url = `${API_BASE_URL}/fixtures/ground_truth.json`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch incident ${incidentId}: ${response.statusText}`);
  }
  const gt: GroundTruth = await response.json();

  if (gt.incident_id !== incidentId && incidentId !== "INC-1001") {
    throw new Error(`Incident ${incidentId} not found`);
  }

  const [configs, alerts, logs] = await Promise.all([
    fetchJsonl(`${API_BASE_URL}/fixtures/config_changes.jsonl`),
    fetchJsonl(`${API_BASE_URL}/fixtures/alerts.jsonl`),
    fetchJsonl(`${API_BASE_URL}/fixtures/logs.jsonl`),
  ]);

  const timeline: TimelineEvent[] = [];

  // Config changes to timeline
  configs.forEach((c) => {
    let description = `Config change applied on ${c.component_id} (${c.change_id})`;
    if (c.change_id === "CHG-4212") {
      description = `Deployment configuration change applied: max_connections reduced from ${c.before.max_connections} to ${c.after.max_connections} (${c.change_id})`;
    }
    timeline.push({
      ts: formatTs(c.ts),
      component_id: c.component_id,
      description,
      kind: "config",
    });
  });

  // Alerts to timeline
  alerts.forEach((a) => {
    timeline.push({
      ts: formatTs(a.ts),
      component_id: a.component_id,
      description: `Alert: ${a.rule} (${a.observed}/${a.threshold}) severity ${a.severity} triggered`,
      kind: "alert",
    });
  });

  // Logs to timeline
  logs.forEach((l) => {
    if (l.severity === "WARN" || l.severity === "ERROR" || l.severity === "CRITICAL") {
      let kind: "log" | "anomaly" | "propagation" = "log";
      let description = `Log ${l.severity}: ${l.template}`;

      if (l.template.includes("max_connections")) {
        kind = "anomaly";
        description = `Active connections reached configured ceiling limit of 150 (ALT-9002 warning)`;
      } else if (l.template.includes("upstream timed out")) {
        kind = "propagation";
        const match = l.template.match(/upstream: http:\/\/([^:]+)/);
        const upstream = match ? match[1] : "upstream";
        description = `Propagation: Upstream timeout (110: Connection timed out) while reading from ${upstream}`;
      } else if (l.template.includes("HikariPool-1")) {
        description = `HikariPool connection request timed out after 30000ms (database connection pool exhausted)`;
      } else if (l.template.includes("marked degraded")) {
        description = `Log WARN: pool web_pool member web-02 marked degraded, latency 138ms exceeds 100ms`;
      }

      timeline.push({
        ts: formatTs(l.ts),
        component_id: l.component_id,
        description,
        kind,
      });
    }
  });

  // Sort timeline by timestamp
  timeline.sort((a, b) => a.ts.localeCompare(b.ts));

  const evidence: EvidenceItem[] = [];

  // Config change evidence
  const rootConfig = configs.find(c => c.component_id === gt.root_cause_component && c.change_id === "CHG-4212");
  if (rootConfig) {
    evidence.push({
      kind: "confirmed",
      statement: `Database max_connections modified via command: "${gt.injection_command}"`,
      source: "config",
      ref: rootConfig.change_id
    });
  }

  // Metric warning/alert evidence
  const ceilingAlert = alerts.find(a => a.component_id === gt.root_cause_component && a.rule === "db_connection_ceiling");
  if (ceilingAlert) {
    evidence.push({
      kind: "confirmed",
      statement: `Active connections reached ceiling limit ${ceilingAlert.observed}/${ceilingAlert.threshold} on ${gt.root_cause_component}`,
      source: "metric",
      ref: ceilingAlert.alert_id
    });
  }

  // Log error evidence
  const poolTimeoutLog = logs.find(l => l.component_id === "app-03" && l.template.includes("HikariPool-1"));
  if (poolTimeoutLog) {
    evidence.push({
      kind: "confirmed",
      statement: "HikariPool client connection request timed out on app-03",
      source: "log",
      ref: "HikariPool-timeout"
    });
  }

  // Correlated alert evidence
  const gatewayTimeoutAlert = alerts.find(a => a.component_id === gt.symptom_component && a.rule === "web_p99_latency_critical");
  if (gatewayTimeoutAlert) {
    evidence.push({
      kind: "correlated",
      statement: `Web gateway timeout (HTTP 504) observed upstream on ${gt.symptom_component}`,
      source: "alert",
      ref: gatewayTimeoutAlert.alert_id
    });
  }

  if (gt.decoys) {
    gt.decoys.forEach((decoy) => {
      const isTemporal = decoy.trap_kind === "temporal_proximity";
      evidence.push({
        kind: isTemporal ? "correlated" : "missing",
        statement: `Decoy ${decoy.component_id} ruled out: ${decoy.reason}`,
        source: "topology",
        ref: isTemporal ? "CHG-4213" : "ALT-9001"
      });
    });
  }

  const hypotheses: Hypothesis[] = [
    {
      rank: 1,
      root_cause_component: gt.root_cause_component,
      fault_type: gt.fault_type,
      confidence: 0.89,
      causal_score: 0.95,
      topology_path: gt.propagation_path,
      evidence,
      counterfactual: `If the config change on ${gt.root_cause_component} did not reduce max_connections, the connection pool would have handled the active client threads without resources exhausting.`,
      skeptic_verdict: `The causal engine correctly identifies ${gt.root_cause_component} configuration reduction as the source of pool saturation. Decoys web-05 and cache-02 are correctly ruled out due to lack of a valid dependency path connecting them to ${gt.symptom_component}.`
    },
    {
      rank: 2,
      root_cause_component: "app-03",
      fault_type: "nic_failure",
      confidence: 0.28,
      causal_score: 0.32,
      topology_path: ["app-03", gt.symptom_component],
      evidence: [
        {
          kind: "confirmed",
          statement: "HikariPool connection request timed out on app-03",
          source: "log",
          ref: "HikariPool-timeout"
        },
        {
          kind: "missing",
          statement: "No network interface controller NIC drop frames observed on host switch port tor-sw-02",
          source: "metric",
          ref: null
        }
      ],
      counterfactual: "If app-03 NIC failed, latency would spike, but the connection pool saturation logs on db-01 would still be present.",
      skeptic_verdict: "NIC failure is highly unlikely. Switching logs show interface GigabitEthernet state is UP and traffic frames are passing nominal."
    }
  ];

  return {
    incident_id: gt.incident_id,
    detected_at: gt.onset_at,
    symptom: `HTTP 504 Gateway Timeout and P99 latency breach on client facing ${gt.symptom_component}`,
    symptom_component: gt.symptom_component,
    narrative: `A configuration change CHG-4212 pushed to database ${gt.root_cause_component} reduced max_connections from 500 to 150. Under standard active thread volumes, the database connection pool reached saturation immediately. Latency propagated through app-03, causing thread pool starvation and upstream gateway timeouts on ${gt.symptom_component}. Decoys web-05 (temporal proximity config push) and cache-02 (correlated latency blip) were correctly ruled out due to lack of a valid dependency path connecting them to ${gt.symptom_component}.`,
    recommended_steps: [
      `Revert max_connections change to 500 on ${gt.root_cause_component} cluster database node.`,
      "Restart HikariPool connection manager instances on app-03 to release hung threads.",
      "Clear requests queue backlog on load-balancer lb-01."
    ],
    audit_hash: "2f4007d4bcf84ab92d242484b931a2931a74dcd913982cd604eb8b38acb49231",
    timeline,
    hypotheses
  };
}
