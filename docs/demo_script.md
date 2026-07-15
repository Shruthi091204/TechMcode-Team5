# Hackathon Demo Walkthrough Script

Welcome to the Network Anomaly Root-Cause Assistant frontend demo. Use this step-by-step guide to showcase the NOC dashboard capabilities to the hackathon judges.

## Core Demo Steps

### 1. Initial State (NOC Console Dashboard)
- **Action**: Load the dashboard. It will auto-redirect to `/incident/INC-2026-0042`.
- **Narration**: "We are looking at the live Network Operations Center (NOC) dashboard for a high-severity incident: `HTTP 504 Gateway Timeout` on server `web-02`. The design is optimized for network engineers: zero-radius sharp corners, low-contrast hairline borders, high-density monospace telemetry, and a dark theme."

### 2. Network Topology Engine Visualization
- **Action**: Highlight the central graph panel. Point out the orange path and the pulsing red node.
- **Narration**: "At the center is our real-time Topology Graph. The engine immediately traces the causal pathway: `db-01` → `tor-03` → `core-01` → `lb-01` → `web-02`. The root cause node (`db-01`) is highlighted with a signature red radar-sweep animation, separating it from the rest of the greyed-out network topology nodes."

### 3. Ranked Hypotheses & Evidence Ledger
- **Action**: Select Rank 1 in the right-hand panel, then examine the three columns.
- **Narration**: "To the right, you see our ranked root-cause hypotheses. Rank 1 is `Database Connection Pool Exhaustion` on `db-01` with 87% confidence. Below it is our key differentiator: the **Evidence Ledger**. It clearly splits telemetry findings into three columns:
  - **Confirmed**: Hard facts (e.g., config changes altering `max_connections` to 50, and pool limits hit).
  - **Correlated**: Timed telemetry spikes matching the event (e.g., packet retransmissions on `tor-03`).
  - **Missing**: Critical checks that *did not* fire, confirming it is not a hardware platform disk failure or an edge firewall drop."

### 4. Interactive Counterfactual Simulator
- **Action**: Locate the **Counterfactual Simulation Engine** toggle. Switch it to **ON**.
- **Observation**: The deployment config change on `db-01` in the timeline gets struck through with a `[STRIKE: COUNTERFACTUAL_REMOVED]` label, and the console logs track state transition.
- **Narration**: "Our engine runs counterfactual simulations. If we toggle `Simulate Recovery`, it isolates the primary config change. The timeline strikes through the initial config push on `db-01` and simulates how the system recovers, showing that thread pool queues clear out."

### 5. Adversarial Skeptic bot Debate
- **Action**: Point to the **Skeptic Verdict Transcript** panel.
- **Narration**: "To prevent automated tunnel vision, we build in an adversarial check. The Investigator AI argues database pool saturation, but our Skeptic Agent reviews SNMP retransmission metrics and demands validation of switch interfaces to rule out physical fiber link issues."

### 6. Interactive Fault Injector Centerpiece
- **Action**: Click any button in the **Fault Injection Panel** (e.g., `FIBER CUT` or `PORT SCAN`).
- **Observation**: The button enters a flashing `INJECTING...` state with a loading indicator for 1.5 seconds, then logs the triggered simulation details in the live scrolling `CONSOLE_OUTPUT` log.
- **Narration**: "Judges can test the platform live. Clicking any vector in our Fault Injector panel simulates real-time failure injection, routing diagnostic vectors directly to our backend causal pipelines."
