from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from contracts.schemas import TelemetryPoint


@dataclass(frozen=True)
class FlowRecord:
    """Single raw-packet row as produced by testbed/capture.py via tshark.

    Columns captured by tshark match these fields:
        frame.time_epoch  →  time_epoch  (Unix epoch seconds, float)
        ip.src            →  src_ip
        ip.dst            →  dst_ip
        tcp.srcport       →  src_port    (0 for non-TCP packets)
        tcp.dstport       →  dst_port    (0 for non-TCP packets)
        frame.len         →  frame_len   (bytes including Ethernet overhead)

    This is an internal P2 type — it is not a frozen Pydantic contract.
    """

    time_epoch: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    frame_len: int


def _floor_to_window(epoch: float, window_seconds: int) -> datetime:
    """Return the UTC datetime of the window boundary containing *epoch*."""
    boundary = int(epoch) // window_seconds * window_seconds
    return datetime.fromtimestamp(boundary, tz=UTC)


def _compute_kpis(
    records: frozenset[FlowRecord],
    component_id: str,
    window_start: datetime,
    window_seconds: int,
) -> TelemetryPoint:
    """Build one TelemetryPoint from all packets in a (component, window) bucket.

    KPI mapping from raw packet fields:

    throughput_mbps:
        Total bytes transferred (sum of frame_len across all packets) converted
        to megabits per second over the window duration.
        Formula: sum(frame_len) × 8 ÷ (window_seconds × 1 000 000)

    connection_count:
        Number of distinct 4-tuple flows (src_ip, src_port, dst_ip, dst_port)
        seen in the window.  Mirrors the NetFlow view of simultaneous sessions.

    jitter_ms:
        Sample standard deviation of inter-packet arrival gaps (in ms).
        Requires ≥ 3 packets (≥ 2 gaps) for a meaningful estimate; returns 0.0
        for fewer packets.  This is the standard RFC 3550 jitter approximation.

    latency_ms:
        Mean inter-packet arrival gap divided by 2, used as a crude half-RTT
        proxy when true TCP round-trip times (SYN/SYN-ACK pairs) are not
        tracked.  Returns 0.0 when fewer than 2 packets are present.
        Note: this is an approximation; accurate latency requires RTT tracking
        beyond what basic tshark frame captures provide.

    packet_loss_pct, error_rate:
        Both default to 0.0 — they require TCP sequence-number analysis or
        protocol-level error counters that are not present in raw frame data.

    cpu_pct, mem_pct:
        Both default to 0.0 — these come from the hardware-telemetry recorder
        (recorder.py / docker stats), not from flow captures.  A future
        extension may merge hardware metrics via a secondary input.
    """
    sorted_times = sorted(r.time_epoch for r in records)

    total_bytes = sum(r.frame_len for r in records)
    throughput_mbps = total_bytes * 8.0 / (window_seconds * 1_000_000.0)

    connection_count = len(
        {(r.src_ip, r.src_port, r.dst_ip, r.dst_port) for r in records}
    )

    if len(sorted_times) >= 2:
        gaps_ms = [
            (sorted_times[i + 1] - sorted_times[i]) * 1_000.0
            for i in range(len(sorted_times) - 1)
        ]
        mean_gap_ms = sum(gaps_ms) / len(gaps_ms)
        latency_ms = mean_gap_ms / 2.0
        jitter_ms = statistics.stdev(gaps_ms) if len(gaps_ms) >= 2 else 0.0
    else:
        latency_ms = 0.0
        jitter_ms = 0.0

    return TelemetryPoint(
        component_id=component_id,
        window_start=window_start,
        latency_ms=max(0.0, latency_ms),
        jitter_ms=max(0.0, jitter_ms),
        packet_loss_pct=0.0,
        throughput_mbps=throughput_mbps,
        error_rate=0.0,
        connection_count=connection_count,
        cpu_pct=0.0,
        mem_pct=0.0,
    )


def aggregate_flows(
    records: list[FlowRecord],
    ip_to_component: dict[str, str],
    window_seconds: int = 30,
) -> list[TelemetryPoint]:
    """Aggregate raw per-packet flow records into per-component TelemetryPoint windows.

    This implements the standard NetFlow / IPFIX aggregation method: raw
    packet-level data is grouped into fixed time windows per network device,
    and a set of KPI fields (throughput, jitter, connection count, …) is
    computed for each (component, window) bucket.

    A packet is attributed to every component whose IP address appears as
    *either* the source or the destination.  A packet between two known
    components therefore contributes to both components' buckets — consistent
    with how real NetFlow exporters report per-device traffic.  Packets whose
    IPs do not appear in *ip_to_component* are silently ignored.

    Args:
        records:          Raw FlowRecord objects, typically from load_flow_csv.
                          May be empty, in which case an empty list is returned.
        ip_to_component:  Mapping from container / device IP address to the
                          canonical component_id used in TelemetryPoint.
                          Values must satisfy the ComponentId pattern
                          (e.g. "db-01", "app-03").
        window_seconds:   Width of each aggregation window in seconds.
                          Must be a positive integer.  Default: 30 (matching
                          the canonical TelemetryPoint cadence in the fixture).

    Returns:
        One TelemetryPoint per (component_id, window_start) bucket that
        contains at least one matching packet, sorted by (component_id,
        window_start).

    Raises:
        ValueError: if window_seconds is not a positive integer.
        pydantic.ValidationError: if any ip_to_component value is not a valid
                                   ComponentId (forwarded from TelemetryPoint).
    """
    if window_seconds <= 0:
        raise ValueError(
            f"window_seconds must be a positive integer, got {window_seconds!r}"
        )
    if not records:
        return []

    buckets: dict[tuple[str, datetime], set[FlowRecord]] = defaultdict(set)

    for record in records:
        window_start = _floor_to_window(record.time_epoch, window_seconds)
        for ip in (record.src_ip, record.dst_ip):
            component = ip_to_component.get(ip)
            if component is not None:
                buckets[(component, window_start)].add(record)

    return [
        _compute_kpis(
            frozenset(bucket_records),
            component_id,
            window_start,
            window_seconds,
        )
        for (component_id, window_start), bucket_records in sorted(buckets.items())
    ]


def load_flow_csv(
    csv_path: str | Path,
    ip_to_component: dict[str, str],
    window_seconds: int = 30,
) -> list[TelemetryPoint]:
    """Read a tshark flow CSV and aggregate into per-component TelemetryPoint windows.

    Expects the CSV format written by testbed/capture.py:
        header row: frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len

    Malformed rows (missing fields, non-numeric values, empty IP addresses) are
    skipped silently — partial captures at the start or end of a tshark session
    commonly produce incomplete rows.  All valid rows are forwarded to
    aggregate_flows.

    Args:
        csv_path:         Path to the tshark capture CSV file.
        ip_to_component:  IP-address → component_id mapping (see aggregate_flows).
        window_seconds:   Aggregation window width in seconds (see aggregate_flows).

    Returns:
        list[TelemetryPoint] — same semantics as aggregate_flows.

    Raises:
        FileNotFoundError: if csv_path does not exist.
        ValueError:        if window_seconds ≤ 0.
    """
    resolved = Path(csv_path)
    if not resolved.exists():
        raise FileNotFoundError(f"flow CSV not found: {resolved}")

    records: list[FlowRecord] = []
    with resolved.open(encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            try:
                src_port_raw = row.get("tcp.srcport", "").strip()
                dst_port_raw = row.get("tcp.dstport", "").strip()
                records.append(
                    FlowRecord(
                        time_epoch=float(row["frame.time_epoch"]),
                        src_ip=row["ip.src"].strip(),
                        dst_ip=row["ip.dst"].strip(),
                        src_port=int(src_port_raw) if src_port_raw else 0,
                        dst_port=int(dst_port_raw) if dst_port_raw else 0,
                        frame_len=int(row["frame.len"]),
                    )
                )
            except (KeyError, ValueError):
                continue

    return aggregate_flows(records, ip_to_component, window_seconds)
