# Network Anomaly Root-Cause Assistant

An AI assistant for network operations that ingests telemetry, logs, alerts, topology, and configuration changes, detects anomalies across time windows, and produces **ranked, evidence-backed root-cause hypotheses** — distinguishing genuine causation from mere correlation.

## The problem

A network operations centre receives thousands of alerts an hour. Most are symptoms. Engineers spend the majority of mean-time-to-resolution simply deciding *which* signal is the cause and which are downstream noise. Tools that correlate events by timestamp routinely blame whichever component moved first — which is frequently the victim, not the culprit.

## The approach

The system is deliberately split into a deterministic core and a bounded reasoning layer.

**Deterministic core.** Anomalies are detected with robust baselines and change-point detection, which yields the *onset time* of a degradation rather than a threshold crossing. Candidate root causes are then constrained by the network topology itself: a component can only be proposed as a cause if a real dependency path exists from it to the symptomatic component. Causal attribution and counterfactual analysis run over that topology-constrained graph.

**Reasoning layer.** A language model is used only for what it is good at — writing the incident timeline, explaining findings in plain English, adversarially reviewing each hypothesis, and recommending next diagnostic steps. It never selects the root cause.

Every hypothesis carries an explicit evidence ledger separating **confirmed evidence**, **correlated signals**, and **missing evidence** — and the missing evidence directly drives the recommended next steps.

## Architecture

```
Telemetry · Logs · Alerts · Topology · Config changes
                     │
                     ▼
        Ingestion  →  Anomaly detection  →  Topology-constrained causal engine
                     │                              │
                     │                              ▼
                     │                    Ranked hypotheses + evidence ledger
                     │                              │
                     ▼                              ▼
              Tamper-evident audit trail   Incident timeline · Narrative · Remediation
```

## Status

Under active development. Detailed setup and execution instructions will accompany the first tagged release.

## Licence

MIT
