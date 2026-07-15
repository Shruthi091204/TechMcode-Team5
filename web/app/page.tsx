"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, ShieldCheck, Zap, ArrowRight, ShieldAlert, Database, Scissors, Settings, WifiOff, Radar } from "lucide-react";
import Link from "next/link";
import { getTopology, getAuditVerification } from "../lib/api";
import { Component } from "../lib/types";

const DEMO_SCENARIOS = [
  { id: "link_degradation", label: "Fiber Cut", icon: Scissors, color: "text-[#E50914]" },
  { id: "bad_config_push", label: "Bad Configuration", icon: Settings, color: "text-[#FFA53B]" },
  { id: "ddos_flood", label: "DDoS Attack", icon: ShieldAlert, color: "text-[#E50914]" },
  { id: "capacity_exhaustion", label: "Pool Exhaustion", icon: Database, color: "text-[#FFA53B]" },
  { id: "nic_failure", label: "NIC Failure", icon: WifiOff, color: "text-[#A3A3A8]" },
  { id: "port_scan", label: "Port Scan", icon: Radar, color: "text-[#2ECC71]" },
];

export default function Home() {
  const [nodes, setNodes] = useState<Component[]>([]);
  const [auditStatus, setAuditStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      getTopology().catch(() => ({ components: [] })),
      getAuditVerification().catch(() => null)
    ]).then(([topo, audit]) => {
      if (!active) return;
      setNodes(topo.components);
      setAuditStatus(audit);
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
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
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#E50914]/10 border border-[#E50914]/20 text-[#E50914] text-[10px] font-bold uppercase tracking-widest mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#E50914] animate-pulse" />
            Global Diagnostics Active
          </div>
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
              <div className="text-3xl font-black text-white">{loading ? "..." : (auditStatus?.verified_events || 0)}</div>
              <div className="text-[11px] text-[#6B6B70] font-bold uppercase tracking-wider mt-1">Audit Ledger Events</div>
            </div>
          </div>

          <div className="bg-[#16161A] border border-[#2A2A2E] p-6 rounded-2xl flex flex-col justify-between shadow-soft hover:border-[#2A2A2E]/80 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <Zap size={20} className="text-[#E50914]" />
              <span className="text-[10px] font-bold text-[#E50914] uppercase tracking-wider bg-[#E50914]/10 px-2 py-0.5 rounded">High Alert</span>
            </div>
            <div>
              <div className="text-3xl font-black text-white">1</div>
              <div className="text-[11px] text-[#6B6B70] font-bold uppercase tracking-wider mt-1">Active Incident</div>
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
        
        {/* SCENARIOS PREVIEW ROW */}
        <motion.div variants={itemVariants} className="pt-12 border-t border-[#2A2A2E]/50 w-full flex flex-col items-center">
          <span className="text-[10px] text-[#6B6B70] font-bold uppercase tracking-widest mb-6 text-center">Available Investigation Scenarios</span>
          <div className="flex flex-wrap justify-center gap-6">
            {DEMO_SCENARIOS.map((sc) => {
              const Icon = sc.icon;
              return (
                <div key={sc.id} className="flex items-center gap-3 text-[#A3A3A8] opacity-70">
                  <Icon size={16} className={sc.color} />
                  <span className="text-xs font-semibold">{sc.label}</span>
                </div>
              );
            })}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
