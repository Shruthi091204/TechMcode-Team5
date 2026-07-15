"use client";

import React from "react";
import { IncidentReport } from "../lib/types";

interface EvidenceLedgerProps {
  incident: IncidentReport;
}

export default function EvidenceLedger({ incident }: EvidenceLedgerProps) {
  const activeHypothesis = incident.hypotheses.find((h) => h.rank === 1);
  const evidenceItems = activeHypothesis?.evidence || [];

  const confirmed = evidenceItems.filter((item) => item.kind === "confirmed");
  const correlated = evidenceItems.filter((item) => item.kind === "correlated");
  const missing = evidenceItems.filter((item) => item.kind === "missing");

  return (
    <div className="w-full font-mono select-none">
      <div className="text-[10px] tracking-[0.15em] font-bold text-grey-muted mb-3 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span>EVIDENCE_LEDGER // HYPOTHESIS_RANK_1</span>
        <span>COUNT: {evidenceItems.length}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Confirmed Column */}
        <div className="border border-border-muted bg-panel-raised p-3 flex flex-col gap-2 rounded-lg">
          <div className="text-xs font-bold text-confirmed border-b border-confirmed/10 pb-1.5 flex justify-between items-center">
            <span>[CONFIRMED]</span>
            <span className="text-[10px] text-grey-muted">{confirmed.length} ITEMS</span>
          </div>
          <div className="flex flex-col gap-3 mt-1 overflow-y-auto max-h-[250px]">
            {confirmed.length === 0 ? (
              <span className="text-xs text-grey-muted italic">No confirmed evidence.</span>
            ) : (
              confirmed.map((item, idx) => (
                <div key={idx} className="text-[12px] leading-relaxed border-l-2 border-confirmed pl-2">
                  <div className="text-white-signal">{item.statement}</div>
                  <div className="text-[10px] text-grey-muted mt-1">
                    SOURCE: {item.source.toUpperCase()} {item.ref && `// REF: ${item.ref}`}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Correlated Column */}
        <div className="border border-border-muted bg-panel-raised p-3 flex flex-col gap-2 rounded-lg">
          <div className="text-xs font-bold text-correlated border-b border-correlated/10 pb-1.5 flex justify-between items-center">
            <span>[CORRELATED]</span>
            <span className="text-[10px] text-grey-muted">{correlated.length} ITEMS</span>
          </div>
          <div className="flex flex-col gap-3 mt-1 overflow-y-auto max-h-[250px]">
            {correlated.length === 0 ? (
              <span className="text-xs text-grey-muted italic">No correlated evidence.</span>
            ) : (
              correlated.map((item, idx) => (
                <div key={idx} className="text-[12px] leading-relaxed border-l-2 border-correlated pl-2">
                  <div className="text-white-signal">{item.statement}</div>
                  <div className="text-[10px] text-grey-muted mt-1">
                    SOURCE: {item.source.toUpperCase()} {item.ref && `// REF: ${item.ref}`}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Missing Column */}
        <div className="border border-border-muted bg-panel-raised p-3 flex flex-col gap-2 rounded-lg">
          <div className="text-xs font-bold text-grey-muted border-b border-border-muted pb-1.5 flex justify-between items-center">
            <span>[MISSING]</span>
            <span className="text-[10px] text-grey-muted">{missing.length} ITEMS</span>
          </div>
          <div className="flex flex-col gap-3 mt-1 overflow-y-auto max-h-[250px]">
            {missing.length === 0 ? (
              <span className="text-xs text-grey-muted italic">No missing evidence.</span>
            ) : (
              missing.map((item, idx) => (
                <div key={idx} className="text-[12px] leading-relaxed border-l-2 border-border-muted pl-2">
                  <div className="text-grey-muted">{item.statement}</div>
                  <div className="text-[10px] text-grey-muted/60 mt-1">
                    SOURCE: {item.source.toUpperCase()} {item.ref && `// REF: ${item.ref}`}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
