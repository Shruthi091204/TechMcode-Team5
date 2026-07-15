from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from contracts.schemas import FaultType  # noqa: E402
from rca.pipeline import build_incident_from_data, load_topology  # noqa: E402
from rca.synth.generator import generate_incident  # noqa: E402

RESULTS_MD = _ROOT / "eval" / "synth_results.md"

SCENARIOS: list[tuple[str, FaultType]] = [
    ("db-01", FaultType.CONFIG_POOL_EXHAUSTION),
    ("app-03", FaultType.BAD_CONFIG_PUSH),
    ("app-04", FaultType.CAPACITY_EXHAUSTION),
    ("app-06", FaultType.DDOS_FLOOD),
    ("app-05", FaultType.NIC_FAILURE),
    ("app-09", FaultType.LINK_DEGRADATION),
    ("app-08", FaultType.PORT_SCAN),
    ("dns-01", FaultType.BAD_CONFIG_PUSH),
]


def _evaluate() -> list[dict]:
    topology = load_topology()
    rows: list[dict] = []
    for seed, (root, fault) in enumerate(SCENARIOS):
        incident = generate_incident(topology, root, fault, seed=seed)
        if incident is None:
            continue
        report = build_incident_from_data(
            topology,
            incident.telemetry,
            incident.logs,
            incident.alerts,
            incident.config_changes,
        )
        ranked = [hypothesis.root_cause_component for hypothesis in report.hypotheses]
        rows.append(
            {
                "root": root,
                "fault": fault.value,
                "symptom": incident.symptom,
                "predicted": ranked[0] if ranked else "none",
                "acc1": bool(ranked) and ranked[0] == root,
                "acc3": root in ranked[:3],
                "path": " -> ".join(incident.path),
            }
        )
    return rows


def _render(rows: list[dict]) -> str:
    acc1 = sum(row["acc1"] for row in rows) / len(rows) if rows else 0.0
    acc3 = sum(row["acc3"] for row in rows) / len(rows) if rows else 0.0
    lines = [
        "# Synthetic Incident Evaluation",
        "",
        f"Injected {len(rows)} incidents into the reference topology, each with a **known** root cause,",
        "and measured whether the causal engine recovers it.",
        "",
        "| Injected Root | Fault | Symptom | Engine #1 | acc@1 | acc@3 | Impact Path |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['root']} | {row['fault']} | {row['symptom']} | {row['predicted']} "
            f"| {'Y' if row['acc1'] else 'N'} | {'Y' if row['acc3'] else 'N'} | {row['path']} |"
        )
    lines += [
        "",
        f"**accuracy@1 = {acc1:.1%}** ({sum(r['acc1'] for r in rows)}/{len(rows)})  ·  "
        f"**accuracy@3 = {acc3:.1%}** ({sum(r['acc3'] for r in rows)}/{len(rows)})",
        "",
        "Ground truth is the injected root cause; it is never shown to the engine.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = _evaluate()
    header = f"{'Injected':10s} {'Fault':24s} {'Symptom':9s} {'Engine #1':10s} {'@1':4s} {'@3'}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['root']:10s} {row['fault']:24s} {row['symptom']:9s} {row['predicted']:10s} "
            f"{'Y' if row['acc1'] else 'N':4s} {'Y' if row['acc3'] else 'N'}"
        )
    acc1 = sum(row["acc1"] for row in rows) / len(rows) if rows else 0.0
    acc3 = sum(row["acc3"] for row in rows) / len(rows) if rows else 0.0
    print("-" * len(header))
    print(f"accuracy@1 = {acc1:.1%}  ({sum(r['acc1'] for r in rows)}/{len(rows)})")
    print(f"accuracy@3 = {acc3:.1%}  ({sum(r['acc3'] for r in rows)}/{len(rows)})")
    RESULTS_MD.write_text(_render(rows), encoding="utf-8")
    print(f"written to {RESULTS_MD}")


if __name__ == "__main__":
    main()
