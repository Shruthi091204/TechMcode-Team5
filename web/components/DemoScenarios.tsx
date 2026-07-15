"use client";

import React from "react";
import {
  Scissors,
  Settings,
  ShieldAlert,
  Database,
  WifiOff,
  Radar,
  CheckCircle2,
  Hourglass
} from "lucide-react";

interface DemoScenariosProps {
  onReplay: (scenarioId: string, label: string) => void;
  activeScenario: string | null;
  isAnalyzing: boolean;
  analysisStep: number;
  elapsedTime: number;
}

export default function DemoScenarios({
  onReplay,
  activeScenario,
  isAnalyzing,
  analysisStep,
  elapsedTime
}: DemoScenariosProps) {
  const scenarios = [
    { id: "fiber_cut", label: "Fiber Cut", icon: Scissors },
    { id: "bad_config", label: "Bad Configuration", icon: Settings },
    { id: "ddos", label: "DDoS Attack", icon: ShieldAlert },
    { id: "db_exhaustion", label: "Database Pool Exhaustion", icon: Database },
    { id: "nic_failure", label: "NIC Failure", icon: WifiOff },
    { id: "port_scan", label: "Port Scan", icon: Radar },
  ];

  return (
    <div className="w-full bg-panel/30 backdrop-blur-md border border-border-muted/15 p-5 rounded-xl font-sans select-none transition-all duration-300">
      <div className="text-xs font-mono text-text-muted mb-4 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span className="font-bold tracking-wider">DEMO_CONTROL_CENTER // INCIDENT_REPLAY_SUITE</span>
        {isAnalyzing ? (
          <span className="text-primary animate-pulse flex items-center gap-1 font-bold">
            <Hourglass size={12} className="animate-spin" />
            ANALYZING SCENARIO: {activeScenario}
          </span>
        ) : activeScenario ? (
          <span className="text-confirmed flex items-center gap-1 font-bold">
            <CheckCircle2 size={12} />
            ANALYSIS COMPLETE: {activeScenario}
          </span>
        ) : (
          <span className="text-text-muted">SYSTEM_STANDBY</span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        {scenarios.map((sc) => {
          const Icon = sc.icon;
          const isSelected = activeScenario === sc.label;
          const isCurrentAnalyzing = isAnalyzing && isSelected;

          return (
            <button
              key={sc.id}
              disabled={isAnalyzing}
              onClick={() => onReplay(sc.id, sc.label)}
              className={`py-3 px-2 border rounded-lg transition-all duration-300 flex flex-col items-center justify-center gap-2 group relative overflow-hidden min-h-[85px] ${
                isCurrentAnalyzing
                  ? "state-active-glow text-red-critical bg-panel-raised"
                  : isSelected && !isAnalyzing
                  ? "border-confirmed bg-confirmed/10 text-confirmed"
                  : "border-border-muted text-foreground hover:state-active-glow hover:bg-panel-raised hover:scale-[1.03]"
              } ${isAnalyzing && !isSelected ? "opacity-30 cursor-not-allowed" : ""}`}
            >
              <Icon
                size={20}
                className={`transition-transform duration-300 ${
                  isCurrentAnalyzing ? "animate-pulse" : "group-hover:scale-110"
                } ${isSelected && !isAnalyzing ? "text-confirmed" : isCurrentAnalyzing ? "text-red-critical" : "text-grey-muted group-hover:text-red-critical"}`}
              />
              <span className="text-[11px] font-bold text-center leading-tight tracking-wide font-mono">
                {sc.label}
              </span>
              {isCurrentAnalyzing && (
                <div className="absolute bottom-0 left-0 h-[3px] bg-primary animate-[pulse_1s_infinite] w-full" />
              )}
            </button>
          );
        })}
      </div>

      {isAnalyzing && (
        <div className="mt-4 flex items-center justify-between bg-background/40 border border-primary/20 p-3 rounded-lg animate-[pulse_2s_infinite]">
          <span className="text-xs font-mono text-primary flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 bg-primary rounded-full animate-ping"></span>
            Analyzing Incident... (Step {analysisStep}/10)
          </span>
          <span className="text-xs font-mono text-text-muted">
            Elapsed time: {elapsedTime.toFixed(1)}s
          </span>
        </div>
      )}
    </div>
  );
}
