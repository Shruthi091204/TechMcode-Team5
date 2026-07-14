from __future__ import annotations

from collections import deque
from functools import cached_property

import networkx as nx

from contracts.schemas import RelationKind, Topology

IMPACT_RELATIONS = frozenset({RelationKind.DEPENDS_ON, RelationKind.ROUTES_VIA})


class TopologyTwin:
    def __init__(self, topology: Topology) -> None:
        self._topology = topology

    @cached_property
    def _impact_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for component in self._topology.components:
            graph.add_node(
                component.component_id,
                component_type=component.component_type.value,
                tier=component.tier.value,
            )
        for edge in self._topology.dependencies:
            if edge.relation not in IMPACT_RELATIONS:
                continue
            graph.add_edge(edge.target_id, edge.source_id, relation=edge.relation.value)
        return graph

    def nodes(self) -> list[str]:
        return sorted(self._impact_graph.nodes)

    def has_path(self, cause_id: str, symptom_id: str) -> bool:
        return self.impact_path(cause_id, symptom_id) is not None

    def impact_path(self, cause_id: str, symptom_id: str) -> list[str] | None:
        graph = self._impact_graph
        if cause_id not in graph or symptom_id not in graph:
            return None
        if cause_id == symptom_id:
            return [cause_id]
        frontier: deque[list[str]] = deque([[cause_id]])
        visited = {cause_id}
        while frontier:
            trail = frontier.popleft()
            for dependent in sorted(graph.successors(trail[-1])):
                if dependent == symptom_id:
                    return [*trail, dependent]
                if dependent in visited:
                    continue
                visited.add(dependent)
                frontier.append([*trail, dependent])
        return None

    def blast_radius(self, cause_id: str) -> list[str]:
        graph = self._impact_graph
        if cause_id not in graph:
            return []
        return sorted(nx.descendants(graph, cause_id))

    def upstream_of(self, component_id: str) -> set[str]:
        graph = self._impact_graph
        if component_id not in graph:
            return set()
        return set(nx.ancestors(graph, component_id))

    def causal_subgraph(self, relevant_ids: set[str]) -> nx.DiGraph:
        present = [node for node in self._impact_graph.nodes if node in relevant_ids]
        return self._impact_graph.subgraph(present).copy()
