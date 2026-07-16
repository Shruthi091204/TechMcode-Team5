"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Scissors, Settings, Shield, Database, WifiOff, Radar, Play, X, RotateCcw } from "lucide-react";
import { IncidentReport } from "../lib/types";

interface DemoLauncherProps {
  onScenarioLoaded: (incidentData: IncidentReport, scenarioLabel: string) => void;
  activeScenarioLabel: string | null;
  setActiveScenarioLabel: (label: string | null) => void;
}

const DEMO_SCENARIOS = [
  {
    id: "bad_config_push",
    label: "Bad Configuration",
    icon: Settings,
    description: "Deployment configuration change reduces active db connections limit",
    available: true,
  },
  {
    id: "link_degradation",
    label: "Fiber Cut",
    icon: Scissors,
    description: "Physical core transport line disruption degrades network path",
    available: false,
  },
  {
    id: "ddos_flood",
    label: "DDoS Attack",
    icon: Shield,
    description: "High rate load-balancer packets flood exhausts socket capacity",
    available: true,
  },
  {
    id: "capacity_exhaustion",
    label: "Database Pool Exhaustion",
    icon: Database,
    description: "Connection pool exhaustion triggers application tier starvation",
    available: false,
  },
  {
    id: "nic_failure",
    label: "NIC Failure",
    icon: WifiOff,
    description: "Hardware network interface controller drops frames on switch port",
    available: false,
  },
  {
    id: "port_scan",
    label: "Port Scan",
    icon: Radar,
    description: "Automated network host sweep attempts scans for active open ports",
    available: false,
  },
];

export default function DemoLauncher({
  onScenarioLoaded,
  activeScenarioLabel,
  setActiveScenarioLabel,
}: DemoLauncherProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [loadingScenarioId, setLoadingScenarioId] = useState<string | null>(null);
  const [errorScenarioId, setErrorScenarioId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleRunInvestigation = async (scenarioId: string, label: string) => {
    setLoadingScenarioId(scenarioId);
    setErrorScenarioId(null);
    setErrorMessage(null);

    try {
      const res = await fetch(`/api/replay/${scenarioId}`, {
        method: "POST",
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Scenario not available");
      }

      const incidentData: IncidentReport = await res.json();
      
      // Update incident state in parent
      onScenarioLoaded(incidentData, label);
      setActiveScenarioLabel(label);
      
      // Collapse launcher back to compact play pill state
      setIsExpanded(false);
    } catch (err: any) {
      setErrorScenarioId(scenarioId);
      setErrorMessage(err.message || "Not available yet");
    } finally {
      setLoadingScenarioId(null);
    }
  };

  const containerVariants = {
    hidden: {},
    show: {
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  };

  return (
    <div className="w-full flex flex-col items-center gap-4 select-none">
      {/* State 1 / Active Header Banner Indicator */}
      <div className="w-full flex justify-between items-center bg-[#16161A]/40 px-4 py-2 rounded-lg border border-[#2A2A2E]/30">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#6B6B70] font-bold uppercase tracking-wider">
            DEMO PANEL:
          </span>
          <span className="text-xs text-white font-bold">
            {activeScenarioLabel ? `Viewing: ${activeScenarioLabel}` : "Viewing: Default Incident (Bad Configuration)"}
          </span>
        </div>
        
        {isExpanded ? (
          <button
            onClick={() => setIsExpanded(false)}
            className="text-xs font-bold text-[#E50914] hover:underline flex items-center gap-1 cursor-pointer transition-colors"
          >
            Collapse Launcher
          </button>
        ) : (
          <motion.button
            onClick={() => setIsExpanded(true)}
            whileHover={{ scale: 1.05 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="px-4 py-1.5 bg-[#E50914] hover:bg-[#b8070f] text-white text-[10px] font-bold rounded-md flex items-center gap-1.5 shadow-[0_0_10px_rgba(229,9,20,0.3)] uppercase tracking-wider cursor-pointer"
          >
            <Play size={10} fill="white" />
            <span>Launch Demo</span>
          </motion.button>
        )}
      </div>

      {/* State 2 & 3: Expanded Grid */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="w-full bg-[#16161A] border border-[#2A2A2E] rounded-xl p-6 shadow-lifted overflow-hidden mt-2"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8]">
                Select Investigation Scenario
              </h3>
              <button
                onClick={() => setIsExpanded(false)}
                className="text-[#6B6B70] hover:text-white p-1 hover:bg-[#1F1F24] rounded-full transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6"
            >
              {DEMO_SCENARIOS.map((sc) => {
                const Icon = sc.icon;
                const isAvailable = sc.available;
                const isLoading = loadingScenarioId === sc.id;
                const isError = errorScenarioId === sc.id;
                const isAnyLoading = loadingScenarioId !== null;
                const isSelected = loadingScenarioId === sc.id;
                const isDisabled = isAnyLoading || !isAvailable;

                return (
                  <motion.div
                    key={sc.id}
                    variants={cardVariants}
                    whileHover={!isDisabled ? { scale: 1.02, backgroundColor: "#1F1F24" } : {}}
                    className={`p-5 rounded-xl bg-[#16161A] border border-[#2A2A2E]/50 shadow-soft transition-opacity flex flex-col justify-between min-h-[140px] relative overflow-hidden ${
                      !isAvailable ? "opacity-40" : isAnyLoading && !isSelected ? "opacity-30" : "opacity-100"
                    } ${isSelected ? "border-[#E50914] state-active-glow" : ""}`}
                    style={{ cursor: isDisabled ? "not-allowed" : "pointer" }}
                    onClick={() => !isDisabled && handleRunInvestigation(sc.id, sc.label)}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Icon
                          size={20}
                          className={`${
                            isLoading ? "text-[#E50914] animate-pulse" : "text-[#A3A3A8]"
                          }`}
                        />
                        {!isAvailable && !isError && (
                          <span className="text-[9px] bg-[#2A2A2E] text-[#8A8A90] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                            Soon
                          </span>
                        )}
                        {isError && (
                          <span className="text-[9px] bg-[#E50914]/20 text-[#E50914] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                            Not available yet
                          </span>
                        )}
                      </div>
                      <h4 className="text-white text-xs font-bold uppercase tracking-wide">
                        {sc.label}
                      </h4>
                      <p className="text-[#A3A3A8] text-[11px] mt-1 leading-relaxed">
                        {sc.description}
                      </p>
                    </div>

                    {/* Bottom Progress bar loading indicator on selected card */}
                    {isLoading && (
                      <div className="absolute bottom-0 left-0 w-full h-1 bg-[#1F1F24]">
                        <motion.div
                          initial={{ left: "-100%" }}
                          animate={{ left: "100%" }}
                          transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
                          className="absolute w-1/2 h-full bg-[#E50914]"
                        />
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
