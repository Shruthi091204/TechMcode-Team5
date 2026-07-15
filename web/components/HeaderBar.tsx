"use client";

import React from "react";
import { ShieldAlert } from "lucide-react";
import { motion } from "framer-motion";

interface HeaderBarProps {
  incidentId: string;
  detectedAt: string;
  auditHash: string;
  symptom: string;
}

export default function HeaderBar({ incidentId, detectedAt, auditHash, symptom }: HeaderBarProps) {
  return (
    <motion.header 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="py-10 flex flex-col gap-4 border-b border-[#2A2A2E]/50 mb-2"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-[10px] text-[#6B6B70] font-bold tracking-widest uppercase">
          <span className="inline-block w-2.5 h-2.5 bg-[#E50914] rounded-full animate-ping"></span>
          <span>INCIDENT: {incidentId}</span>
          <span>•</span>
          <span>DETECTED: {detectedAt}</span>
        </div>
        <div className="text-[10px] bg-[#16161A] px-3.5 py-1.5 font-bold text-[#6B6B70] rounded-full uppercase tracking-wider shadow-soft">
          {auditHash.slice(0, 12)}
        </div>
      </div>
      
      <div className="mt-2 flex items-center gap-4">
        <div className="shrink-0 w-8 h-8 rounded-full bg-[#E50914] flex items-center justify-center shadow-[0_0_12px_#E50914]">
          <ShieldAlert size={18} className="text-white" />
        </div>
        <h1 className="text-3xl sm:text-4xl font-black tracking-tighter text-white uppercase leading-tight select-none" style={{ fontWeight: 900, letterSpacing: "-0.02em" }}>
          {symptom}
        </h1>
      </div>
    </motion.header>
  );
}
