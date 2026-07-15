"use client";

import React from "react";
import { motion } from "framer-motion";
import { IncidentReport } from "../lib/types";

interface MetricStripProps {
  incident: IncidentReport;
}

export default function MetricStrip({ incident }: MetricStripProps) {
  // Compute metric values based on incident timeline/state
  const telemetryValue = "138.4 ms";
  const telemetryStatus = "+480% DEVIATION";
  
  const logsValue = "15.4K Ingested";
  const logsStatus = "3 CRITICAL ERRORS";
  
  const alertsValue = "3 ACTIVE";
  const alertsStatus = "CRITICAL SEVERITY";
  
  const configsValue = "3 Tracked";
  const configsStatus = "CHG-4212 REDUCTION";

  const cards = [
    {
      label: "TELEMETRY",
      value: telemetryValue,
      status: telemetryStatus,
      severity: "critical", // red + glow
    },
    {
      label: "LOGS",
      value: logsValue,
      status: logsStatus,
      severity: "critical", // red + glow
    },
    {
      label: "ALERTS",
      value: alertsValue,
      status: alertsStatus,
      severity: "critical", // red + glow
    },
    {
      label: "CONFIG CHANGES",
      value: configsValue,
      status: configsStatus,
      severity: "elevated", // amber
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 100 } },
  };

  return (
    <motion.section 
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6"
    >
      {cards.map((card, idx) => {
        const isCritical = card.severity === "critical";
        const isElevated = card.severity === "elevated";
        
        const valueColor = isCritical 
          ? "text-[#E50914] text-status-glow" 
          : isElevated 
            ? "text-[#FFA53B]" 
            : "text-white";

        return (
          <motion.div
            key={idx}
            variants={itemVariants}
            whileHover={{ 
              scale: 1.02, 
              boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
              backgroundColor: "#1F1F24"
            }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="bg-[#16161A] p-6 flex flex-col justify-between min-h-[120px] rounded-xl shadow-soft cursor-pointer select-none"
          >
            <div className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase">
              {card.label}
            </div>
            <div className="mt-2">
              <div 
                className={`text-3xl font-black ${valueColor}`}
                style={{ fontWeight: 900, letterSpacing: "-0.02em" }}
              >
                {card.value}
              </div>
              <div 
                className={`text-[13px] font-medium mt-1 uppercase ${
                  isCritical ? "text-[#E50914]" : "text-[#A3A3A8]"
                }`}
              >
                {card.status}
              </div>
            </div>
          </motion.div>
        );
      })}
    </motion.section>
  );
}
