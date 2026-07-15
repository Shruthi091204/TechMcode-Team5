# Synthetic Incident Evaluation

Injected 8 incidents into the reference topology, each with a **known** root cause,
and measured whether the causal engine recovers it.

| Injected Root | Fault | Symptom | Engine #1 | acc@1 | acc@3 | Impact Path |
|---|---|---|---|---|---|---|
| db-01 | config_pool_exhaustion | web-01 | db-01 | Y | Y | db-01 -> app-01 -> web-01 |
| cache-01 | capacity_exhaustion | web-01 | cache-01 | Y | Y | cache-01 -> app-01 -> web-01 |
| cache-02 | ddos_flood | web-03 | cache-02 | Y | Y | cache-02 -> app-06 -> web-03 |
| app-03 | bad_config_push | web-02 | app-03 | Y | Y | app-03 -> web-02 |
| app-07 | capacity_exhaustion | web-04 | app-07 | Y | Y | app-07 -> web-04 |
| app-09 | link_degradation | web-05 | app-09 | Y | Y | app-09 -> web-05 |
| mq-01 | ddos_flood | web-01 | mq-01 | Y | Y | mq-01 -> app-01 -> web-01 |
| dns-01 | bad_config_push | web-01 | dns-01 | Y | Y | dns-01 -> web-01 |

**accuracy@1 = 100.0%** (8/8)  ·  **accuracy@3 = 100.0%** (8/8)

Ground truth is the injected root cause; it is never shown to the engine.
