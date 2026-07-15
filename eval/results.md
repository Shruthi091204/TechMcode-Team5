# P2 Detection Evaluation Results

Evaluated against 6 real incidents captured by the testbed.
Telemetry source: `hardware_telemetry.csv` (cpu_pct, mem_pct only).
Detector: MAD baseline + PELT change-point (P2 modules).

## Per-Incident Results

| Scenario | True Root Cause | Rank-1 Detection | acc@1 | acc@3 | MTTD | Anomalies |
|---|---|---|---|---|---|---|
| bad_config_push | web-01 | db-01 | N | N | N/A | 1 |
| ddos_flood | lb-01 | db-01 | N | N | N/A | 1 |
| link_degradation | db-01 | lb-01 | N | N | N/A | 1 |
| nic_failure | app-01 | db-01 | N | N | N/A | 1 |
| port_scan | lb-01 | — | N | N | N/A | 0 |
| capacity_exhaustion | db-01 | db-01 | Y | Y | 11.6s | 1 |

## Summary Metrics

| Metric | Value |
|---|---|
| accuracy@1 | **16.7%** (1/6) |
| accuracy@3 | **16.7%** (1/6) |
| mean MTTD  | **11.6s** |

## Methodology Notes

- Ground truth (`ground_truth.json`) is read **after** detection completes and
  is never used to guide or tune the detector.
- MTTD counts only scenarios where the true root-cause component has a detected
  anomaly with `onset_ts >= injection_timestamp`.
- Only `cpu_pct` and `mem_pct` carry real signal; the six remaining TelemetryPoint
  fields are zero-filled (not available from `hardware_telemetry.csv`).
- Detection using full-KPI telemetry (`contracts/fixtures/telemetry.csv`) produces
  125 anomalies and correctly identifies the db-01 root cause within one 30s window.
