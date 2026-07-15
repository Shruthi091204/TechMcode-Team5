"use client";

import React from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";

interface AnalysisProgressProps {
  currentStep: number;
}

export default function AnalysisProgress({ currentStep }: AnalysisProgressProps) {
  const steps = [
    { label: "Loading telemetry...", stepNum: 1 },
    { label: "Correlating logs...", stepNum: 2 },
    { label: "Processing alerts...", stepNum: 3 },
    { label: "Building topology graph...", stepNum: 4 },
    { label: "Reading configuration changes...", stepNum: 5 },
    { label: "Running anomaly detection...", stepNum: 6 },
    { label: "Performing causal reasoning...", stepNum: 7 },
    { label: "Ranking root-cause hypotheses...", stepNum: 8 },
    { label: "Generating AI explanation...", stepNum: 9 },
    { label: "Complete.", stepNum: 10 },
  ];

  return (
    <div className="w-full bg-panel border border-border-muted p-5 rounded-xl font-mono text-xs select-none">
      <div className="text-[10px] tracking-[0.15em] font-bold text-grey-muted border-b border-border-muted/10 pb-2 mb-3">
        ACTIVE_REASONING_PIPELINE // ANALYZING_SCENARIO
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
        {steps.map((step) => {
          const isCompleted = currentStep > step.stepNum;
          const isCurrent = currentStep === step.stepNum;

          return (
            <div
              key={step.stepNum}
              className={`flex items-center gap-2.5 py-1 transition-all duration-300 ${
                isCurrent
                  ? "text-red-critical text-status-glow scale-[1.02] pl-1 font-bold"
                  : isCompleted
                  ? "text-confirmed"
                  : "text-grey-muted/40"
              }`}
            >
              {isCompleted ? (
                <CheckCircle2 size={14} className="text-confirmed shrink-0" />
              ) : isCurrent ? (
                <Loader2 size={14} className="animate-spin text-red-critical shrink-0 text-status-glow" />
              ) : (
                <Circle size={14} className="text-grey-muted/20 shrink-0" />
              )}
              <span className={isCompleted ? "line-through opacity-60" : ""}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
