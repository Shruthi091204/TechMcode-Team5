"use client";

import React from "react";
import { IncidentReport } from "../lib/types";
interface CounterfactualPanelProps {
  incident: IncidentReport;
  active: boolean;
  onToggle: (active: boolean) => void;
}

export default function CounterfactualPanel({
  incident,
  active,
  onToggle,
}: CounterfactualPanelProps) {
  const activeHypothesis = incident.hypotheses.find((h) => h.rank === 1);
  const counterfactualStatement = activeHypothesis?.counterfactual || "No counterfactual simulation available.";

  return (
    <div className="w-full bg-panel border border-border-muted/20 p-4 font-mono select-none">
      <div className="text-xs text-text-muted mb-3 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span>COUNTERFACTUAL_SIMULATION_ENGINE</span>
        <span className="text-[10px] text-confirmed">READY</span>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex-1">
          <div className="text-xs font-bold text-foreground mb-1 uppercase">
            {active ? "STATE: [SIMULATING_NORMAL]" : "STATE: [OBSERVED_INCIDENT]"}
          </div>
          <div className="text-xs text-text-muted leading-relaxed">
            {active
              ? `Hypothetical state: ${counterfactualStatement}`
              : "Toggle simulation to isolate the primary config change and trace recovery paths."}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold ${active ? "text-confirmed" : "text-text-muted"}`}>
            SIMULATE_RECOVERY
          </span>
          <button
            onClick={() => onToggle(!active)}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer transition-colors duration-200 ease-in-out border border-border-muted/30 ${
              active ? "bg-confirmed" : "bg-background"
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 bg-foreground transform transition duration-200 ease-in-out ${
                active ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}
