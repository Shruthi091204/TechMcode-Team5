"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, ShieldCheck, Zap, ArrowRight, PlayCircle } from "lucide-react";
import Link from "next/link";
import { getTopology, getAuditVerification, getUsageStats, UsageStats, AuditVerification } from "../lib/api";
import { Component } from "../lib/types";
import IncidentUploader from "../components/IncidentUploader";

const BADGE_TONES: Record<string, string> = {
  green: "text-[var(--accent-green)] bg-[var(--accent-green)]/10",
  amber: "text-[var(--accent-amber)] bg-[var(--accent-amber)]/10",
  muted: "text-[var(--text-tertiary)] bg-[var(--text-tertiary)]/10",
};

interface StatCardProps {
  icon: React.ReactNode;
  value: number;
  label: string;
  badge: string;
  badgeTone: "green" | "amber" | "muted";
  loading: boolean;
  highlight?: boolean;
}

function StatCard({ icon, value, label, badge, badgeTone, loading, highlight }: StatCardProps) {
  return (
    <div
      className={`surface interactive p-5 sm:p-6 flex flex-col justify-between gap-4 ${
        highlight ? "border-[var(--accent-amber)]/30" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <span className={highlight ? "text-[var(--accent-amber)]" : "text-[var(--text-tertiary)]"}>{icon}</span>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${BADGE_TONES[badgeTone]}`}>
          {badge}
        </span>
      </div>
      <div>
        {loading ? (
          <div className="skeleton h-8 w-16 mb-2" aria-hidden />
        ) : (
          <div className="text-3xl font-black text-white tabular-nums leading-none">{value}</div>
        )}
        <div className="text-[11px] text-[var(--text-tertiary)] font-bold uppercase tracking-wider mt-2">{label}</div>
      </div>
    </div>
  );
}

export default function Home() {
  const [nodes, setNodes] = useState<Component[]>([]);
  const [auditStatus, setAuditStatus] = useState<AuditVerification | null>(null);
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
    <div className="relative overflow-hidden">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[560px] bg-[var(--accent-red)]/5 rounded-full blur-[130px]" />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="relative max-w-[1120px] mx-auto px-4 sm:px-6 py-12 sm:py-16 flex flex-col gap-10 z-10"
      >
        {/* HERO */}
        <motion.div variants={itemVariants} className="flex flex-col gap-4 max-w-3xl">
          <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--accent-red)]">
            Network Operations Center
          </span>
          <h1 className="text-4xl sm:text-6xl font-black tracking-tighter text-white leading-[0.98]">
            Find the cause,
            <br />
            not the loudest victim.
          </h1>
          <p className="text-[var(--text-secondary)] text-base sm:text-lg font-medium leading-relaxed max-w-2xl">
            Topology-constrained causal analysis names the component that actually caused the outage, with cited
            evidence, a deterministic ranking, and agentic-RAG remediation grounded in your NOC runbooks.
          </p>
        </motion.div>

        {/* STATS STRIP */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            icon={<Activity size={18} aria-hidden />}
            value={nodes.length}
            label="Monitored Nodes"
            badge="Online"
            badgeTone="green"
            loading={loading}
          />
          <StatCard
            icon={<ShieldCheck size={18} aria-hidden />}
            value={auditStatus?.total_events ?? 0}
            label="Audit Ledger Events"
            badge={auditStatus?.is_valid ? "Verified" : "Checking"}
            badgeTone={auditStatus?.is_valid ? "green" : "amber"}
            loading={loading}
          />
          <StatCard
            icon={<Zap size={18} aria-hidden />}
            value={incidentsAnalyzed}
            label={incidentsAnalyzed === 1 ? "Incident Analyzed" : "Incidents Analyzed"}
            badge={incidentsAnalyzed > 0 ? "Live" : "Idle"}
            badgeTone={incidentsAnalyzed > 0 ? "amber" : "muted"}
            loading={loading}
            highlight={incidentsAnalyzed > 0}
          />
        </motion.div>

        {/* ENTRY POINTS: reference demo + bring your own data */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
          {/* Reference incident card */}
          <div className="surface p-6 flex flex-col justify-between gap-6">
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2.5">
                <span className="w-9 h-9 rounded-[var(--radius-md)] bg-[var(--accent-red)]/12 text-[var(--accent-red)] flex items-center justify-center shrink-0">
                  <PlayCircle size={18} aria-hidden />
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[var(--accent-red)]/10 text-[var(--accent-red)]">
                  Live reference incident
                </span>
              </div>
              <h3 className="text-white text-lg font-bold">See it work in one click</h3>
              <p className="text-[var(--text-secondary)] text-sm leading-relaxed">
                A fully worked incident: a database connection-pool exhaustion propagating to the web tier. Ranked
                cause, three-tier evidence ledger, timeline, and agentic-RAG remediation, all pre-computed.
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                {["INC-1001", "db-01 → web-02", `${nodes.length || 30} nodes`].map((chip) => (
                  <span
                    key={chip}
                    className="text-[10.5px] font-semibold text-[var(--text-secondary)] bg-[var(--bg-panel-raised)] border border-[var(--line-hairline)] rounded px-2 py-0.5"
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </div>
            <Link
              href="/incident/INC-1001"
              className="interactive group bg-[var(--accent-red)] hover:bg-[#c00811] text-white px-5 py-3 rounded-[var(--radius-md)] font-bold uppercase tracking-wider text-xs flex items-center justify-center gap-2.5 shadow-lifted"
            >
              <span>Launch Incident Dashboard</span>
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </div>

          {/* Upload panel */}
          <IncidentUploader />
        </motion.div>
      </motion.div>
    </div>
  );
}
