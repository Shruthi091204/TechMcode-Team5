import { Component, Dependency, IncidentReport } from "./types";

// Note: In Next.js, fetching from "/api" hits our next.config.ts proxy
// which routes traffic directly to the Python FastAPI backend on port 8000.
export const API_BASE_URL = "/api";

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

export async function getAuditVerification(): Promise<any> {
  const url = `${API_BASE_URL}/audit/verify`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch audit verification: ${response.statusText}`);
  }
  return await response.json();
}
