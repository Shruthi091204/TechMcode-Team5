"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

interface Stage {
  label: string;
  detail: string;
}

const DETERMINISTIC_STAGES: Stage[] = [
  { label: "Detecting anomalies", detail: "change-point + robust baseline" },
  { label: "Constraining suspects", detail: "topology paths to the symptom" },
  { label: "Ranking root cause", detail: "attribution + evidence ledger" },
];

const ENRICHED_STAGES: Stage[] = [
  ...DETERMINISTIC_STAGES,
  { label: "Retrieving runbooks", detail: "semantic search over the knowledge base" },
  { label: "Verifying and narrating", detail: "skeptic, investigator, remediation" },
];

interface AnalysisProgressProps {
  enriched: boolean;
  label: string;
}

export default function AnalysisProgress({ enriched, label }: AnalysisProgressProps) {
  const stages = enriched ? ENRICHED_STAGES : DETERMINISTIC_STAGES;
  const stepMs = enriched ? 7000 : 900;
  const [active, setActive] = useState(0);

  useEffect(() => {
    setActive(0);
    const timer = setInterval(() => {
      setActive((current) => (current >= stages.length - 1 ? current : current + 1));
    }, stepMs);
    return () => clearInterval(timer);
  }, [stages.length, stepMs]);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="overflow-hidden"
      role="status"
      aria-live="polite"
      aria-label={`Analyzing ${label}`}
    >
      <div className="surface-raised p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[11px] font-bold uppercase tracking-wider text-white">{label}</span>
          <span className="text-[10px] font-semibold text-[var(--text-tertiary)]">
            {enriched ? "Full AI investigation" : "Deterministic engine"}
          </span>
        </div>

        <div className="h-1 w-full rounded-full bg-[var(--bg-sunken)] overflow-hidden">
          <div className="indeterminate-bar h-full w-1/3 rounded-full bg-[var(--accent-red)]" />
        </div>

        <ol className="flex flex-col gap-2">
          {stages.map((stage, index) => {
            const done = index < active;
            const running = index === active;
            return (
              <li key={stage.label} className="flex items-start gap-2.5">
                <span className="mt-0.5 shrink-0 w-4 h-4 flex items-center justify-center">
                  <AnimatePresence mode="wait" initial={false}>
                    {done ? (
                      <motion.span
                        key="done"
                        initial={{ scale: 0.6, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="text-[var(--accent-green)]"
                      >
                        <Check size={13} strokeWidth={3} />
                      </motion.span>
                    ) : running ? (
                      <motion.span key="run" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-[var(--accent-red)]">
                        <Loader2 size={13} className="animate-spin" />
                      </motion.span>
                    ) : (
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--line-strong)]" />
                    )}
                  </AnimatePresence>
                </span>
                <span className="flex flex-col leading-tight">
                  <span
                    className={`text-[12px] font-semibold transition-colors ${
                      done ? "text-[var(--text-secondary)]" : running ? "text-white" : "text-[var(--text-tertiary)]"
                    }`}
                  >
                    {stage.label}
                  </span>
                  <span className="text-[10.5px] text-[var(--text-tertiary)]">{stage.detail}</span>
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </motion.div>
  );
}
