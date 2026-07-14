from __future__ import annotations

import os

from contracts.schemas import Topology
from rca.graph.queries import MERGE_COMPONENT, MERGE_DEPENDENCY, RESET_GRAPH


def neo4j_settings() -> dict[str, str]:
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "hackathon123"),
    }


def load_into_neo4j(topology: Topology) -> int:
    from neo4j import GraphDatabase

    settings = neo4j_settings()
    driver = GraphDatabase.driver(settings["uri"], auth=(settings["user"], settings["password"]))
    written = 0
    try:
        with driver.session() as session:
            session.run(RESET_GRAPH)
            for component in topology.components:
                session.run(
                    MERGE_COMPONENT,
                    component_id=component.component_id,
                    component_type=component.component_type.value,
                    tier=component.tier.value,
                    rack=component.rack,
                    capacity_mbps=component.capacity_mbps,
                )
                written += 1
            for edge in topology.dependencies:
                session.run(
                    MERGE_DEPENDENCY % edge.relation.value,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                )
    finally:
        driver.close()
    return written
