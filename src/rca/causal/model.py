from __future__ import annotations

import contextlib
import io
import warnings

import networkx as nx
import pandas as pd

from rca.graph.twin import TopologyTwin

CAUSAL_SIGNAL = "latency_ms"


def relevant_nodes(twin: TopologyTwin, candidates: list[str], symptom_id: str) -> set[str]:
    nodes: set[str] = {symptom_id}
    for candidate in candidates:
        path = twin.impact_path(candidate, symptom_id)
        if path is None:
            continue
        nodes.update(path)
    return nodes


def _signal_frame(telemetry: pd.DataFrame, nodes: set[str]) -> pd.DataFrame:
    scoped = telemetry[telemetry["component_id"].isin(nodes)]
    wide = scoped.pivot_table(
        index="window_start",
        columns="component_id",
        values=CAUSAL_SIGNAL,
        aggfunc="mean",
    )
    return wide.dropna(axis=1, how="any").sort_index()


def _deterministic_attribution(twin: TopologyTwin, candidates: list[str], symptom_id: str) -> dict[str, float]:
    candidate_set = set(candidates)
    scores: dict[str, float] = {}
    for candidate in candidates:
        if twin.impact_path(candidate, symptom_id) is None:
            scores[candidate] = 0.0
            continue
        explains = len(set(twin.blast_radius(candidate)) & candidate_set)
        scores[candidate] = 1.0 + explains
    return _normalise(scores)


def _normalise(scores: dict[str, float]) -> dict[str, float]:
    total = sum(scores.values())
    if total <= 0.0:
        even = 1.0 / max(1, len(scores))
        return {node: even for node in scores}
    return {node: value / total for node, value in scores.items()}


def attribute_causes(
    twin: TopologyTwin,
    candidates: list[str],
    symptom_id: str,
    telemetry: pd.DataFrame,
) -> dict[str, float]:
    if len(candidates) <= 1:
        return _normalise({candidate: 1.0 for candidate in candidates})
    try:
        return _dowhy_attribution(twin, candidates, symptom_id, telemetry)
    except Exception:
        return _deterministic_attribution(twin, candidates, symptom_id)


def _dowhy_attribution(
    twin: TopologyTwin,
    candidates: list[str],
    symptom_id: str,
    telemetry: pd.DataFrame,
) -> dict[str, float]:
    from dowhy import gcm

    gcm.config.disable_progress_bars()

    nodes = relevant_nodes(twin, candidates, symptom_id)
    frame = _signal_frame(telemetry, nodes)
    if symptom_id not in frame.columns or frame.shape[0] < 8:
        raise ValueError("insufficient signal for causal fitting")

    subgraph: nx.DiGraph = twin.causal_subgraph(set(frame.columns))
    if subgraph.number_of_edges() == 0:
        raise ValueError("empty causal subgraph")

    split = max(4, int(frame.shape[0] * 0.45))
    baseline = frame.iloc[:split]
    anomalous = frame.iloc[[-1]]

    hush_out = contextlib.redirect_stdout(io.StringIO())
    hush_err = contextlib.redirect_stderr(io.StringIO())
    with warnings.catch_warnings(), hush_out, hush_err:
        warnings.simplefilter("ignore")
        scm = gcm.StructuralCausalModel(subgraph)
        gcm.auto.assign_causal_mechanisms(scm, baseline)
        gcm.fit(scm, baseline)
        contributions = gcm.attribute_anomalies(scm, target_node=symptom_id, anomaly_samples=anomalous)

    attribution = {
        candidate: float(abs(contributions.get(candidate, [0.0])[0]))
        for candidate in candidates
        if candidate in frame.columns
    }
    for candidate in candidates:
        attribution.setdefault(candidate, 0.0)
    if sum(attribution.values()) <= 0.0:
        raise ValueError("degenerate attribution")
    return _normalise(attribution)
