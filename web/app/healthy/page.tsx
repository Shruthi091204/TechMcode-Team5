"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ShieldCheck, ArrowLeft, Activity, Layers, CheckCircle2, Gauge } from "lucide-react";
import TopologyGraph from "../../components/TopologyGraph";
import { Component, Dependency } from "../../lib/types";
import { HealthyResult } from "../../lib/api";

interface HealthyState {
  result: HealthyResult;
  topology: { components: Component[]; dependencies: Dependency[] };
}

export default function HealthyPage() {
  const [state, setState] = useState<HealthyState | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const raw = typeof window !== "undefined" ? sessionStorage.getItem("healthy:latest") : null;
    if (raw) {
      try {
        setState(JSON.parse(raw));
      } catch {
        // ignore corrupt cache
      }
    }
    setLoaded(true);
  }, []);

  if (loaded && !state) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-white">
        <p className="text-[#A3A3A8] text-sm">No health report loaded — upload a dataset first.</p>
        <Link href="/" className="text-[#2ECC71] text-sm font-bold uppercase tracking-wider">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  if (!state) return null;

  const { result, topology } = state;

  const stats = [
    { label: "Components Monitored", value: result.components_analyzed, icon: Layers },
    { label: "Telemetry Windows", value: result.telemetry_windows, icon: Activity },
    { label: "Anomalies Detected", value: 0, icon: ShieldCheck },
    { label: "Metrics Evaluated", value: result.metrics_evaluated.length, icon: Gauge },
  ];

  const checks = [
    `${result.components_analyzed} components scanned across every tier`,
    `${result.telemetry_windows} telemetry windows analyzed with MAD baseline + PELT change-point detection`,
    "0 change-points detected — no metric departed from its established baseline",
    "0 threshold breaches and 0 configuration changes correlated with degradation",
    `All KPIs within baseline: ${result.metrics_evaluated.join(", ")}`,
  ];

  return (
    <div className="min-h-screen bg-transparent text-white p-8 flex flex-col gap-8 max-w-6xl mx-auto">
      <Link
        href="/"
        className="flex items-center gap-2 text-[#A3A3A8] hover:text-white text-xs font-bold uppercase tracking-wider w-fit"
      >
        <ArrowLeft size={14} /> Dashboard
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="bg-[#2ECC71]/10 border border-[#2ECC71]/30 rounded-2xl p-8 flex items-center gap-5 shadow-[0_0_30px_rgba(46,204,113,0.12)]"
      >
        <div className="p-4 rounded-2xl bg-[#2ECC71]/20">
          <ShieldCheck size={40} className="text-[#2ECC71]" />
        </div>
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight">All Systems Nominal</h1>
          <p className="text-[#8FE3B0] mt-1">{result.message}</p>
        </div>
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-[#16161A] border border-[#2A2A2E] rounded-2xl p-6 flex flex-col gap-3">
              <Icon size={20} className="text-[#2ECC71]" />
              <div>
                <div className="text-3xl font-black text-white">{stat.value}</div>
                <div className="text-[11px] text-[#6B6B70] font-bold uppercase tracking-wider mt-1">{stat.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[#16161A] border border-[#2A2A2E] rounded-2xl overflow-hidden h-[440px]">
          <div className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8] px-5 pt-4 pb-2">
            Network Topology
          </div>
          <div className="h-[calc(100%-2.75rem)] px-1 pb-1">
            <TopologyGraph topology={topology} highlightActive={false} />
          </div>
        </div>

        <div className="bg-[#16161A] border border-[#2A2A2E] rounded-2xl p-6 flex flex-col gap-4">
          <h3 className="text-xs uppercase tracking-wider font-bold text-[#A3A3A8]">Why It Is Healthy</h3>
          <div className="flex flex-col gap-3.5">
            {checks.map((check, index) => (
              <div key={index} className="flex items-start gap-2.5 text-[13px] leading-relaxed text-[#D1D1D6]">
                <CheckCircle2 size={16} className="text-[#2ECC71] shrink-0 mt-0.5" />
                <span>{check}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
