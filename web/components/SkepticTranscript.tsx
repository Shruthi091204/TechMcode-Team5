"use client";

import React from "react";
import { IncidentReport } from "../lib/types";
interface SkepticTranscriptProps {
  incident: IncidentReport;
}

export default function SkepticTranscript({ incident }: SkepticTranscriptProps) {
  const activeHypothesis = incident.hypotheses.find((h) => h.rank === 1);
  const skepticVerdict = activeHypothesis?.skeptic_verdict || "No skeptic analysis available for this incident.";

  // Splitting the verdict into a structured chat transcript for NOC aesthetics
  const transcript = [
    {
      speaker: "INVESTIGATOR_AI",
      message: `Root Cause Analysis indicates ${activeHypothesis?.root_cause_component} underwent a critical fault: ${activeHypothesis?.fault_type}. Deployment config audit confirms max_connections changed.`,
      time: "09:28:15",
      color: "text-[#FFFFFF]",
    },
    {
      speaker: "SKEPTIC_BOT",
      message: skepticVerdict,
      time: "09:29:02",
      color: "text-[#E8A94B]",
    },
    {
      speaker: "INVESTIGATOR_AI",
      message: "Acknowledged. However, the telemetry timeline places the database connection pool saturation exactly 25 seconds before the packet retransmissions began on tor-03, pointing to downstream queue backlog rather than line corruption.",
      time: "09:29:45",
      color: "text-[#FFFFFF]",
    },
  ];

  return (
    <div className="w-full bg-panel border border-border-muted/20 p-4 font-mono select-none">
      <div className="text-xs text-text-muted mb-3 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span>SKEPTIC_VERDICT_TRANSCRIPT // HYPOTHESIS_VALIDATION</span>
        <span className="text-[10px] text-correlated">CRITICAL_REVIEW</span>
      </div>

      <div className="flex flex-col gap-4 overflow-y-auto max-h-[350px] pr-2">
        {transcript.map((chat, idx) => (
          <div key={idx} className="border-l border-border-muted/20 pl-3">
            <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
              <span className={`font-bold ${chat.color}`}>[{chat.speaker}]</span>
              <span className="tabular-nums">{chat.time}</span>
            </div>
            <div className="text-xs text-foreground leading-relaxed">
              {chat.message}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
