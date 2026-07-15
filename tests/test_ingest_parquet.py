from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.rca.ingest.parquet_adapter import load_parquet

# ---------------------------------------------------------------------------
# Synthetic Parquet fixture helpers
# ---------------------------------------------------------------------------


def _write_parquet(tmp_path: Path, name: str, table: pa.Table) -> Path:
    file_path = tmp_path / name
    pq.write_table(table, str(file_path))
    return file_path


def _simple_table() -> pa.Table:
    return pa.table(
        {
            "duration": pa.array([0, 10, 5], type=pa.int64()),
            "src_bytes": pa.array([181, 0, 500], type=pa.int64()),
            "label": pa.array(["normal", "attack", "normal"], type=pa.string()),
        }
    )


def _numeric_table() -> pa.Table:
    return pa.table(
        {
            "a": pa.array([1.0, 4.0], type=pa.float64()),
            "b": pa.array([2.0, 5.0], type=pa.float64()),
            "c": pa.array([3.0, 6.0], type=pa.float64()),
        }
    )


def _nsbk15_mini_table() -> pa.Table:
    """Minimal table resembling UNSW-NB15 column structure."""
    return pa.table(
        {
            "srcip": pa.array(["149.171.126.0", "149.171.126.1"], type=pa.string()),
            "sport": pa.array([1040, 1041], type=pa.int64()),
            "dstip": pa.array(["149.171.126.9", "149.171.126.8"], type=pa.string()),
            "dsport": pa.array([80, 443], type=pa.int64()),
            "proto": pa.array(["tcp", "tcp"], type=pa.string()),
            "dur": pa.array([0.121478, 0.649902], type=pa.float64()),
            "sbytes": pa.array([232, 1384], type=pa.int64()),
            "dbytes": pa.array([8232, 5765], type=pa.int64()),
            "Sjit": pa.array([0.0, 83.1565], type=pa.float64()),
            "Djit": pa.array([0.0, 250.27], type=pa.float64()),
            "Label": pa.array([0, 1], type=pa.int64()),
            "attack_cat": pa.array(["Normal", "Backdoors"], type=pa.string()),
        }
    )


# ---------------------------------------------------------------------------
# FileNotFoundError
# ---------------------------------------------------------------------------


def test_missing_file_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_parquet(tmp_path / "nonexistent.parquet")


def test_missing_file_accepts_str_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_parquet(str(tmp_path / "missing.parquet"))


# ---------------------------------------------------------------------------
# ValueError on invalid / corrupt content
# ---------------------------------------------------------------------------


def test_non_parquet_file_raises_value_error(tmp_path: Path):
    bad = tmp_path / "not_parquet.parquet"
    bad.write_bytes(b"this is not a parquet file\x00\x01\x02")
    with pytest.raises(ValueError, match="failed to parse"):
        load_parquet(bad)


def test_empty_file_raises_value_error(tmp_path: Path):
    empty = tmp_path / "empty.parquet"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="failed to parse"):
        load_parquet(empty)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_returns_dataframe(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert isinstance(result, pd.DataFrame)


def test_accepts_path_object(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    assert isinstance(load_parquet(path), pd.DataFrame)


def test_accepts_str_path(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    assert isinstance(load_parquet(str(path)), pd.DataFrame)


# ---------------------------------------------------------------------------
# Row and column counts
# ---------------------------------------------------------------------------


def test_row_count_matches_table(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert len(result) == 3


def test_column_count_matches_schema(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert len(result.columns) == 3


def test_column_names_match_parquet_schema(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert list(result.columns) == ["duration", "src_bytes", "label"]


# ---------------------------------------------------------------------------
# Numeric dtype preservation
# ---------------------------------------------------------------------------


def test_integer_columns_preserved(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert pd.api.types.is_integer_dtype(result["duration"])
    assert pd.api.types.is_integer_dtype(result["src_bytes"])


def test_float_columns_preserved(tmp_path: Path):
    path = _write_parquet(tmp_path, "numeric.parquet", _numeric_table())
    result = load_parquet(path)
    for col in ["a", "b", "c"]:
        assert pd.api.types.is_float_dtype(result[col])


def test_float_values_are_correct(tmp_path: Path):
    path = _write_parquet(tmp_path, "numeric.parquet", _numeric_table())
    result = load_parquet(path)
    assert result["a"].tolist() == [1.0, 4.0]
    assert result["b"].tolist() == [2.0, 5.0]


# ---------------------------------------------------------------------------
# String column preservation
# ---------------------------------------------------------------------------


def test_string_columns_are_readable(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert pd.api.types.is_string_dtype(result["label"])


def test_string_values_are_correct(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert result["label"].tolist() == ["normal", "attack", "normal"]


# ---------------------------------------------------------------------------
# Numeric values round-trip correctly
# ---------------------------------------------------------------------------


def test_integer_values_are_correct(tmp_path: Path):
    path = _write_parquet(tmp_path, "simple.parquet", _simple_table())
    result = load_parquet(path)
    assert result["duration"].tolist() == [0, 10, 5]
    assert result["src_bytes"].tolist() == [181, 0, 500]


# ---------------------------------------------------------------------------
# Numeric-only table (no string columns)
# ---------------------------------------------------------------------------


def test_numeric_only_table(tmp_path: Path):
    path = _write_parquet(tmp_path, "numeric.parquet", _numeric_table())
    result = load_parquet(path)
    assert list(result.columns) == ["a", "b", "c"]
    assert len(result) == 2


# ---------------------------------------------------------------------------
# UNSW-NB15 mini fixture
# ---------------------------------------------------------------------------


def test_nswb15_mini_row_count(tmp_path: Path):
    path = _write_parquet(tmp_path, "nb15.parquet", _nsbk15_mini_table())
    result = load_parquet(path)
    assert len(result) == 2


def test_nb15_mini_has_label_column(tmp_path: Path):
    path = _write_parquet(tmp_path, "nb15.parquet", _nsbk15_mini_table())
    result = load_parquet(path)
    assert "Label" in result.columns


def test_nb15_mini_has_attack_cat_column(tmp_path: Path):
    path = _write_parquet(tmp_path, "nb15.parquet", _nsbk15_mini_table())
    result = load_parquet(path)
    assert "attack_cat" in result.columns


def test_nb15_mini_attack_cat_values(tmp_path: Path):
    path = _write_parquet(tmp_path, "nb15.parquet", _nsbk15_mini_table())
    result = load_parquet(path)
    assert result["attack_cat"].tolist() == ["Normal", "Backdoors"]


def test_nb15_mini_float_jitter_field(tmp_path: Path):
    path = _write_parquet(tmp_path, "nb15.parquet", _nsbk15_mini_table())
    result = load_parquet(path)
    assert pd.api.types.is_float_dtype(result["Sjit"])
    assert abs(result["Sjit"].iloc[1] - 83.1565) < 1e-4


def test_nb15_mini_label_binary(tmp_path: Path):
    path = _write_parquet(tmp_path, "nb15.parquet", _nsbk15_mini_table())
    result = load_parquet(path)
    assert result["Label"].tolist() == [0, 1]


# ---------------------------------------------------------------------------
# Large-ish synthetic table (performance sanity)
# ---------------------------------------------------------------------------


def test_large_table_loads_without_error(tmp_path: Path):
    n = 10_000
    large = pa.table(
        {
            "x": pa.array(list(range(n)), type=pa.float64()),
            "y": pa.array(list(range(n, 2 * n)), type=pa.float64()),
            "cat": pa.array(["a" if i % 2 == 0 else "b" for i in range(n)], type=pa.string()),
        }
    )
    path = _write_parquet(tmp_path, "large.parquet", large)
    result = load_parquet(path)
    assert len(result) == n
    assert list(result.columns) == ["x", "y", "cat"]
