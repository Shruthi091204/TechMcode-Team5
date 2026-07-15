"use client";

import React from "react";
import { Component, IncidentReport } from "../lib/types";
import { X, Cpu, Activity, AlertTriangle, FileText, Settings, Database } from "lucide-react";

interface NodeDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  nodeId: string | null;
  isCluster: boolean;
  tier: string | null;
  topology: { components: Component[] };
  incident: IncidentReport;
  onExpandTier?: (tier: string) => void;
  pathNodes: string[];
}

export default function NodeDetailDrawer({
  isOpen,
  onClose,
  nodeId,
  isCluster,
  tier,
  topology,
  incident,
  onExpandTier,
  pathNodes
}: NodeDetailDrawerProps) {
  if (!isOpen) return null;

  // Filter components belonging to this tier if cluster
  const clusterComponents = isCluster && tier
    ? topology.components.filter((c) => c.tier === tier)
    : [];

  // Filter logs, alerts, config changes from timeline for real component
  const componentEvents = !isCluster && nodeId
    ? incident.timeline.filter((e) => e.component_id === nodeId)
    : [];

  const componentLogs = componentEvents.filter((e) => e.kind === "log" || e.kind === "anomaly" || e.kind === "propagation").slice(-5);
  const componentAlerts = componentEvents.filter((e) => e.kind === "alert");
  const componentConfigs = componentEvents.filter((e) => e.kind === "config");

  // Determine dynamic telemetry metrics based on active path
  const isRootCause = !isCluster && nodeId === incident.hypotheses.find((h) => h.rank === 1)?.root_cause_component;
  const isOnPath = !isCluster && nodeId && pathNodes.includes(nodeId);

  const getMockTelemetry = () => {
    if (isRootCause) {
      return { cpu: "94.2%", mem: "91.5%", latency: "138.4ms", loss: "0.1%", status: "CRITICAL" };
    }
    if (isOnPath) {
      return { cpu: "82.1%", mem: "78.4%", latency: "112.5ms", loss: "0.0%", status: "DEGRADED" };
    }
    return { cpu: "14.5%", mem: "42.1%", latency: "1.8ms", loss: "0.0%", status: "NOMINAL" };
  };

  const telemetry = getMockTelemetry();

  return (
    <div className="fixed top-0 right-0 h-full w-[400px] bg-panel/95 backdrop-blur-md border-l border-border-muted z-50 shadow-2xl flex flex-col font-mono text-xs text-white-signal animate-[slide-in_0.3s_ease-out]">
      {/* Header */}
      <div className="p-4 border-b border-border-muted flex items-center justify-between bg-panel-raised">
        <div className="flex items-center gap-2">
          <Database size={16} className="text-red-critical" />
          <span className="font-bold tracking-wider uppercase">
            {isCluster ? `CLUSTER: ${tier?.toUpperCase()}` : `NODE: ${nodeId}`}
          </span>
        </div>
        <button onClick={onClose} className="text-grey-muted hover:text-white-signal p-1">
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
        {isCluster ? (
          /* Cluster Detail View */
          <div className="flex flex-col gap-4">
            <div className="text-[10px] text-grey-muted tracking-wider uppercase border-b border-border-muted/10 pb-1">
              COMPONENTS IN CLUSTER ({clusterComponents.length})
            </div>
            <div className="flex flex-col gap-2">
              {clusterComponents.map((comp) => {
                const compIsOnPath = pathNodes.includes(comp.component_id);
                const compIsRoot = comp.component_id === incident.hypotheses.find((h) => h.rank === 1)?.root_cause_component;
                const statusColor = compIsRoot ? "text-red-critical" : compIsOnPath ? "text-[#FFA53B]" : "text-confirmed";
                const statusText = compIsRoot ? "CRITICAL" : compIsOnPath ? "DEGRADED" : "NOMINAL";

                return (
                  <div
                    key={comp.component_id}
                    className="flex justify-between items-center p-2 border border-border-muted/5 bg-background/20 rounded"
                  >
                    <span className="font-bold">{comp.component_id}</span>
                    <span className={`font-bold text-[10px] ${statusColor}`}>{statusText}</span>
                  </div>
                );
              })}
            </div>

            {onExpandTier && tier && (
              <button
                onClick={() => onExpandTier(tier)}
                className="mt-4 py-2 px-4 border border-red-critical/50 text-red-critical hover:bg-red-critical/10 text-center font-bold tracking-widest rounded-lg transition-all duration-300"
              >
                EXPAND FULL TIER TOPOLOGY
              </button>
            )}
          </div>
        ) : (
          /* Real Component Detail View */
          <div className="flex flex-col gap-6">
            {/* Live Telemetry Snapshot */}
            <div className="flex flex-col gap-2">
              <div className="text-[10px] text-grey-muted tracking-wider uppercase border-b border-border-muted/10 pb-1 flex justify-between">
                <span>TELEMETRY SNAPSHOT</span>
                <span className={telemetry.status === "CRITICAL" ? "text-red-critical text-status-glow font-bold" : telemetry.status === "DEGRADED" ? "text-[#FFA53B] font-bold" : "text-confirmed font-bold"}>
                  {telemetry.status}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 mt-1.5">
                <div className="bg-panel-raised border border-border-muted p-2.5 rounded flex items-center gap-2">
                  <Cpu size={14} className="text-grey-muted" />
                  <div>
                    <div className="text-[9px] text-grey-muted">CPU</div>
                    <div className="font-bold text-white-signal">{telemetry.cpu}</div>
                  </div>
                </div>
                <div className="bg-panel-raised border border-border-muted p-2.5 rounded flex items-center gap-2">
                  <Activity size={14} className="text-grey-muted" />
                  <div>
                    <div className="text-[9px] text-grey-muted">MEMORY</div>
                    <div className="font-bold text-white-signal">{telemetry.mem}</div>
                  </div>
                </div>
                <div className="bg-panel-raised border border-border-muted p-2.5 rounded flex items-center gap-2">
                  <Activity size={14} className="text-grey-muted" />
                  <div>
                    <div className="text-[9px] text-grey-muted">LATENCY</div>
                    <div className="font-bold text-white-signal">{telemetry.latency}</div>
                  </div>
                </div>
                <div className="bg-panel-raised border border-border-muted p-2.5 rounded flex items-center gap-2">
                  <Activity size={14} className="text-grey-muted" />
                  <div>
                    <div className="text-[9px] text-grey-muted">PACKET LOSS</div>
                    <div className="font-bold text-white-signal">{telemetry.loss}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Active Alerts */}
            <div className="flex flex-col gap-2">
              <div className="text-[10px] text-grey-muted tracking-wider uppercase border-b border-border-muted/10 pb-1 flex justify-between">
                <span>ACTIVE ALERTS</span>
                <span className="text-grey-muted">{componentAlerts.length} ACTIVE</span>
              </div>
              <div className="flex flex-col gap-2 mt-1">
                {componentAlerts.length === 0 ? (
                  <span className="text-grey-muted italic text-[11px]">No active alerts triggered.</span>
                ) : (
                  componentAlerts.map((alert, idx) => (
                    <div key={idx} className="bg-red-critical/5 border border-red-critical/20 p-2 rounded flex items-start gap-2">
                      <AlertTriangle size={14} className="text-red-critical shrink-0 mt-0.5" />
                      <span className="text-red-critical text-[11px] font-sans">{alert.description}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Log Records */}
            <div className="flex flex-col gap-2">
              <div className="text-[10px] text-grey-muted tracking-wider uppercase border-b border-border-muted/10 pb-1 flex justify-between">
                <span>RECENT LOG RECORDS</span>
                <span className="text-grey-muted">{componentLogs.length} READINGS</span>
              </div>
              <div className="flex flex-col gap-2 mt-1">
                {componentLogs.length === 0 ? (
                  <span className="text-grey-muted italic text-[11px]">No log outputs found.</span>
                ) : (
                  componentLogs.map((log, idx) => (
                    <div key={idx} className="bg-background/40 border border-border-muted p-2 rounded font-sans text-[11px] leading-relaxed flex gap-2">
                      <FileText size={12} className="text-grey-muted shrink-0 mt-0.5" />
                      <div>
                        <span className="text-grey-muted text-[10px] font-mono mr-1.5">[{log.ts}]</span>
                        <span>{log.description}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Configuration Changes */}
            <div className="flex flex-col gap-2">
              <div className="text-[10px] text-grey-muted tracking-wider uppercase border-b border-border-muted/10 pb-1 flex justify-between">
                <span>CONFIGURATION AUDITS</span>
                <span className="text-grey-muted">{componentConfigs.length} TRACKED</span>
              </div>
              <div className="flex flex-col gap-2 mt-1">
                {componentConfigs.length === 0 ? (
                  <span className="text-grey-muted italic text-[11px]">No configuration updates recorded.</span>
                ) : (
                  componentConfigs.map((cfg, idx) => (
                    <div key={idx} className="bg-[#FFA53B]/5 border border-[#FFA53B]/20 p-2 rounded flex items-start gap-2">
                      <Settings size={14} className="text-[#FFA53B] shrink-0 mt-0.5" />
                      <span className="text-[#FFA53B] text-[11px] font-sans">{cfg.description}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
