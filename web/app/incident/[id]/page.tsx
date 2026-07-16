"use client";

import React, { useState, use, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import HeaderBar from "../../../components/HeaderBar";
import MetricStrip from "../../../components/MetricStrip";
import TopologyGraph from "../../../components/TopologyGraph";
import IncidentDetailPanel from "../../../components/IncidentDetailPanel";
import InvestigationTabs from "../../../components/InvestigationTabs";
import { IncidentReport, Component, Dependency } from "../../../lib/types";
import { getIncident, getTopology } from "../../../lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function IncidentPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const [selectedRank, setSelectedRank] = useState<number>(1);
  const [incident, setIncident] = useState<IncidentReport | null>(null);
  const [topology, setTopology] = useState<{ components: Component[]; dependencies: Dependency[] } | null>(null);
  const [telemetry, setTelemetry] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Timeline scrub filtering state
  const [timelineFilterIndex, setTimelineFilterIndex] = useState<number>(999);


  // Side Details Drawer / Panel states
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [drawerNodeId, setDrawerNodeId] = useState<string | null>(null);
  const [drawerIsCluster, setDrawerIsCluster] = useState<boolean>(false);
  const [drawerTier, setDrawerTier] = useState<string | null>(null);
  const [expandedTiers, setExpandedTiers] = useState<string[]>([]);

  // Cinematic Breach Sequence State
  const [isBreachSequence, setIsBreachSequence] = useState<boolean>(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const uploaded =
      typeof window !== "undefined" ? sessionStorage.getItem(`analyzed:${resolvedParams.id}`) : null;
    if (uploaded) {
      try {
        const parsed = JSON.parse(uploaded);
        setIncident(parsed.report);
        setTopology(parsed.topology);
        setTelemetry(parsed.telemetry || []);
        setTimelineFilterIndex(parsed.report.timeline.length - 1);
        setLoading(false);
        setIsBreachSequence(true);
        setTimeout(() => {
          if (active) setIsBreachSequence(false);
        }, 2000);
        return () => {
          active = false;
        };
      } catch {
        // corrupt cache — fall through to the API
      }
    }

    Promise.all([getIncident(resolvedParams.id), getTopology()])
      .then(([incData, topoData]) => {
        if (!active) return;
        setIncident(incData);
        setTopology(topoData);
        // Initialize timeline scrub range to the end of timeline
        setTimelineFilterIndex(incData.timeline.length - 1);
        setLoading(false);
        setIsBreachSequence(true);
        setTimeout(() => setIsBreachSequence(false), 2000); // 2-second cinematic reveal
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load incident diagnostics");
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [resolvedParams.id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
        <div className="text-center select-none flex flex-col items-center gap-3">
          <div className="w-8 h-8 border border-[#E50914] border-t-transparent animate-spin rounded-full" />
          <div className="text-xs text-[#A3A3A8] animate-pulse uppercase tracking-widest font-semibold">
            Loading Incident Diagnostics...
          </div>
        </div>
      </div>
    );
  }

  if (error || !incident || !topology) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
        <div className="border border-[#2A2A2E] bg-[#16161A] p-6 max-w-md w-full select-none rounded-xl">
          <div className="text-[#E50914] font-extrabold text-sm mb-2 border-b border-[#2A2A2E] pb-2 flex justify-between">
            <span>[CRITICAL_FAILURE]</span>
            <span>ERROR CODE: 500</span>
          </div>
          <div className="text-xs text-[#A3A3A8] mb-4 font-sans leading-relaxed">
            {error || "An unexpected error occurred while loading telemetry fixtures."}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="text-xs py-2 px-4 border border-[#E50914] text-white hover:bg-[#E50914]/10 rounded-lg w-full font-bold uppercase transition-all"
          >
            Retry Connectivity
          </button>
        </div>
      </div>
    );
  }

  const activeHypothesis = incident.hypotheses.find((h) => h.rank === selectedRank) || incident.hypotheses[0];
  const pathNodes = activeHypothesis?.topology_path || [];

  // Filter components & dependencies based on scrubbed timeline state
  const filteredTimeline = incident.timeline.slice(0, timelineFilterIndex + 1);

  // We construct a filtered view of the incident report to pass down to visualizers
  const filteredIncidentView: IncidentReport = {
    ...incident,
    timeline: filteredTimeline,
    hypotheses: [
      activeHypothesis,
      ...incident.hypotheses.filter((h) => h.rank !== selectedRank),
    ],
  };

  const handleNodeClick = (nodeId: string, isCluster: boolean, tier: string | null) => {
    setDrawerNodeId(nodeId);
    setDrawerIsCluster(isCluster);
    setDrawerTier(tier);
    setIsDrawerOpen(true);
  };

  // BFS hop distance from root cause node in page.tsx
  const hopDistances = (() => {
    const distances: Record<string, number> = {};
    const rootCauseId = activeHypothesis?.root_cause_component;
    if (!rootCauseId) return distances;
    
    distances[rootCauseId] = 0;
    const queue: string[] = [rootCauseId];
    
    const adj: Record<string, string[]> = {};
    topology.components.forEach(c => {
      adj[c.component_id] = [];
    });
    topology.dependencies.forEach(dep => {
      if (!adj[dep.source_id]) adj[dep.source_id] = [];
      adj[dep.source_id].push(dep.target_id);
      if (!adj[dep.target_id]) adj[dep.target_id] = [];
      adj[dep.target_id].push(dep.source_id);
    });
    
    let head = 0;
    while (head < queue.length) {
      const u = queue[head++];
      const d = distances[u];
      const neighbors = adj[u] || [];
      for (const v of neighbors) {
        if (distances[v] === undefined) {
          distances[v] = d + 1;
          queue.push(v);
        }
      }
    }
    return distances;
  })();

  // Page Load Framer Motion Variants
  const pageVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.05
      }
    }
  };

  const sectionVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } }
  };

  return (
    <motion.div 
      variants={pageVariants}
      initial="hidden"
      animate="show"
      className="min-h-screen bg-transparent text-white font-sans flex flex-col p-6 gap-6 selection:bg-[#E50914] selection:text-white relative"
    >
      <AnimatePresence>
        {isBreachSequence && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.8, ease: "easeOut" } }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-[#0B0B0D] overflow-hidden pointer-events-none"
          >
            {/* Scanlines & Vignette */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] z-20 pointer-events-none opacity-50" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#000_120%)] z-10 opacity-90" />
            
            <motion.div 
              initial={{ scale: 0.8, filter: "blur(10px)" }}
              animate={{ scale: 1, filter: "blur(0px)" }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="relative z-30 flex flex-col items-center gap-4"
            >
              <motion.div 
                animate={{ opacity: [1, 0, 1, 0, 1], x: [0, -5, 5, -2, 0] }}
                transition={{ duration: 0.5, times: [0, 0.2, 0.4, 0.6, 1] }}
                className="text-5xl md:text-7xl font-black text-[#E50914] tracking-tighter mix-blend-screen drop-shadow-[0_0_20px_rgba(229,9,20,0.8)]"
              >
                SYSTEM BREACH DETECTED
              </motion.div>
              <div className="text-[#A3A3A8] text-sm tracking-[0.4em] font-bold uppercase animate-pulse">
                Initiating Diagnostic Override...
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 1. HeaderBar */}
      <HeaderBar 
        incidentId={resolvedParams.id}
        detectedAt={incident.detected_at}
        auditHash={incident.audit_hash}
        symptom={incident.symptom}
      />

      {/* 2. MetricStrip */}
      <MetricStrip incident={filteredIncidentView} />

      {/* 3 & 4. Centerpiece Topology + IncidentDetailPanel */}
      <motion.section 
        variants={sectionVariants}
        className="flex flex-col lg:flex-row gap-6 relative"
      >
        {/* Topology View (Resizes smoothly from 100% to 40%) */}
        <motion.div 
          layout
          transition={{ duration: 0.4, ease: "easeInOut" }}
          className={`bg-[#16161A] border border-[#2A2A2E] rounded-2xl overflow-hidden shadow-soft flex flex-col h-[550px] p-4 ${
            isDrawerOpen ? "w-full lg:w-[40%] shrink-0" : "w-full lg:w-full"
          }`}
        >
          <div className="flex-1 relative h-full w-full">
            <TopologyGraph
              topology={topology}
              incident={filteredIncidentView}
              highlightActive={true}
              expandedTiers={expandedTiers}
              onNodeClick={handleNodeClick}
            />
          </div>
        </motion.div>

        {/* Sliding Side Detail Panel */}
        <AnimatePresence mode="wait">
          {isDrawerOpen && (
            <IncidentDetailPanel 
              isOpen={isDrawerOpen}
              onClose={() => setIsDrawerOpen(false)}
              nodeId={drawerNodeId}
              isCluster={drawerIsCluster}
              tier={drawerTier}
              topology={topology}
              telemetryData={telemetry}
              incident={filteredIncidentView}
              onExpandTier={(tier) => setExpandedTiers((prev) => Array.from(new Set([...prev, tier])))}
              pathNodes={pathNodes}
            />
          )}
        </AnimatePresence>
      </motion.section>

      {/* 5. InvestigationTabs */}
      <motion.section variants={sectionVariants}>
        <InvestigationTabs 
          incident={incident}
          activeHypothesis={activeHypothesis}
          timelineFilterIndex={timelineFilterIndex}
          setTimelineFilterIndex={setTimelineFilterIndex}
        />
      </motion.section>

      {/* Tiny Operational Status Bar Footer */}
      <motion.footer 
        variants={sectionVariants}
        className="border-t border-[#2A2A2E]/50 pt-4 text-[10px] text-[#A3A3A8] flex items-center justify-between font-semibold"
      >
        <span>CONSOLE_FEED // STATUS: ACTIVE_DIAGNOSTICS</span>
        <span>NODE_COUNT: {topology?.components.length} // NOC_STABLE</span>
      </motion.footer>
    </motion.div>
  );
}
