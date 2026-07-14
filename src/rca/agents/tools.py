import csv
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
# from anthropic.beta.tools import tool as beta_tool
from anthropic import beta_tool;

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"


@lru_cache(maxsize=1)
def load_topology_fixture() -> dict[str, Any]:
    topology_path = FIXTURES_DIR / "topology.json"
    if not topology_path.exists():
        return {"components": [], "dependencies": []}
    return json.loads(topology_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_telemetry_fixture() -> list[dict[str, Any]]:
    telemetry_path = FIXTURES_DIR / "telemetry.csv"
    if not telemetry_path.exists():
        return []
    with telemetry_path.open(mode="r", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


@lru_cache(maxsize=1)
def load_logs_fixture() -> list[dict[str, Any]]:
    logs_path = FIXTURES_DIR / "logs.jsonl"
    if not logs_path.exists():
        return []
    raw_lines = logs_path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in raw_lines if line.strip()]


@lru_cache(maxsize=1)
def load_changes_fixture() -> list[dict[str, Any]]:
    changes_path = FIXTURES_DIR / "config_changes.jsonl"
    if not changes_path.exists():
        return []
    raw_lines = changes_path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in raw_lines if line.strip()]


def parse_timestamp(timestamp_string: str) -> datetime:
    return datetime.fromisoformat(timestamp_string.replace("Z", "+00:00"))


def is_within_window(record_timestamp: str, window_start: str, window_end: str) -> bool:
    current_time = parse_timestamp(record_timestamp)
    start_time = parse_timestamp(window_start)
    end_time = parse_timestamp(window_end)
    return start_time <= current_time <= end_time


@beta_tool
def query_graph(component_id: str) -> dict[str, Any]:
    topology_graph = load_topology_fixture()
    target_component = next(
        (comp for comp in topology_graph.get("components", []) if comp.get("component_id") == component_id),
        None,
    )
    if not target_component:
        return {"error": f"component {component_id} not found in topology"}

    upstream_dependencies = [
        dep for dep in topology_graph.get("dependencies", []) if dep.get("target_id") == component_id
    ]
    downstream_dependencies = [
        dep for dep in topology_graph.get("dependencies", []) if dep.get("source_id") == component_id
    ]

    return {
        "component": target_component,
        "upstream_dependencies": upstream_dependencies,
        "downstream_dependencies": downstream_dependencies,
    }


@beta_tool
def query_metrics(component_id: str, window_start: str, window_end: str) -> list[dict[str, Any]]:
    telemetry_records = load_telemetry_fixture()
    matching_records = []
    for record in telemetry_records:
        if record.get("component_id") != component_id:
            continue
        if not is_within_window(record.get("window_start", ""), window_start, window_end):
            continue
        matching_records.append(record)
    return matching_records


@beta_tool
def query_logs(component_id: str, window_start: str, window_end: str) -> list[dict[str, Any]]:
    log_records = load_logs_fixture()
    matching_records = []
    for record in log_records:
        if record.get("component_id") != component_id:
            continue
        if not is_within_window(record.get("ts", ""), window_start, window_end):
            continue
        matching_records.append(record)
    return matching_records


@beta_tool
def query_changes(window_start: str, window_end: str) -> list[dict[str, Any]]:
    change_records = load_changes_fixture()
    matching_records = []
    for record in change_records:
        if not is_within_window(record.get("ts", ""), window_start, window_end):
            continue
        matching_records.append(record)
    return matching_records