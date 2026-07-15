from __future__ import annotations

MERGE_COMPONENT = (
    "MERGE (c:Component {component_id: $component_id}) "
    "SET c.component_type = $component_type, c.tier = $tier, c.rack = $rack, "
    "c.capacity_mbps = $capacity_mbps"
)

MERGE_DEPENDENCY = (
    "MATCH (s:Component {component_id: $source_id}) "
    "MATCH (t:Component {component_id: $target_id}) "
    "MERGE (s)-[r:%s]->(t)"
)

IMPACT_PATH = (
    "MATCH path = shortestPath("
    "  (cause:Component {component_id: $cause_id})"
    "  -[:DEPENDS_ON|ROUTES_VIA*1..12]->"
    "  (symptom:Component {component_id: $symptom_id})"
    ") "
    "RETURN [node IN nodes(path) | node.component_id] AS chain"
)

BLAST_RADIUS = (
    "MATCH (victim:Component)-[:DEPENDS_ON|ROUTES_VIA*1..12]->(cause:Component {component_id: $cause_id}) "
    "RETURN collect(DISTINCT victim.component_id) AS blast_radius"
)

RESET_GRAPH = "MATCH (n) DETACH DELETE n"
