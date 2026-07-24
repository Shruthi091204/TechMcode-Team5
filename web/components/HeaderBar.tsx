"use client";

import React from "react";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

interface HeaderBarProps {
  incidentId: string;
  detectedAt: string;
  auditHash: string;
  symptom: string;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatDetected(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.replace("T", " ").replace("Z", " UTC");
  }
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(parsed.getUTCDate())} ${MONTHS[parsed.getUTCMonth()]} ${parsed.getUTCFullYear()}, ${pad(parsed.getUTCHours())}:${pad(parsed.getUTCMinutes())} UTC`;
}

export default function HeaderBar({ incidentId, detectedAt, auditHash, symptom }: HeaderBarProps) {
  return (
    <motion.header 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="py-10 flex flex-col gap-4 border-b border-[#2A2A2E]/50 mb-2"
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 sm:gap-4">
          <Link
            href="/"
            aria-label="Back to operations console"
            className="interactive shrink-0 w-9 h-9 rounded-[var(--radius-md)] border border-[var(--line-hairline)] bg-[var(--bg-panel)] flex items-center justify-center text-[var(--text-secondary)] hover:text-white"
          >
            <ArrowLeft size={16} aria-hidden />
          </Link>
          <div className="bg-white p-1 rounded-md shadow-[0_0_15px_rgba(255,255,255,0.1)] flex items-center justify-center shrink-0">
            <img
              src="/tech_mahindra_logo_uploaded.png?v=2"
              alt="Tech Mahindra"
              className="h-8 w-8 object-contain mix-blend-multiply"
            />
          </div>
          <div className="flex items-center gap-2 text-[11px] text-[var(--text-secondary)] font-bold tracking-wide flex-wrap">
            <span className="inline-block w-2 h-2 bg-[var(--accent-red)] rounded-full animate-ping shadow-[0_0_8px_#E50914]" aria-hidden></span>
            <span>Incident ID: {incidentId}</span>
            <span className="text-[var(--text-tertiary)]" aria-hidden>•</span>
            <span>Detected: {formatDetected(detectedAt)}</span>
          </div>
        </div>
        <div
          title={auditHash}
          className="text-[10px] bg-[var(--bg-panel-raised)] px-3.5 py-1.5 font-bold text-[var(--text-secondary)] rounded-full tracking-wide shadow-soft border border-[var(--line-hairline)]"
        >
          Audit Hash: {auditHash.slice(0, 12)}
        </div>
      </div>
      
      <div className="mt-2 flex items-start gap-4">
        <div className="shrink-0 w-9 h-9 mt-1 rounded-xl bg-[#E50914] flex items-center justify-center shadow-[0_0_12px_#E50914]">
          <ShieldAlert size={20} className="text-white" />
        </div>
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white leading-tight select-none" style={{ fontWeight: 900 }}>
            {symptom.includes(' CROSSED ') 
              ? `${symptom.split(' CROSSED ')[0]} Spike` 
              : symptom.split(',')[0]}
          </h1>
          <p className="text-sm font-medium text-[#A3A3A8] tracking-wide mt-1 leading-relaxed max-w-2xl border-l-2 border-[#E50914] pl-3">
            {symptom.includes(' CROSSED ') 
              ? `Crossed ${symptom.split(' CROSSED ').slice(1).join(' CROSSED ').toLowerCase()}`
              : symptom.includes(',') 
                ? symptom.split(',').slice(1).join(',').trim()
                : "Critical system degradation detected in the topology."}
          </p>
        </div>
      </div>
    </motion.header>
  );
}
