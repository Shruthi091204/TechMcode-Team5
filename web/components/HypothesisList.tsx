"use client";

import React from "react";
import { IncidentReport } from "../lib/types";
interface HypothesisListProps {
  incident: IncidentReport;
  selectedRank?: number;
  onSelectRank?: (rank: number) => void;
}

export default function HypothesisList({
  incident,
  selectedRank = 1,
  onSelectRank,
}: HypothesisListProps) {
  return (
    <div className="w-full font-mono select-none">
      <div className="text-[10px] tracking-[0.15em] font-bold text-grey-muted mb-3 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span>ROOT_CAUSE_HYPOTHESES // RANKED</span>
        <span>COUNT: {incident.hypotheses.length}</span>
      </div>

      <div className="flex flex-col gap-3">
        {incident.hypotheses
          .sort((a, b) => a.rank - b.rank)
          .map((hyp) => {
            const isSelected = hyp.rank === selectedRank;
            const confidencePercentage = Math.round(hyp.confidence * 100);

            return (
              <div
                key={hyp.rank}
                onClick={() => onSelectRank?.(hyp.rank)}
                className={`p-3 border transition-all duration-300 cursor-pointer rounded-lg ${
                  isSelected
                    ? "border-red-critical bg-panel-raised state-active-glow"
                    : "border-border-muted hover:state-active-glow bg-background/10"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-1.5 py-0.5 border ${
                        hyp.rank === 1
                          ? "border-red-critical text-red-critical bg-red-critical/5 text-status-glow"
                          : "border-border-muted text-grey-muted"
                      }`}
                    >
                      RANK_{hyp.rank.toString().padStart(2, "0")}
                    </span>
                    <span className="text-sm font-bold text-white-signal">{hyp.root_cause_component}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-grey-muted mr-2">CONFIDENCE:</span>
                    <span className="text-sm font-bold tabular-nums text-white-signal">{confidencePercentage}%</span>
                  </div>
                </div>

                <div className="text-[12px] text-white-signal mb-3">{hyp.fault_type}</div>

                {/* Confidence bar */}
                <div className="w-full h-1 bg-[#1A1A1E] mb-3">
                  <div
                    className={`h-full ${hyp.rank === 1 ? "bg-red-critical text-status-glow" : "bg-grey-muted"}`}
                    style={{ width: `${confidencePercentage}%` }}
                  />
                </div>

                {/* Metrics row */}
                <div className="flex justify-between items-center text-[10px] text-grey-muted mb-2">
                  <span>CAUSAL_SCORE: <span className="text-white-signal font-bold">{hyp.causal_score.toFixed(1)}</span></span>
                  <span>PATH_HOPS: <span className="text-white-signal font-bold">{hyp.topology_path.length}</span></span>
                </div>

                {/* Topology Breadcrumb */}
                <div className="text-[11px] text-text-muted mt-2 pt-2 border-t border-border-muted/10 overflow-x-auto whitespace-nowrap scrollbar-thin">
                  {hyp.topology_path.map((node, index) => {
                    const isLast = index === hyp.topology_path.length - 1;
                    const isRoot = index === 0;

                    return (
                      <span key={node} className="inline-flex items-center">
                        <span
                          className={`${
                            isRoot
                              ? "text-primary font-bold"
                              : isLast
                              ? "text-foreground"
                              : "text-text-muted"
                          }`}
                        >
                          {node}
                        </span>
                        {!isLast && <span className="mx-1 text-text-muted/40">→</span>}
                      </span>
                    );
                  })}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}
