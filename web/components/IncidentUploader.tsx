"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { UploadCloud, FlaskConical, Loader2, AlertCircle, Sparkles } from "lucide-react";
import { analyzeIncident } from "../lib/api";
import { IncidentReport } from "../lib/types";

interface UploadPayload {
  topology?: { components?: unknown[]; dependencies?: unknown[] };
  telemetry?: unknown[];
  [key: string]: unknown;
}

export default function IncidentUploader() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [enriched, setEnriched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const runAnalysis = async (payload: UploadPayload, label: string) => {
    setBusy(true);
    setError(null);
    setStatus(enriched ? `${label} — running full AI investigation (~40s)…` : `${label} — analyzing…`);
    try {
      const result = await analyzeIncident(payload, !enriched);
      if ("status" in result && result.status === "healthy") {
        const healthyTopo = payload.topology ?? { components: [], dependencies: [] };
        sessionStorage.setItem(
          "healthy:latest",
          JSON.stringify({
            result,
            topology: { components: healthyTopo.components ?? [], dependencies: healthyTopo.dependencies ?? [] },
          }),
        );
        router.push("/healthy");
        return;
      }
      const report = result as IncidentReport;
      const topo = payload.topology ?? { components: [], dependencies: [] };
      sessionStorage.setItem(
        `analyzed:${report.incident_id}`,
        JSON.stringify({
          report,
          topology: { components: topo.components ?? [], dependencies: topo.dependencies ?? [] },
          telemetry: payload.telemetry ?? [],
        }),
      );
      router.push(`/incident/${report.incident_id}`);
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : "Analysis failed");
      setBusy(false);
      setStatus(null);
    }
  };

  const analyzePasted = () => {
    let payload: UploadPayload;
    try {
      payload = JSON.parse(text);
    } catch {
      setError("That isn't valid JSON — compare it against the sample format.");
      return;
    }
    if (!payload.topology || !payload.telemetry) {
      setError("Your incident needs at least a 'topology' and 'telemetry'.");
      return;
    }
    runAnalysis(payload, "Uploaded incident");
  };

  const analyzeSample = async () => {
    setBusy(true);
    setError(null);
    setStatus("Loading sample incident…");
    try {
      const response = await fetch("/sample_incident.json");
      const payload: UploadPayload = await response.json();
      await runAnalysis(payload, "Sample incident");
    } catch {
      setError("Could not load the sample dataset.");
      setBusy(false);
      setStatus(null);
    }
  };

  const onFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result ?? ""));
    reader.readAsText(file);
  };

  return (
    <div className="w-full bg-[#16161A] border border-[#2A2A2E] rounded-2xl p-6 shadow-soft flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white text-sm font-bold uppercase tracking-wider">Analyze Your Own Incident</h3>
          <p className="text-[#6B6B70] text-[11px] mt-1">
            Upload a topology + telemetry bundle, or try the bundled sample.
          </p>
        </div>
        <UploadCloud size={20} className="text-[#A3A3A8]" />
      </div>

      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        disabled={busy}
        placeholder='Paste an incident bundle:  { "topology": {…}, "telemetry": [...], "logs": [...], "alerts": [...], "config_changes": [...] }'
        className="w-full h-28 bg-[#0E0E10] border border-[#2A2A2E] rounded-lg p-3 text-[11px] text-[#D4D4D8] font-mono resize-none focus:outline-none focus:border-[#E50914]/50"
      />

      <div className="flex flex-wrap items-center gap-3">
        <input ref={fileRef} type="file" accept="application/json,.json" onChange={onFile} className="hidden" />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="px-3 py-2 text-[11px] font-bold text-[#A3A3A8] border border-[#2A2A2E] rounded-lg hover:border-[#3A3A3E] transition-colors disabled:opacity-40"
        >
          Choose JSON file…
        </button>

        <label className="flex items-center gap-2 text-[11px] text-[#A3A3A8] cursor-pointer select-none ml-auto">
          <input
            type="checkbox"
            checked={enriched}
            onChange={(event) => setEnriched(event.target.checked)}
            disabled={busy}
            className="accent-[#E50914]"
          />
          <Sparkles size={13} className="text-[#FFA53B]" />
          Full AI investigation (~40s)
        </label>
      </div>

      <div className="flex items-center gap-3">
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={analyzePasted}
          disabled={busy || !text.trim()}
          className="flex-1 bg-[#E50914] hover:bg-[#b8070f] disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors"
        >
          {busy ? <Loader2 size={14} className="animate-spin" /> : null}
          Analyze Incident
        </motion.button>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={analyzeSample}
          disabled={busy}
          className="px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider border border-[#2A2A2E] text-[#A3A3A8] hover:border-[#3A3A3E] disabled:opacity-40 flex items-center gap-2 transition-colors"
        >
          <FlaskConical size={14} className="text-[#2ECC71]" />
          Try Sample
        </motion.button>
      </div>

      {status ? (
        <div className="flex items-center gap-2 text-[11px] text-[#6B95E5]">
          <Loader2 size={12} className="animate-spin" />
          {status}
        </div>
      ) : null}
      {error ? (
        <div className="flex items-center gap-2 text-[11px] text-[#E50914]">
          <AlertCircle size={12} />
          {error}
        </div>
      ) : null}
    </div>
  );
}
