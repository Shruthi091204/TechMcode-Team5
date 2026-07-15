from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from contracts.schemas import TelemetryPoint
from src.rca.ingest.csv_adapter import load_telemetry_csv
from src.rca.ingest.store import TelemetryStore

FIXTURES = Path(__file__).resolve().parents[1] / "contracts" / "fixtures"
_UTC = UTC

_BASE_TS = datetime(2026, 7, 14, 14, 25, 0, tzinfo=_UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _point(
    component_id: str = "db-01",
    offset_minutes: int = 0,
    latency_ms: float = 10.0,
    connection_count: int = 100,
) -> TelemetryPoint:
    return TelemetryPoint(
        component_id=component_id,
        window_start=_BASE_TS + timedelta(minutes=offset_minutes),
        latency_ms=latency_ms,
        jitter_ms=0.5,
        packet_loss_pct=0.0,
        throughput_mbps=50.0,
        error_rate=0.001,
        connection_count=connection_count,
        cpu_pct=30.0,
        mem_pct=40.0,
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def test_in_memory_store_creates_without_error():
    with TelemetryStore(":memory:") as store:
        assert store is not None


def test_default_path_is_in_memory():
    with TelemetryStore() as store:
        assert store.row_count() == 0


def test_empty_store_row_count_is_zero():
    with TelemetryStore() as store:
        assert store.row_count() == 0


def test_on_disk_store_creates_file(tmp_path: Path):
    db_file = tmp_path / "test.duckdb"
    with TelemetryStore(db_file) as store:
        store.write_telemetry([_point()])
    assert db_file.exists()


def test_on_disk_store_accepts_path_object(tmp_path: Path):
    db_file = tmp_path / "path_obj.duckdb"
    with TelemetryStore(db_file) as store:
        assert store.row_count() == 0


# ---------------------------------------------------------------------------
# write_telemetry — basic behaviour
# ---------------------------------------------------------------------------


def test_write_empty_list_returns_zero():
    with TelemetryStore() as store:
        assert store.write_telemetry([]) == 0


def test_write_empty_list_does_not_change_row_count():
    with TelemetryStore() as store:
        store.write_telemetry([])
        assert store.row_count() == 0


def test_write_single_point_returns_one():
    with TelemetryStore() as store:
        count = store.write_telemetry([_point()])
        assert count == 1


def test_write_single_point_increases_row_count():
    with TelemetryStore() as store:
        store.write_telemetry([_point()])
        assert store.row_count() == 1


def test_write_multiple_points_returns_correct_count():
    points = [_point(offset_minutes=i) for i in range(5)]
    with TelemetryStore() as store:
        assert store.write_telemetry(points) == 5


def test_write_multiple_points_increases_row_count():
    points = [_point(offset_minutes=i) for i in range(5)]
    with TelemetryStore() as store:
        store.write_telemetry(points)
        assert store.row_count() == 5


def test_write_is_cumulative():
    with TelemetryStore() as store:
        store.write_telemetry([_point(offset_minutes=0)])
        store.write_telemetry([_point(offset_minutes=1)])
        assert store.row_count() == 2


# ---------------------------------------------------------------------------
# read_telemetry — empty database
# ---------------------------------------------------------------------------


def test_read_empty_store_returns_empty_list():
    with TelemetryStore() as store:
        assert store.read_telemetry() == []


def test_read_with_component_filter_on_empty_store():
    with TelemetryStore() as store:
        assert store.read_telemetry(component_id="db-01") == []


# ---------------------------------------------------------------------------
# read_telemetry — return type and contract
# ---------------------------------------------------------------------------


def test_read_returns_list():
    with TelemetryStore() as store:
        store.write_telemetry([_point()])
        result = store.read_telemetry()
        assert isinstance(result, list)


def test_read_items_are_telemetry_points():
    with TelemetryStore() as store:
        store.write_telemetry([_point()])
        result = store.read_telemetry()
        assert all(isinstance(tp, TelemetryPoint) for tp in result)


def test_round_trip_count():
    points = [_point(offset_minutes=i) for i in range(3)]
    with TelemetryStore() as store:
        store.write_telemetry(points)
        result = store.read_telemetry()
        assert len(result) == 3


# ---------------------------------------------------------------------------
# read_telemetry — field fidelity
# ---------------------------------------------------------------------------


def test_round_trip_component_id():
    p = _point(component_id="app-03")
    with TelemetryStore() as store:
        store.write_telemetry([p])
        result = store.read_telemetry()
    assert result[0].component_id == "app-03"


def test_round_trip_window_start_timezone_aware():
    with TelemetryStore() as store:
        store.write_telemetry([_point()])
        result = store.read_telemetry()
    assert result[0].window_start.tzinfo is not None


def test_round_trip_window_start_value():
    p = _point(offset_minutes=5)
    with TelemetryStore() as store:
        store.write_telemetry([p])
        result = store.read_telemetry()
    assert result[0].window_start == p.window_start


def test_round_trip_latency_ms():
    p = _point(latency_ms=42.7)
    with TelemetryStore() as store:
        store.write_telemetry([p])
        result = store.read_telemetry()
    assert abs(result[0].latency_ms - 42.7) < 1e-9


def test_round_trip_connection_count():
    p = _point(connection_count=250)
    with TelemetryStore() as store:
        store.write_telemetry([p])
        result = store.read_telemetry()
    assert result[0].connection_count == 250


# ---------------------------------------------------------------------------
# read_telemetry — component_id filter
# ---------------------------------------------------------------------------


def test_filter_by_component_id_returns_only_matching():
    db = _point(component_id="db-01")
    app = _point(component_id="app-01")
    with TelemetryStore() as store:
        store.write_telemetry([db, app])
        result = store.read_telemetry(component_id="db-01")
    assert all(tp.component_id == "db-01" for tp in result)
    assert len(result) == 1


def test_filter_by_component_id_unknown_returns_empty():
    with TelemetryStore() as store:
        store.write_telemetry([_point()])
        result = store.read_telemetry(component_id="unknown-99")
    assert result == []


# ---------------------------------------------------------------------------
# read_telemetry — time-range filters
# ---------------------------------------------------------------------------


def test_filter_since_excludes_earlier_rows():
    early = _point(offset_minutes=0)
    late = _point(offset_minutes=5)
    cutoff = _BASE_TS + timedelta(minutes=3)
    with TelemetryStore() as store:
        store.write_telemetry([early, late])
        result = store.read_telemetry(since=cutoff)
    assert all(tp.window_start >= cutoff for tp in result)
    assert len(result) == 1


def test_filter_until_excludes_later_rows():
    early = _point(offset_minutes=0)
    late = _point(offset_minutes=5)
    cutoff = _BASE_TS + timedelta(minutes=3)
    with TelemetryStore() as store:
        store.write_telemetry([early, late])
        result = store.read_telemetry(until=cutoff)
    assert all(tp.window_start <= cutoff for tp in result)
    assert len(result) == 1


def test_filter_since_and_until_combined():
    points = [_point(offset_minutes=i) for i in range(10)]
    start = _BASE_TS + timedelta(minutes=2)
    end = _BASE_TS + timedelta(minutes=5)
    with TelemetryStore() as store:
        store.write_telemetry(points)
        result = store.read_telemetry(since=start, until=end)
    assert all(start <= tp.window_start <= end for tp in result)
    assert len(result) == 4  # offsets 2, 3, 4, 5


def test_filter_component_and_time_combined():
    db_points = [_point(component_id="db-01", offset_minutes=i) for i in range(5)]
    app_points = [_point(component_id="app-01", offset_minutes=i) for i in range(5)]
    cutoff = _BASE_TS + timedelta(minutes=2)
    with TelemetryStore() as store:
        store.write_telemetry(db_points + app_points)
        result = store.read_telemetry(component_id="db-01", since=cutoff)
    assert all(tp.component_id == "db-01" for tp in result)
    assert all(tp.window_start >= cutoff for tp in result)


# ---------------------------------------------------------------------------
# read_telemetry — ordering
# ---------------------------------------------------------------------------


def test_output_ordered_by_component_then_window_start():
    points = [
        _point(component_id="web-01", offset_minutes=1),
        _point(component_id="db-01", offset_minutes=2),
        _point(component_id="db-01", offset_minutes=0),
    ]
    with TelemetryStore() as store:
        store.write_telemetry(points)
        result = store.read_telemetry()
    pairs = [(tp.component_id, tp.window_start) for tp in result]
    assert pairs == sorted(pairs)


# ---------------------------------------------------------------------------
# context manager
# ---------------------------------------------------------------------------


def test_context_manager_closes_cleanly():
    with TelemetryStore() as store:
        store.write_telemetry([_point()])
        assert store.row_count() == 1


def test_context_manager_with_path(tmp_path: Path):
    db_file = tmp_path / "ctx.duckdb"
    with TelemetryStore(db_file) as store:
        store.write_telemetry([_point()])
    assert db_file.exists()


# ---------------------------------------------------------------------------
# Fixture integration
# ---------------------------------------------------------------------------


def test_fixture_telemetry_round_trips():
    """All 930 fixture rows must survive a write → read round trip."""
    fixture_points = load_telemetry_csv(FIXTURES / "telemetry.csv")
    with TelemetryStore() as store:
        written = store.write_telemetry(fixture_points)
        result = store.read_telemetry()
    assert written == 930
    assert len(result) == 930


def test_fixture_component_filter():
    """Filtering by component_id on the fixture must return only that component."""
    fixture_points = load_telemetry_csv(FIXTURES / "telemetry.csv")
    with TelemetryStore() as store:
        store.write_telemetry(fixture_points)
        db01 = store.read_telemetry(component_id="db-01")
    assert all(tp.component_id == "db-01" for tp in db01)
    assert len(db01) == 31


def test_fixture_all_items_are_telemetry_points():
    fixture_points = load_telemetry_csv(FIXTURES / "telemetry.csv")
    with TelemetryStore() as store:
        store.write_telemetry(fixture_points)
        result = store.read_telemetry()
    assert all(isinstance(tp, TelemetryPoint) for tp in result)


def test_fixture_timezone_preserved_after_round_trip():
    fixture_points = load_telemetry_csv(FIXTURES / "telemetry.csv")
    with TelemetryStore() as store:
        store.write_telemetry(fixture_points)
        result = store.read_telemetry()
    assert all(tp.window_start.tzinfo is not None for tp in result)
