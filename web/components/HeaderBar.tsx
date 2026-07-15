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
        <div className="flex items-center gap-4">
          <div className="bg-white p-1 rounded-md shadow-[0_0_15px_rgba(255,255,255,0.1)] flex items-center justify-center">
            <img 
              src="/tech_mahindra_logo_uploaded.png?v=2" 
              alt="Tech Mahindra" 
              className="h-8 w-8 object-contain mix-blend-multiply"
            />
          </div>
          <div className="flex items-center gap-2 text-[11px] text-[#A3A3A8] font-bold tracking-wide">
            <span className="inline-block w-2 h-2 bg-[#E50914] rounded-full animate-ping shadow-[0_0_8px_#E50914]"></span>
            <span>Incident ID: {incidentId}</span>
            <span className="text-[#6B6B70]">•</span>
            <span>Detected: {detectedAt}</span>
          </div>
        </div>
        <div className="text-[10px] bg-[#1F1F24] px-3.5 py-1.5 font-bold text-[#A3A3A8] rounded-full tracking-wide shadow-soft border border-[#2A2A2E]">
          Audit Hash: {auditHash.slice(0, 12)}
        </div>
      </div>
      
      <div className="mt-2 flex items-center gap-4">
        <div className="shrink-0 w-8 h-8 rounded-full bg-[#E50914] flex items-center justify-center shadow-[0_0_12px_#E50914]">
          <ShieldAlert size={18} className="text-white" />
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
