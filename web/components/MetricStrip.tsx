"use client";

import React from "react";
import { motion } from "framer-motion";
import { IncidentReport } from "../lib/types";

interface MetricStripProps {
  incident: IncidentReport;
}

export default function MetricStrip({ incident }: MetricStripProps) {
  // Derived from the actual incident report — not hardcoded
  const timeline = incident.timeline || [];
  const logCount = timeline.filter((event) => event.kind === "log").length;
  const alertCount = timeline.filter((event) => event.kind === "alert").length;
  const configEvents = timeline.filter((event) => event.kind === "config");
  const configId = configEvents[0]?.description.match(/CHG-\d+/)?.[0];

  const latencyMatch = incident.symptom?.match(/([\d.]+)\s*ms/);
  const deviationMatch = incident.symptom?.match(/([+-]?\d+)\s*%/);
  const telemetryValue = latencyMatch ? `${latencyMatch[1]} ms` : incident.symptom_component;
  const telemetryStatus = deviationMatch ? `${deviationMatch[1]}% Deviation` : "Baseline breach";

  const cards = [
    {
      label: "Telemetry",
      value: telemetryValue,
      status: telemetryStatus,
      severity: "critical",
    },
    {
      label: "Logs",
      value: `${logCount}`,
      status: logCount ? `${logCount} log event${logCount === 1 ? "" : "s"}` : "No log events",
      severity: "normal",
    },
    {
      label: "Alerts",
      value: `${alertCount} Active`,
      status: alertCount ? "Threshold breaches" : "None active",
      severity: alertCount ? "critical" : "normal",
    },
    {
      label: "Config Changes",
      value: `${configEvents.length} Tracked`,
      status: configId || (configEvents.length ? "Change tracked" : "None tracked"),
      severity: configEvents.length ? "elevated" : "normal",
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
    show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } },
  };

  return (
    <motion.section 
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6"
    >
      {cards.map((card, idx) => {
        const isCritical = card.severity === "critical";
        const isElevated = card.severity === "elevated";

        const valueColor = isCritical
          ? "text-[var(--accent-red)] text-status-glow"
          : isElevated
            ? "text-[var(--accent-amber)]"
            : "text-white";

        const accentBorder = isCritical
          ? "border-[var(--accent-red)]/35"
          : isElevated
            ? "border-[var(--accent-amber)]/30"
            : "border-[var(--line-hairline)]";

        return (
          <motion.div
            key={idx}
            variants={itemVariants}
            className={`surface interactive border ${accentBorder} p-5 sm:p-6 flex flex-col justify-between min-h-[120px] select-none relative overflow-hidden`}
          >
            {isCritical ? (
              <span className="absolute inset-x-0 top-0 h-0.5 bg-[var(--accent-red)]" aria-hidden />
            ) : null}
            <div className="text-[11px] tracking-[0.08em] uppercase font-bold text-[var(--text-tertiary)]">
              {card.label}
            </div>
            <div className="mt-2">
              <div
                className={`text-2xl sm:text-3xl font-black tabular-nums ${valueColor}`}
                style={{ fontWeight: 900, letterSpacing: "-0.02em" }}
              >
                {card.value}
              </div>
              <div
                className={`text-[12px] font-medium mt-1 ${
                  isCritical ? "text-[var(--accent-red)]" : "text-[var(--text-secondary)]"
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
