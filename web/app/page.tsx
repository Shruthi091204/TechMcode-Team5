"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, ShieldCheck, Zap, ArrowRight } from "lucide-react";
import Link from "next/link";
import { getTopology, getAuditVerification, getUsageStats, UsageStats } from "../lib/api";
import { Component } from "../lib/types";
import IncidentUploader from "../components/IncidentUploader";

export default function Home() {
  const [nodes, setNodes] = useState<Component[]>([]);
  const [auditStatus, setAuditStatus] = useState<any>(null);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      getTopology().catch(() => ({ components: [] })),
      getAuditVerification().catch(() => null),
      getUsageStats().catch(() => null)
    ]).then(([topo, audit, usage]) => {
      if (!active) return;
      setNodes(topo.components);
      setAuditStatus(audit);
      setStats(usage);
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const incidentsAnalyzed = stats?.incidents_analyzed ?? 0;

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } }
  };

  return (
    <div className="min-h-screen bg-transparent text-white font-sans p-8 flex flex-col items-center justify-center relative overflow-hidden selection:bg-[#E50914] selection:text-white">
      {/* Background ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-[#E50914]/5 rounded-full blur-[120px] pointer-events-none" />

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="w-full max-w-5xl flex flex-col gap-12 z-10"
      >
        {/* HERO SECTION */}
        <motion.div variants={itemVariants} className="text-center flex flex-col items-center gap-4">
          <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-white">
            NETWORK OPERATIONS
          </h1>
          <p className="text-[#A3A3A8] text-lg max-w-2xl font-medium">
            AI-driven root cause analysis, automated topological propagation tracking, and cryptographically verified evidence ledgers.
          </p>
        </motion.div>

        {/* METRICS & AUDIT ROW */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-[#16161A] border border-[#2A2A2E] p-6 rounded-2xl flex flex-col justify-between shadow-soft hover:border-[#2A2A2E]/80 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <Activity size={20} className="text-[#A3A3A8]" />
              <span className="text-[10px] font-bold text-[#2ECC71] uppercase tracking-wider bg-[#2ECC71]/10 px-2 py-0.5 rounded">Online</span>
            </div>
            <div>
              <div className="text-3xl font-black text-white">{loading ? "..." : nodes.length}</div>
              <div className="text-[11px] text-[#6B6B70] font-bold uppercase tracking-wider mt-1">Monitored Nodes</div>
            </div>
          </div>

          <div className="bg-[#16161A] border border-[#2A2A2E] p-6 rounded-2xl flex flex-col justify-between shadow-soft hover:border-[#2A2A2E]/80 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <ShieldCheck size={20} className="text-[#A3A3A8]" />
              {auditStatus?.is_valid ? (
                <span className="text-[10px] font-bold text-[#2ECC71] uppercase tracking-wider bg-[#2ECC71]/10 px-2 py-0.5 rounded">Verified</span>
              ) : (
                <span className="text-[10px] font-bold text-[#FFA53B] uppercase tracking-wider bg-[#FFA53B]/10 px-2 py-0.5 rounded">Checking</span>
              )}
            </div>
            <div>
              <div className="text-3xl font-black text-white">{loading ? "..." : (auditStatus?.total_events ?? 0)}</div>
              <div className="text-[11px] text-[#6B6B70] font-bold uppercase tracking-wider mt-1">Audit Ledger Events</div>
            </div>
          </div>

          <div className="bg-[#16161A] border border-[#2A2A2E] p-6 rounded-2xl flex flex-col justify-between shadow-soft hover:border-[#2A2A2E]/80 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <Zap size={20} className={incidentsAnalyzed > 0 ? "text-[#FFA53B]" : "text-[#A3A3A8]"} />
              {incidentsAnalyzed > 0 ? (
                <span className="text-[10px] font-bold text-[#FFA53B] uppercase tracking-wider bg-[#FFA53B]/10 px-2 py-0.5 rounded">Live</span>
              ) : (
                <span className="text-[10px] font-bold text-[#6B6B70] uppercase tracking-wider bg-[#6B6B70]/10 px-2 py-0.5 rounded">Idle</span>
              )}
            </div>
            <div>
              <div className="text-3xl font-black text-white">{loading ? "..." : incidentsAnalyzed}</div>
              <div className="text-[11px] text-[#6B6B70] font-bold uppercase tracking-wider mt-1">{incidentsAnalyzed === 1 ? "Incident Analyzed" : "Incidents Analyzed"}</div>
            </div>
          </div>
        </motion.div>

        {/* ENTER DASHBOARD CTA */}
        <motion.div variants={itemVariants} className="flex justify-center mt-4">
          <Link href="/incident/INC-1001">
            <motion.div
              whileHover={{ scale: 1.05, boxShadow: "0 10px 40px -10px rgba(229,9,20,0.5)" }}
              whileTap={{ scale: 0.95 }}
              className="bg-[#E50914] hover:bg-[#b8070f] text-white px-8 py-4 rounded-full font-bold uppercase tracking-widest text-sm flex items-center gap-3 shadow-lifted transition-all cursor-pointer"
            >
              <span>Launch Incident Dashboard</span>
              <ArrowRight size={18} />
            </motion.div>
          </Link>
        </motion.div>

        {/* UPLOAD / ANALYZE YOUR OWN INCIDENT */}
        <motion.div variants={itemVariants} className="w-full max-w-2xl mx-auto">
          <IncidentUploader />
        </motion.div>
      </motion.div>
    </div>
  );
}
