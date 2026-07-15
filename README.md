# Network Anomaly Root-Cause Assistant

> Ingests network telemetry, logs, alerts, topology, and configuration changes; detects anomalies across time windows; and produces **ranked, evidence-backed root-cause hypotheses** — distinguishing genuine **causation from mere correlation** by constraining inference to the physical network topology.

Upload an incident (or your own dataset), and the system tells you **which component is the root cause**, **why** (with a three-tier evidence ledger), **how the fault propagated**, and **what to do next** — backed by a tamper-evident audit trail.

---

## Table of contents

1. [The problem](#the-problem)
2. [What makes it different](#what-makes-it-different)
3. [Key features](#key-features)
4. [Architecture](#architecture)
5. [How it works](#how-it-works)
6. [Tech stack](#tech-stack)
7. [Repository structure](#repository-structure)
8. [Running locally](#running-locally)
9. [Using the application](#using-the-application)
10. [Input data format](#input-data-format)
11. [API reference](#api-reference)
12. [Testing](#testing)
13. [Evaluation & accuracy](#evaluation--accuracy)
14. [Design decisions & FAQ](#design-decisions--faq)
15. [Known limitations & roadmap](#known-limitations--roadmap)
16. [Licence](#licence)

---

## The problem

A network operations centre receives **thousands of alerts an hour**. Most are *symptoms*, not causes. Engineers spend the majority of mean-time-to-resolution simply deciding *which* signal is the culprit and which are downstream noise.

Tools that correlate events by timestamp routinely **blame whichever component moved first** — which is frequently the *victim*, not the cause. A database that saturates its connection pool will make the web tier look broken; a naive tool blames the web tier. The engineer needs the *cause*: the database.

## What makes it different

**We separate causation from correlation using the network topology itself.** A component can only be proposed as a root cause if a **real dependency path exists** from it to the symptomatic component. Everything else — no matter how anomalous or how recently it changed — is demoted, and the *reason* it was demoted is shown to the user.

The system is deliberately split into two layers:

- **A deterministic core** that decides the root cause. Robust baselines + change-point detection find the *onset* of each anomaly; topology-constrained candidate filtering + causal attribution + counterfactual analysis rank the causes. **The same incident always produces the same ranking** — it is reproducible and explainable, not a black box.
- **A bounded reasoning (LLM) layer** that only does what language models are good at: writing the incident timeline, explaining findings in plain English, **adversarially reviewing** each hypothesis, and recommending diagnostic steps. **The LLM never selects the root cause**, and its influence on confidence is clamped so it can never override the deterministic ranking.

This is the "**vending machine over slot machine**" principle — determinism where correctness matters, AI where language matters.

## Key features

- **Topology-constrained causal ranking** — the moat. Impact paths, blast-radius, and DoWhy attribution over the real dependency graph.
- **Three-tier evidence ledger** — every hypothesis separates **confirmed evidence** (cited to a raw record), **correlated signals**, and **missing evidence** — and the missing evidence *is* the recommended-next-steps list.
- **Counterfactual replay** — "removing config change X restores web-02 to baseline."
- **Bounded, agentic AI** — skeptic (adversarial STORM verification), investigator (narrative + timeline), remediation (grounded diagnostic steps), each an OpenAI tool-calling agent.
- **Upload your own data** — analyze any contract-conforming incident bundle, not just canned demos.
- **Healthy-state detection** — upload a fault-free dataset and get an "All Systems Nominal" report explaining *why* it's healthy.
- **Tamper-evident audit trail** — every investigation step is written to a SHA-256 hash-chained log with a verification endpoint.
- **Deterministic + reproducible** — same input → same ranking, every run (verified in tests).
- **Two analysis modes** — instant deterministic report (no API key), or full LLM-enriched investigation.
- **Synthetic incident generator** — injects a *known* root cause into the topology to benchmark recovery accuracy honestly.

## Architecture

```
 Telemetry · Logs · Alerts · Topology · Config changes      (frozen data contract, Pydantic v2)
                          │
                          ▼
              Anomaly detection                MAD robust baseline + PELT change-point → onset times
                          │
                          ▼
     Topology-constrained causal engine        networkx impact paths · candidate filter ·
                          │                     DoWhy attribution · counterfactual replay
                          ▼
        Ranked hypotheses + evidence ledger     confirmed / correlated / missing
                          │
                          ▼
             Bounded LLM reasoning (OpenAI)      skeptic (STORM) · investigator · remediation
                          │                      — explains & verifies, never picks the cause
                          ▼
   Incident timeline · narrative · next steps        + SHA-256 hash-chained audit trail
                          │
                          ▼
                  FastAPI  ──►  Next.js NOC dashboard
```

Every layer is developed against a **frozen data contract** (`contracts/schemas.py`), which is why detection, causal inference, the agents, and the frontend could all be built in parallel and still fit together.

## How it works

1. **Ingest** — an incident is a bundle of contract-typed streams: a `topology` (components + dependency edges), `telemetry` (per-component metric windows), and optional `logs`, `alerts`, and `config_changes`.
2. **Detect** — a MAD (median-absolute-deviation) baseline over a pre-incident window plus PELT change-point detection flags anomalies and, crucially, their **onset time** (not just a threshold crossing).
3. **Constrain** — candidate root causes are filtered to anomalous components that have a **topology dependency path** to the symptom. Components with no path are rejected as decoys (and told to the user).
4. **Attribute & rank** — a weighted model combines topology-constrained causal attribution (DoWhy, with a deterministic fallback), config-change proximity, evidence strength, temporal precedence, "rootness" (how many other suspects a candidate explains), and severity. Severity is deliberately down-weighted so victims never outrank causes.
5. **Explain (optional AI)** — the skeptic agent adversarially tries to *disprove* the top hypotheses; the investigator writes the timeline + narrative; remediation converts the missing-evidence ledger into concrete diagnostic steps.
6. **Audit** — every step is appended to a hash-chained ledger that can be independently verified.

## Tech stack

| Layer | Choice |
|---|---|
| Data contract | Pydantic v2 (frozen models, exported JSON Schema) |
| Anomaly detection | NumPy / SciPy robust baselines, `ruptures` PELT change-point |
| Causal engine | `networkx` topology twin, DoWhy GCM attribution (deterministic fallback), seeded for reproducibility |
| Reasoning agents | OpenAI (structured outputs + native tool-calling), bounded confidence influence |
| API | FastAPI + Uvicorn |
| Frontend | Next.js 15, React 19, Cytoscape.js, Recharts, Tailwind, Framer Motion |
| Audit | SHA-256 hash-chained JSONL ledger |

## Repository structure

```
contracts/          frozen data contract: schemas.py, schemas.json, golden fixture + streams
src/rca/
  detect/           anomaly detection (baseline, change-point, windowing)
  graph/            networkx topology twin + impact-path / blast-radius queries
  causal/           candidate filter, attribution, counterfactual, evidence ledger, ranker
  agents/           OpenAI skeptic / investigator / remediation + the tool-calling runner
  synth/            synthetic incident generator (inject a known cause → benchmark recovery)
  audit/            SHA-256 hash-chained audit log + verifier
  api/              FastAPI routes (topology, incident, replay, analyze, audit)
eval/               accuracy benchmarks (synth_eval.py, run_eval.py)
web/                Next.js NOC dashboard (upload → analyze → report; healthy view)
tests/              contract + engine + detection + generator + upload suites (300+ tests)
Makefile            setup / lint / test / check targets
```

## Running locally

### Prerequisites

- **Python 3.11+**
- **Node 20+**
- An **OpenAI API key** — *only* needed for the "Full AI investigation" mode. The deterministic engine, the API, the upload flow, and the reference incident all run **without** it.

### 1. Backend

```bash
# from the repository root
make setup                              # create .venv and install Python dependencies
cp .env.example .env                    # then edit .env:  OPENAI_API_KEY=sk-...  OPENAI_MODEL=gpt-4.1

# start the API (http://localhost:8000)
PYTHONPATH=src .venv/bin/uvicorn rca.api.main:app --port 8000
```

Quick check: `curl -s localhost:8000/health` → `{"status":"ok"}`.

### 2. Frontend (in a second terminal)

```bash
cd web
npm install
npm run dev                             # http://localhost:3000
```

Open **http://localhost:3000**. The dashboard proxies `/api/*` to the backend on port 8000 (configured in `web/next.config.ts`), so both servers must be running for uploads to work.

> **Tip:** never run `npm run build` while `npm run dev` is live — it rewrites the `.next` cache and can cause "Cannot find module" errors. If that happens: `rm -rf web/.next && npm run dev`.

### One-command sanity check

```bash
make check                              # ruff lint + full test suite (300+ tests)
cd web && npx tsc --noEmit              # frontend type-check
```

## Using the application

From the landing page you can:

- **Launch the reference incident** — a fully worked example (`INC-1001`: a database connection-pool exhaustion propagating to the web tier) with the topology graph, ranked hypotheses, evidence ledger, timeline, and audit trail.
- **Analyze your own incident** — paste an incident bundle, upload a JSON file, or click **Try Sample** (loads `web/public/sample_incident.json`). The result renders in the same dashboard.
- **Toggle "Full AI investigation"** — off = an **instant deterministic** report (ranking, evidence, timeline, counterfactual); on = the full **LLM-enriched** investigation (adversarial skeptic verdicts + AI narrative + grounded remediation, ~40s, requires `OPENAI_API_KEY`).
- **Upload healthy data** — a fault-free bundle produces an **"All Systems Nominal"** dashboard: the all-green topology graph plus the exact checks that passed (windows analyzed, 0 change-points, all KPIs within baseline).

The topology graph colours the **root cause red**, the **impact path amber/yellow**, and **all healthy nodes green**. Clicking any node opens a detail panel with its real per-node telemetry peaks, alerts, logs, and config audits.

## Input data format

An incident bundle is JSON conforming to the frozen contract (`contracts/schemas.py`, exported to `contracts/schemas.json`):

```jsonc
{
  "topology": {
    "components":    [ { "component_id": "db-01", "component_type": "database", "tier": "data", "rack": "R1", "capacity_mbps": 1000 }, ... ],
    "dependencies":  [ { "source_id": "app-03", "target_id": "db-01", "relation": "DEPENDS_ON" }, ... ]
  },
  "telemetry":       [ { "component_id": "db-01", "window_start": "2026-...Z", "latency_ms": 22.0, "connection_count": 48, "cpu_pct": 32.0, ... }, ... ],
  "logs":            [ { "component_id": "db-01", "ts": "...", "severity": "ERROR", "template": "..." }, ... ],
  "alerts":          [ { "alert_id": "ALT-9001", "component_id": "web-02", "ts": "...", "severity": "CRITICAL", "metric": "latency_ms", "threshold": 100, "observed": 165 }, ... ],
  "config_changes":  [ { "change_id": "CHG-4212", "component_id": "db-01", "ts": "...", "change_type": "db_param_update", "before": {...}, "after": {...} }, ... ],
  "symptom_component": "web-02"          // optional; the engine infers it if omitted
}
```

**Minimum required:** `topology` + `telemetry`. Logs/alerts/config enrich the evidence ledger. **Topology is what unlocks causation** — without it the system can only do correlation-based detection. `web/public/sample_incident.json` is a complete, ready-to-upload example.

## API reference

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `GET /topology` | The reference topology (components + dependencies) |
| `GET /incidents/{id}` | The pre-computed reference incident report |
| `POST /analyze` | **Analyze an uploaded bundle** → full LLM report (add `?fast=true` for instant deterministic; returns a healthy result if no anomalies) |
| `POST /incidents/analyze` | Investigate pre-ranked hypotheses (LLM narrative only) |
| `POST /replay/{scenario}` | Replay the built-in reference scenario through the live pipeline |
| `GET /audit/verify` | Verify the SHA-256 audit chain integrity |

## Testing

```bash
make check                               # ruff (lint) + full pytest suite (300+ tests)
make lint                                # lint only
make test                                # tests only
.venv/bin/python -m pytest tests/ -q     # direct
cd web && npx tsc --noEmit               # frontend type-check
```

The suite covers the frozen contract invariants, the causal engine (ranking, determinism, decoy rejection), detection, the synthetic generator (recovery), and the upload path.

## Evaluation & accuracy

The honest, headline number comes from the **synthetic incident benchmark**: it injects a **known** root cause into the real topology (across all fault types and tiers) and measures whether the engine recovers it — the ground truth is *never* shown to the engine.

```bash
PYTHONPATH=src:. .venv/bin/python eval/synth_eval.py     # writes eval/synth_results.md
```

> **Result: 100% root-cause accuracy@1** (and @3) on the injected incidents — deterministic across runs.

On the golden reference incident, the engine correctly ranks `db-01` #1 and **rejects the tempting decoys** (a config change 10s before onset, a cache latency blip) because they have no dependency path to the symptom — the causation-vs-correlation story in one screen.

*(`eval/run_eval.py` is a separate, weaker benchmark that scores raw detection on hardware-only signal from captured flows; it is not representative of the causal engine and is kept only for reference.)*

## Design decisions & FAQ

**Why a deterministic core instead of "just asking an LLM"?**
Root-cause analysis must be **trustworthy and reproducible**. An LLM asked "what's the root cause?" is a slot machine — plausible but unaccountable, and different every run. Our engine is deterministic and every ranking decision is explainable from the evidence ledger. The LLM is used only for language tasks (explanation, adversarial review, remediation), where it adds value without risking correctness.

**How does it actually separate causation from correlation?**
By constraining candidates to those with a real **topology dependency path** to the symptom, and by **down-weighting severity** (5% of the score) while up-weighting causal attribution, config proximity, evidence, and rootness (~75%). A victim that looks worse than its cause still loses, because it can't explain the other victims and the cause can.

**Does it need Docker / a special testbed to run?**
**No.** It's math + graph traversal + API calls over whatever contract-conforming data you give it. Upload a dataset and it works.

**Is it deterministic?**
Yes — the causal ranking is deterministic (DoWhy is seeded; the fallback is pure). The LLM layer is the only non-deterministic part, and it is bounded so it can never change the #1 cause.

**What data does it need?**
Telemetry + topology at minimum (topology is what enables causation). Logs, alerts, and config changes enrich the evidence but aren't required.

**Is there an audit trail?**
Yes — a SHA-256 hash-chained ledger of every investigation step, verifiable at `GET /audit/verify`.

## Known limitations & roadmap

- **Deep-path non-config faults** — for a non-config fault three or more hops deep, causal attribution can occasionally rank an intermediate hop first (the true cause drops to #2–#3). Config faults and shallow faults recover robustly. A rootness tie-break in the ranker is the planned fix.
- **The "Full AI investigation" mode** needs `OPENAI_API_KEY`; the deterministic mode is the always-available default.
- **Displayed fault type** is inferred from config presence, so a non-config injected fault may display a related fault label.
- **Roadmap:** agentic RAG over a NOC runbook knowledge base (grounded remediation), a ranker tie-break for deep paths, and ingestion adapters for additional real-capture datasets.

## Licence

MIT
