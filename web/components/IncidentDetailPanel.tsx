"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Cpu, Activity, AlertTriangle, FileText, Settings, Database, Layers } from "lucide-react";
import { IncidentReport, Component } from "../lib/types";

interface IncidentDetailPanelProps {
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

export default function IncidentDetailPanel({
  isOpen,
  onClose,
  nodeId,
  isCluster,
  tier,
  topology,
  incident,
  onExpandTier,
  pathNodes,
}: IncidentDetailPanelProps) {
  if (!isOpen || !nodeId) return null;

  // Filter components belonging to this tier if cluster
  const clusterComponents = isCluster && tier
    ? topology.components.filter((c) => c.tier === tier)
    : [];

  // Filter logs, alerts, config changes from timeline for real component
  const componentEvents = !isCluster
    ? incident.timeline.filter((e) => e.component_id === nodeId)
    : [];

  const componentLogs = componentEvents.filter((e) => e.kind === "log" || e.kind === "anomaly" || e.kind === "propagation").slice(-5);
  const componentAlerts = componentEvents.filter((e) => e.kind === "alert");
  const componentConfigs = componentEvents.filter((e) => e.kind === "config");

  // Determine dynamic telemetry metrics based on active path
  const isRootCause = !isCluster && nodeId === incident.hypotheses[0]?.root_cause_component;
  const isOnPath = !isCluster && pathNodes.includes(nodeId);

  const getTelemetryMetrics = () => {
    if (isRootCause) {
      return { cpu: "94.2%", mem: "91.5%", latency: "138.4ms", loss: "0.1%", status: "CRITICAL" };
    }
    if (isOnPath) {
      return { cpu: "82.1%", mem: "78.4%", latency: "112.5ms", loss: "0.0%", status: "DEGRADED" };
    }
    return { cpu: "14.5%", mem: "42.1%", latency: "1.8ms", loss: "0.0%", status: "NOMINAL" };
  };

  const telemetry = getTelemetryMetrics();

  return (
    <motion.div
      initial={{ x: "100%", opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: "100%", opacity: 0 }}
      transition={{ type: "spring", damping: 25, stiffness: 120 }}
      className="lg:w-[60%] w-full bg-[#16161A] border border-[#2A2A2E] rounded-xl p-6 flex flex-col justify-between h-[550px] overflow-y-auto relative shadow-lifted"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-[#A3A3A8] hover:text-white transition-colors p-1.5 hover:bg-[#1F1F24] rounded-full z-10"
        title="Close panel"
      >
        <X size={20} />
      </button>

      {/* Content wrapper with fade transition on swap */}
      <AnimatePresence mode="wait">
        <motion.div
          key={nodeId}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="flex flex-col gap-6"
        >
          {/* HEADER SECTION */}
          <div>
            <div className="flex items-center gap-2">
              {isCluster ? (
                <Layers size={16} className="text-[#FFA53B]" />
              ) : (
                <Database size={16} className={isRootCause ? "text-[#E50914]" : isOnPath ? "text-[#FFA53B]" : "text-[#A3A3A8]"} />
              )}
              <span className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase">
                {isCluster ? "CLUSTER DETAIL" : "NODE SPECIFIC INVESTIGATION"}
              </span>
            </div>
            <h2 className="text-3xl font-black mt-1 text-white tracking-tighter" style={{ fontWeight: 900 }}>
              {isCluster ? `${tier?.toUpperCase()} TIER` : nodeId}
            </h2>
            <p className="text-[#A3A3A8] text-xs mt-1 uppercase font-bold tracking-wider">
              {isCluster ? "Tier Components Group" : isRootCause ? "Root Cause Target Component" : isOnPath ? "Propagation Path Node" : "Nominal Service"}
            </p>
          </div>

          {/* CLUSTER CONTAINER IF CLUSTER */}
          {isCluster ? (
            <div className="flex flex-col gap-4">
              <span className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase">
                COMPONENTS IN CLUSTER ({clusterComponents.length})
              </span>
              <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
                {clusterComponents.map((comp) => {
                  const compIsRoot = comp.component_id === incident.hypotheses[0]?.root_cause_component;
                  const compIsOnPath = pathNodes.includes(comp.component_id);
                  const color = compIsRoot ? "text-[#E50914]" : compIsOnPath ? "text-[#FFA53B]" : "text-[#2ECC71]";
                  const status = compIsRoot ? "CRITICAL" : compIsOnPath ? "DEGRADED" : "NOMINAL";

                  return (
                    <div
                      key={comp.component_id}
                      className="flex justify-between items-center p-3 rounded-lg border border-[#2A2A2E] bg-[#1F1F24] hover:bg-[#25252b] transition-colors"
                    >
                      <span className="font-bold text-white text-xs">{comp.component_id}</span>
                      <span className={`font-bold text-[11px] uppercase tracking-wider ${color}`}>
                        {status}
                      </span>
                    </div>
                  );
                })}
              </div>

              {onExpandTier && tier && (
                <button
                  onClick={() => onExpandTier(tier)}
                  className="mt-2 py-2.5 px-4 border border-[#E50914]/50 text-white hover:bg-[#E50914]/15 text-center font-bold tracking-wider rounded-lg transition-all text-xs"
                >
                  EXPAND FULL TIER TOPOLOGY
                </button>
              )}
            </div>
          ) : (
            /* REAL COMPONENT DETAIL VIEW */
            <div className="flex flex-col gap-6">
              {/* TELEMETRY METRICS */}
              <div>
                <div className="flex justify-between items-center text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase border-b border-[#2A2A2E] pb-2">
                  <span>TELEMETRY SNAPSHOT</span>
                  <span className={`font-black uppercase tracking-wider ${
                    telemetry.status === "CRITICAL" ? "text-[#E50914]" : telemetry.status === "DEGRADED" ? "text-[#FFA53B]" : "text-[#2ECC71]"
                  }`}>
                    {telemetry.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-3">
                  <div className="bg-[#1F1F24] border border-[#2A2A2E] p-3 rounded-xl flex items-center gap-3">
                    <Cpu size={16} className="text-[#6B6B70]" />
                    <div>
                      <div className="text-[10px] text-[#6B6B70] font-bold">CPU UTILIZATION</div>
                      <div className="font-extrabold text-white text-sm">{telemetry.cpu}</div>
                    </div>
                  </div>
                  <div className="bg-[#1F1F24] border border-[#2A2A2E] p-3 rounded-xl flex items-center gap-3">
                    <Activity size={16} className="text-[#6B6B70]" />
                    <div>
                      <div className="text-[10px] text-[#6B6B70] font-bold">MEMORY USAGE</div>
                      <div className="font-extrabold text-white text-sm">{telemetry.mem}</div>
                    </div>
                  </div>
                  <div className="bg-[#1F1F24] border border-[#2A2A2E] p-3 rounded-xl flex items-center gap-3">
                    <Activity size={16} className="text-[#6B6B70]" />
                    <div>
                      <div className="text-[10px] text-[#6B6B70] font-bold">P99 LATENCY</div>
                      <div className="font-extrabold text-white text-sm">{telemetry.latency}</div>
                    </div>
                  </div>
                  <div className="bg-[#1F1F24] border border-[#2A2A2E] p-3 rounded-xl flex items-center gap-3">
                    <Activity size={16} className="text-[#6B6B70]" />
                    <div>
                      <div className="text-[10px] text-[#6B6B70] font-bold">PACKET LOSS</div>
                      <div className="font-extrabold text-white text-sm">{telemetry.loss}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ACTIVE ALERTS */}
              <div>
                <span className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase block border-b border-[#2A2A2E] pb-2">
                  ACTIVE ALERTS ({componentAlerts.length})
                </span>
                <div className="flex flex-col gap-2 mt-3">
                  {componentAlerts.length === 0 ? (
                    <span className="text-xs text-[#6B6B70] italic">No active alerts triggered for this node.</span>
                  ) : (
                    componentAlerts.map((alert, idx) => (
                      <div key={idx} className="bg-[#E50914]/5 border border-[#E50914]/20 p-3 rounded-lg flex items-start gap-2.5">
                        <AlertTriangle size={15} className="text-[#E50914] shrink-0 mt-0.5" />
                        <span className="text-white text-xs leading-relaxed">{alert.description}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* RECENT LOG ENTRIES */}
              <div>
                <span className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase block border-b border-[#2A2A2E] pb-2">
                  RECENT LOG ENTRIES
                </span>
                <div className="flex flex-col gap-2 mt-3 max-h-[140px] overflow-y-auto pr-1">
                  {componentLogs.length === 0 ? (
                    <span className="text-xs text-[#6B6B70] italic">No diagnostic logs found.</span>
                  ) : (
                    componentLogs.map((log, idx) => (
                      <div key={idx} className="bg-[#1F1F24] border border-[#2A2A2E] p-3 rounded-lg text-xs leading-relaxed flex gap-2.5">
                        <FileText size={14} className="text-[#6B6B70] shrink-0 mt-0.5" />
                        <div>
                          <span className="text-[#6B6B70] font-bold mr-2">[{log.ts}]</span>
                          <span className="text-[#A3A3A8]">{log.description}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* CONFIGURATION AUDITS */}
              <div>
                <span className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase block border-b border-[#2A2A2E] pb-2">
                  CONFIGURATION AUDITS ({componentConfigs.length})
                </span>
                <div className="flex flex-col gap-2 mt-3">
                  {componentConfigs.length === 0 ? (
                    <span className="text-xs text-[#6B6B70] italic">No configuration modifications tracked.</span>
                  ) : (
                    componentConfigs.map((cfg, idx) => (
                      <div key={idx} className="bg-[#FFA53B]/5 border border-[#FFA53B]/20 p-3 rounded-lg flex items-start gap-2.5">
                        <Settings size={15} className="text-[#FFA53B] shrink-0 mt-0.5" />
                        <span className="text-white text-xs leading-relaxed">{cfg.description}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  );
}
