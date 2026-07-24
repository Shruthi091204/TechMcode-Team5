import { Component, Dependency, IncidentReport } from "./types";

// In production, set NEXT_PUBLIC_API_URL to the deployed backend origin
// (e.g. https://causalops-backend.onrender.com). Locally it falls back to
// "/api", which the next.config.ts rewrite proxies to the FastAPI backend.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export async function getTopology(): Promise<{ components: Component[]; dependencies: Dependency[] }> {
  const url = `${API_BASE_URL}/topology`;
  const response = await fetch(url, { cache: "no-store" });
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
  const url = `${API_BASE_URL}/incidents/${incidentId}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch incident ${incidentId}: ${response.statusText}`);
  }
  const data: IncidentReport = await response.json();
  
  // Format timestamps nicely if the backend sends full ISO
  if (data.timeline) {
    data.timeline = data.timeline.map((event) => {
      const parts = event.ts.split("T");
      return {
        ...event,
        ts: parts.length > 1 ? parts[1].slice(0, 8) : event.ts,
      };
    });
  }

  return data;
}

export interface AuditVerification {
  is_valid: boolean;
  total_events: number;
  failed_at_index: number | null;
  failure_reason: string | null;
}

export async function getAuditVerification(): Promise<AuditVerification> {
  const url = `${API_BASE_URL}/audit/verify`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch audit verification: ${response.statusText}`);
  }
  return await response.json();
}

export interface KnowledgeMatch {
  id: string;
  title: string;
  snippet: string;
  score: number;
}

export interface KnowledgeResult {
  runbooks: KnowledgeMatch[];
  similar_incidents: KnowledgeMatch[];
}

export async function retrieveKnowledge(query: string, k = 3): Promise<KnowledgeResult> {
  const url = `${API_BASE_URL}/knowledge/retrieve`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, k }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to retrieve knowledge: ${response.statusText}`);
  }
  return await response.json();
}

export interface UsageStats {
  incidents_analyzed: number;
  nodes_analyzed: number;
  audit_events: number;
}

export async function getUsageStats(): Promise<UsageStats> {
  const url = `${API_BASE_URL}/stats`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch usage stats: ${response.statusText}`);
  }
  return await response.json();
}

export interface HealthyResult {
  status: "healthy";
  components_analyzed: number;
  telemetry_windows: number;
  metrics_evaluated: string[];
  message: string;
}

export async function analyzeIncident(
  payload: unknown,
  fast: boolean = false,
): Promise<IncidentReport | HealthyResult> {
  const url = `${API_BASE_URL}/analyze${fast ? "?fast=true" : ""}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Analysis failed: ${response.statusText}`);
  }
  return await response.json();
}
