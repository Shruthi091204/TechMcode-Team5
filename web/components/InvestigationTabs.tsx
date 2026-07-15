"use client";

import React, { useState } from "react";
import { AnimatePresence, motion as m } from "framer-motion";
import { Sparkles, ClipboardList, Zap, Play, ChevronDown, ChevronUp } from "lucide-react";
import { IncidentReport, TimelineEvent } from "../lib/types";
import CounterfactualPanel from "./CounterfactualPanel";
import SkepticTranscript from "./SkepticTranscript";

interface InvestigationTabsProps {
  incident: IncidentReport;
  activeHypothesis: any;
  timelineFilterIndex: number;
  setTimelineFilterIndex: (index: number) => void;
}

export default function InvestigationTabs({
  incident,
  activeHypothesis,
  timelineFilterIndex,
  setTimelineFilterIndex,
}: InvestigationTabsProps) {
  const [expandedBox, setExpandedBox] = useState<"investigation" | "evidence" | "timeline" | "actions" | null>(null);

  const evidenceItems = activeHypothesis?.evidence || [];
  const confirmed = evidenceItems.filter((item: any) => item.kind === "confirmed");
  const correlated = evidenceItems.filter((item: any) => item.kind === "correlated");
  const missing = evidenceItems.filter((item: any) => item.kind === "missing");

  // Chat Transcript logic for AI Investigation
  const skepticVerdict = activeHypothesis?.skeptic_verdict || "No skeptic analysis available.";
  const transcript = [
    {
      speaker: "Investigator AI",
      message: `Root Cause Analysis indicates ${activeHypothesis?.root_cause_component} underwent a critical fault: ${activeHypothesis?.fault_type}. Deployment config audit confirms max_connections changed.`,
      time: "09:28:15",
      isSkeptic: false,
    },
    {
      speaker: "Skeptic Bot",
      message: skepticVerdict,
      time: "09:29:02",
      isSkeptic: true,
    },
    {
      speaker: "Investigator AI",
      message: "Acknowledged. However, the telemetry timeline places the database connection pool saturation exactly 25 seconds before the packet retransmissions began on tor-03, pointing to downstream queue backlog rather than line corruption.",
      time: "09:29:45",
      isSkeptic: false,
    },
  ];

  const boxes = [
    {
      id: "investigation" as const,
      label: "AI INVESTIGATION",
      summary: "Narrative & reviews logged",
      icon: Sparkles,
    },
    {
      id: "evidence" as const,
      label: "EVIDENCE LEDGER",
      summary: `${evidenceItems.length} items verified`,
      icon: ClipboardList,
    },
    {
      id: "timeline" as const,
      label: "INCIDENT TIMELINE",
      summary: `${incident.timeline.length} events mapped`,
      icon: Zap,
    },
    {
      id: "actions" as const,
      label: "RECOMMENDED ACTIONS",
      summary: `${incident.recommended_steps.length} mitigation tasks`,
      icon: Play,
    },
  ];

  return (
    <div className="flex flex-col gap-6 w-full mt-4">
      {/* 4-Column Card Grid (Collapsed states) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
        {boxes.map((box) => {
          const isExpanded = expandedBox === box.id;
          const Icon = box.icon;
          
          return (
            <m.button
              key={box.id}
              onClick={() => setExpandedBox(isExpanded ? null : box.id)}
              whileHover={{ 
                scale: 1.02, 
                boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                backgroundColor: "#1F1F24"
              }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              className={`bg-[#16161A] border rounded-xl p-5 text-left transition-all duration-300 flex items-center justify-between shadow-soft select-none ${
                isExpanded ? "border-[#E50914] state-active-glow" : "border-[#2A2A2E]/50"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${isExpanded ? "bg-[#E50914]/20 text-[#E50914]" : "bg-[#1F1F24] text-[#A3A3A8]"}`}>
                  <Icon size={18} />
                </div>
                <div>
                  <div className="text-[11px] tracking-[0.08em] font-semibold text-[#A3A3A8] uppercase">
                    {box.label}
                  </div>
                  <div className="text-xs text-[#6B6B70] mt-0.5 font-medium">
                    {box.summary}
                  </div>
                </div>
              </div>
              {isExpanded ? <ChevronUp size={16} className="text-[#E50914]" /> : <ChevronDown size={16} className="text-[#A3A3A8]" />}
            </m.button>
          );
        })}
      </div>

      {/* Accordion Expanded Content Panel */}
      <AnimatePresence initial={false}>
        {expandedBox && (
          <m.div
            key={expandedBox}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="bg-[#16161A] border border-[#2A2A2E] rounded-xl overflow-hidden shadow-lifted"
          >
            <div className="p-6">
              {/* AI INVESTIGATION PANEL */}
              {expandedBox === "investigation" && (
                <div className="flex flex-col gap-6">
                  <div>
                    <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8] mb-3">AI GENERATED NARRATIVE</h3>
                    <div className="text-sm leading-relaxed text-[#A3A3A8] bg-[#1F1F24] p-5 border border-[#2A2A2E] rounded-xl shadow-soft">
                      {incident.narrative}
                    </div>
                  </div>

                  <div className="border-t border-[#2A2A2E]/50 pt-5">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8] mb-4">CRITICAL VALIDATION TRANSCRIPT</h3>
                    <div className="flex flex-col gap-4 max-h-[300px] overflow-y-auto pr-2">
                      {transcript.map((chat, idx) => (
                        <div 
                          key={idx} 
                          className={`flex flex-col max-w-[80%] p-4 rounded-xl border ${
                            chat.isSkeptic 
                              ? "self-end bg-[#FFA53B]/5 border-[#FFA53B]/20 text-white" 
                              : "self-start bg-[#1F1F24] border-[#2A2A2E] text-white"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-6 text-[9px] text-[#6B6B70] font-bold tracking-wider uppercase mb-1">
                            <span className={chat.isSkeptic ? "text-[#FFA53B]" : "text-white"}>{chat.speaker}</span>
                            <span>{chat.time}</span>
                          </div>
                          <p className="text-xs leading-relaxed text-[#A3A3A8]">{chat.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* EVIDENCE LEDGER PANEL */}
              {expandedBox === "evidence" && (
                <div>
                  <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8] mb-4">VERIFIED EVIDENCE LEDGER</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Confirmed Column */}
                    <div className="bg-[#1F1F24] border border-[#2A2A2E] rounded-xl overflow-hidden shadow-soft flex flex-col">
                      <div className="px-4 py-3 bg-[#1F1F24] border-b border-[#2A2A2E] flex justify-between items-center">
                        <span className="text-xs font-bold text-[#2ECC71]">CONFIRMED</span>
                        <span className="text-[10px] text-[#6B6B70] font-bold">{confirmed.length} ITEMS</span>
                      </div>
                      <div className="p-4 flex flex-col gap-3 max-h-[250px] overflow-y-auto">
                        {confirmed.length === 0 ? (
                          <span className="text-xs text-[#6B6B70] italic">No confirmed evidence.</span>
                        ) : (
                          confirmed.map((item: any, idx: number) => (
                            <div key={idx} className="text-xs border-l-2 border-[#2ECC71] pl-3 py-1">
                              <div className="text-white font-medium">{item.statement}</div>
                              <div className="text-[9px] text-[#6B6B70] mt-1 font-semibold uppercase">
                                SOURCE: {item.source} {item.ref && `| REF: ${item.ref}`}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Correlated Column */}
                    <div className="bg-[#1F1F24] border border-[#2A2A2E] rounded-xl overflow-hidden shadow-soft flex flex-col">
                      <div className="px-4 py-3 bg-[#1F1F24] border-b border-[#2A2A2E] flex justify-between items-center">
                        <span className="text-xs font-bold text-[#FFA53B]">CORRELATED</span>
                        <span className="text-[10px] text-[#6B6B70] font-bold">{correlated.length} ITEMS</span>
                      </div>
                      <div className="p-4 flex flex-col gap-3 max-h-[250px] overflow-y-auto">
                        {correlated.length === 0 ? (
                          <span className="text-xs text-[#6B6B70] italic">No correlated evidence.</span>
                        ) : (
                          correlated.map((item: any, idx: number) => (
                            <div key={idx} className="text-xs border-l-2 border-[#FFA53B] pl-3 py-1">
                              <div className="text-white font-medium">{item.statement}</div>
                              <div className="text-[9px] text-[#6B6B70] mt-1 font-semibold uppercase">
                                SOURCE: {item.source} {item.ref && `| REF: ${item.ref}`}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Missing Column */}
                    <div className="bg-[#1F1F24] border border-[#2A2A2E] rounded-xl overflow-hidden shadow-soft flex flex-col">
                      <div className="px-4 py-3 bg-[#1F1F24] border-b border-[#2A2A2E] flex justify-between items-center">
                        <span className="text-xs font-bold text-[#6B6B70]">MISSING</span>
                        <span className="text-[10px] text-[#6B6B70] font-bold">{missing.length} ITEMS</span>
                      </div>
                      <div className="p-4 flex flex-col gap-3 max-h-[250px] overflow-y-auto">
                        {missing.length === 0 ? (
                          <span className="text-xs text-[#6B6B70] italic">No missing evidence.</span>
                        ) : (
                          missing.map((item: any, idx: number) => (
                            <div key={idx} className="text-xs border-l-2 border-[#2A2A2E] pl-3 py-1">
                              <div className="text-[#A3A3A8]">{item.statement}</div>
                              <div className="text-[9px] text-[#6B6B70]/60 mt-1 font-semibold uppercase">
                                SOURCE: {item.source}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* INCIDENT TIMELINE PANEL (Scrubbable Timeline) */}
              {expandedBox === "timeline" && (
                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8]">INCIDENT EVENT TIMELINE</h3>
                    <span className="text-xs text-[#E50914] font-bold">
                      Scrubbing: showing {timelineFilterIndex + 1} of {incident.timeline.length} events
                    </span>
                  </div>

                  {/* Scrub Slider Container */}
                  <div className="bg-[#1F1F24] p-5 rounded-xl border border-[#2A2A2E] shadow-soft mb-6 flex flex-col gap-4">
                    <input 
                      type="range"
                      min={0}
                      max={incident.timeline.length - 1}
                      value={timelineFilterIndex}
                      onChange={(e) => setTimelineFilterIndex(Number(e.target.value))}
                      className="w-full accent-[#E50914] bg-[#16161A] h-1.5 rounded-lg appearance-none cursor-pointer"
                    />
                    
                    {/* Visual Markers Row */}
                    <div className="relative w-full h-3 flex items-center justify-between px-1">
                      {incident.timeline.map((event, idx) => {
                        const isTriggered = idx <= timelineFilterIndex;
                        const eventColor = event.kind === "config" 
                          ? "bg-[#FFA53B]" 
                          : event.kind === "alert" || event.kind === "anomaly" 
                            ? "bg-[#E50914]" 
                            : "bg-[#2ECC71]";
                        
                        return (
                          <div 
                            key={idx} 
                            className={`w-2 h-2 rounded-full transition-all ${
                              isTriggered ? `${eventColor} scale-125` : "bg-[#2A2A2E]"
                            }`}
                            title={`[${event.ts}] ${event.component_id}: ${event.description}`}
                          />
                        );
                      })}
                    </div>
                  </div>

                  {/* Horizontal Scrollable Timeline Stream */}
                  <div className="flex gap-4 overflow-x-auto pb-4 pt-1">
                    {incident.timeline.slice(0, timelineFilterIndex + 1).map((event, idx) => {
                      const color = event.kind === "config" 
                        ? "border-[#FFA53B]" 
                        : event.kind === "alert" || event.kind === "anomaly" 
                          ? "border-[#E50914]" 
                          : "border-[#2A2A2E]";
                          
                      return (
                        <m.div
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          key={idx}
                          className={`bg-[#1F1F24] border ${color} rounded-lg p-3 shrink-0 w-[240px] flex flex-col justify-between`}
                        >
                          <div className="flex justify-between items-center text-[9px] text-[#6B6B70] font-bold uppercase tracking-wider">
                            <span>{event.component_id}</span>
                            <span>{event.ts}</span>
                          </div>
                          <div className="text-white text-xs font-semibold mt-1.5 line-clamp-2">
                            {event.description}
                          </div>
                        </m.div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* RECOMMENDED ACTIONS PANEL */}
              {expandedBox === "actions" && (
                <div>
                  <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8] mb-4">MITIGATION ROADMAP</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {incident.recommended_steps.map((step, idx) => (
                      <div key={idx} className="bg-[#1F1F24] border border-[#2A2A2E] p-4 rounded-lg flex items-start gap-4 shadow-soft">
                        <span className="text-[11px] px-2 py-0.5 border border-[#E50914]/40 text-[#E50914] font-bold rounded bg-[#E50914]/5 select-none shrink-0 mt-0.5">
                          {(idx + 1).toString().padStart(2, "0")}
                        </span>
                        <span className="text-xs text-[#A3A3A8] leading-relaxed font-sans font-medium">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}
