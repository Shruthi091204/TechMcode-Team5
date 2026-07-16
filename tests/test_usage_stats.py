from rca.stats.store import read_usage_stats, record_analysis


def test_read_usage_stats_missing_file(tmp_path):
    stats_file = tmp_path / "absent.json"
    assert read_usage_stats(file_path=stats_file) == {"incidents_analyzed": 0, "nodes_analyzed": 0}


def test_record_analysis_accumulates(tmp_path):
    stats_file = tmp_path / "usage_stats.json"
    assert record_analysis(30, file_path=stats_file) == {"incidents_analyzed": 1, "nodes_analyzed": 30}
    assert record_analysis(12, file_path=stats_file) == {"incidents_analyzed": 2, "nodes_analyzed": 42}
    assert read_usage_stats(file_path=stats_file) == {"incidents_analyzed": 2, "nodes_analyzed": 42}


def test_record_analysis_ignores_negative_node_count(tmp_path):
    stats_file = tmp_path / "usage_stats.json"
    assert record_analysis(-5, file_path=stats_file) == {"incidents_analyzed": 1, "nodes_analyzed": 0}


def test_read_usage_stats_recovers_from_corrupt_file(tmp_path):
    stats_file = tmp_path / "usage_stats.json"
    stats_file.write_text("{not valid json", encoding="utf-8")
    assert read_usage_stats(file_path=stats_file) == {"incidents_analyzed": 0, "nodes_analyzed": 0}
