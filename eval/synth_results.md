# Synthetic Incident Evaluation

Injected 8 incidents into the reference topology, each with a **known** root cause,
and measured whether the causal engine recovers it.

| Injected Root | Fault | Symptom | Engine #1 | acc@1 | acc@3 | Impact Path |
|---|---|---|---|---|---|---|
| db-01 | config_pool_exhaustion | web-01 | db-01 | Y | Y | db-01 -> app-01 -> web-01 |
| app-03 | bad_config_push | web-02 | app-03 | Y | Y | app-03 -> web-02 |
| app-04 | capacity_exhaustion | web-02 | app-04 | Y | Y | app-04 -> web-02 |
| app-06 | ddos_flood | web-03 | app-06 | Y | Y | app-06 -> web-03 |
| app-05 | nic_failure | web-03 | app-05 | Y | Y | app-05 -> web-03 |
| app-09 | link_degradation | web-05 | app-09 | Y | Y | app-09 -> web-05 |
| app-08 | port_scan | web-04 | app-08 | Y | Y | app-08 -> web-04 |
| dns-01 | bad_config_push | web-01 | dns-01 | Y | Y | dns-01 -> web-01 |

**accuracy@1 = 100.0%** (8/8)  ·  **accuracy@3 = 100.0%** (8/8)

Ground truth is the injected root cause; it is never shown to the engine.
