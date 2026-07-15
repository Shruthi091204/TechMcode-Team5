"use client";

import React, { useState } from "react";

interface FaultInjectorProps {
  onInject?: (scenario: string) => void;
}

export default function FaultInjector({ onInject = (s) => console.log(`Injecting: ${s}`) }: FaultInjectorProps) {
  const [injecting, setInjecting] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);

  const scenarios = [
    { id: "fiber_cut", label: "FIBER CUT" },
    { id: "bad_config", label: "BAD CONFIG" },
    { id: "ddos", label: "DDOS ATTACK" },
    { id: "db_exhaustion", label: "DB POOL EXHAUSTION" },
    { id: "nic_failure", label: "NIC FAILURE" },
    { id: "port_scan", label: "PORT SCAN" },
  ];

  const handleInject = (scenarioId: string, label: string) => {
    if (injecting) return;
    setInjecting(label);
    
    setTimeout(() => {
      onInject(scenarioId);
      setActiveScenario(label);
      setInjecting(null);
    }, 1500);
  };

  return (
    <div className="w-full bg-panel border border-border-muted/20 p-4 font-mono select-none">
      <div className="text-xs text-text-muted mb-3 flex items-center justify-between border-b border-border-muted/10 pb-2">
        <span>DEMO_CONTROL_CENTER // FAULT_INJECTION_PANEL</span>
        {activeScenario ? (
          <span className="text-primary animate-pulse text-[10px] font-bold">
            ACTIVE_FAULT: {activeScenario}
          </span>
        ) : (
          <span className="text-text-muted text-[10px]">SYSTEM_STANDBY</span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        {scenarios.map((sc) => {
          const isCurrentInjecting = injecting === sc.label;
          const isActive = activeScenario === sc.label;

          return (
            <button
              key={sc.id}
              disabled={!!injecting}
              onClick={() => handleInject(sc.id, sc.label)}
              className={`text-xs py-2 px-1 border transition-colors duration-150 relative overflow-hidden flex flex-col items-center justify-center min-h-[50px] rounded-none ${
                isCurrentInjecting
                  ? "border-primary text-primary bg-primary/5 cursor-wait"
                  : isActive
                  ? "border-primary text-primary bg-primary/10"
                  : "border-border-muted/20 text-foreground hover:border-border-muted/50 bg-background/20"
              }`}
            >
              {isCurrentInjecting ? (
                <>
                  <span className="text-[9px] uppercase tracking-wider text-primary animate-pulse">
                    INJECTING...
                  </span>
                  <div className="absolute bottom-0 left-0 h-[2px] bg-primary animate-[pulse_1.5s_infinite] w-full" />
                </>
              ) : (
                <>
                  <span className="font-bold text-center">{sc.label}</span>
                  {isActive && (
                    <span className="text-[8px] text-primary mt-1 font-mono uppercase tracking-tight">
                      [TRIGGERED]
                    </span>
                  )}
                </>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
