# Network Anomaly Root-Cause Assistant

An assistant for network operations that ingests telemetry, logs, alerts, topology, and configuration changes, detects anomalies across time windows, and produces **ranked, evidence-backed root-cause hypotheses** — distinguishing genuine causation from mere correlation.

## The problem

A network operations centre receives thousands of alerts an hour. Most are symptoms. Engineers spend the majority of mean-time-to-resolution simply deciding *which* signal is the cause and which are downstream noise. Tools that correlate events by timestamp routinely blame whichever component moved first — which is frequently the victim, not the culprit.

## The approach

The system is deliberately split into a deterministic core and a bounded reasoning layer.

**Deterministic core.** Anomalies are detected with robust baselines and change-point detection, which yields the *onset time* of a degradation rather than a threshold crossing. Candidate root causes are then constrained by the network topology itself: a component can only be proposed as a cause if a real dependency path exists from it to the symptomatic component. Causal attribution and counterfactual analysis run over that topology-constrained graph. The engine is fully deterministic — the same incident produces the same ranking every time.

**Reasoning layer.** A language model is used only for what it is good at — writing the incident timeline, explaining findings in plain English, adversarially reviewing each hypothesis, and recommending next diagnostic steps. It never selects the root cause, and its influence on confidence is bounded so it can never override the deterministic ranking.

Every hypothesis carries an explicit evidence ledger separating **confirmed evidence**, **correlated signals**, and **missing evidence** — and the missing evidence directly drives the recommended next steps. Every step of an investigation is written to a SHA-256 hash-chained audit trail.

## Architecture

```
 Telemetry · Logs · Alerts · Topology · Config changes   (frozen data contract)
                          │
                          ▼
              Anomaly detection          MAD baseline + PELT change-point
                          │
                          ▼
        Topology-constrained causal engine    networkx impact paths · DoWhy
                          │                    attribution · counterfactual replay
                          ▼
          Ranked hypotheses + evidence ledger
                          │
                          ▼
              Bounded LLM reasoning        skeptic (STORM) · investigator ·
                          │                remediation — never picks the cause
                          ▼
      Incident timeline · narrative · next steps        + hash-chained audit trail
                          │
                          ▼
                  FastAPI  ──►  Next.js NOC dashboard
```

## Tech stack

| Layer | Choice |
|---|---|
| Contract | Pydantic v2 (frozen models, exported JSON Schema) |
| Detection | NumPy / SciPy robust baselines, `ruptures` PELT change-point |
| Causal engine | `networkx` topology twin, DoWhy GCM attribution with deterministic fallback |
| Reasoning agents | OpenAI (structured outputs + tool use), bounded confidence influence |
| API | FastAPI |
| Frontend | Next.js 15, React 19, Cytoscape.js, Recharts, Tailwind |

## Repository layout

```
contracts/        frozen data contract: schemas.py, schemas.json, golden fixture
src/rca/
  detect/         anomaly detection (baseline, change-point, windowing)
  graph/          networkx topology twin + impact-path queries
  causal/         candidate filter, attribution, counterfactual, evidence, ranker
  agents/         OpenAI skeptic / investigator / remediation + tool runner
  audit/          SHA-256 hash-chained audit log + verifier
  api/            FastAPI routes (topology, incident, replay, audit)
eval/             replay harness → accuracy@1 / @3 / MTTD
web/              Next.js NOC dashboard
tests/            contract + engine + detection + ingestion suites
```

## Getting started

Requires Python 3.11+ and Node 20+.

### Backend

```bash
make setup                 # create .venv and install dependencies
make check                 # static analysis + full test suite

cp .env.example .env        # then set OPENAI_API_KEY and OPENAI_MODEL (default gpt-4.1)
PYTHONPATH=src .venv/bin/uvicorn rca.api.main:app --port 8000
```

The reasoning layer requires `OPENAI_API_KEY`. The deterministic engine, the API, and the pre-computed reference incident all run without it.

### Frontend

```bash
cd web
npm install
npm run dev                # http://localhost:3000  →  /incident/INC-1001
```

The dashboard proxies `/api/*` to the backend on port 8000. Open the reference incident, or use the **Run Investigation** launcher to execute the full live pipeline (detection → causal engine → reasoning agents) end-to-end.

### Evaluation

```bash
PYTHONPATH=src:. .venv/bin/python eval/run_eval.py   # writes eval/results.md
```

## The contract

`contracts/` holds the frozen data contract that every component is built against: Pydantic models in `schemas.py`, the exported JSON Schema in `schemas.json`, and a fully validated reference incident under `fixtures/`. Freezing the contract first let detection, causal inference, the reasoning agents, and the frontend all be developed in parallel against the same golden incident.

## Frontend NOC dashboard

A high-density, NOC-style diagnostics panel built in Next.js 15.

- **Causal topology graph** — Cytoscape.js highlights the dependency path and pulses the active root-cause node.
- **Three-tier evidence ledger** — distinct `CONFIRMED` / `CORRELATED` / `MISSING` columns keep confirmed fact visually separate from correlation.
- **Investigation timeline** — traces propagation from fault to symptom, with counterfactual replay controls.
- **Investigation launcher** — runs the full live pipeline on the reference bad-configuration incident; additional fault classes (fiber cut, DDoS, NIC failure, port scan) are scaffolded for future datasets.

## Status

The end-to-end pipeline — detection, topology-constrained causal ranking, bounded LLM reasoning, audit trail, API, and dashboard — is functional against the golden reference incident. Ingestion adapters for additional real-capture datasets are in progress.

## Licence

MIT
