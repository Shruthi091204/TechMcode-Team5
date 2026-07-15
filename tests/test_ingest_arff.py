from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.rca.ingest.arff_adapter import load_arff

# ---------------------------------------------------------------------------
# Minimal synthetic ARFF fixtures
# ---------------------------------------------------------------------------

_SIMPLE_ARFF = """\
@relation test_data

@attribute duration numeric
@attribute protocol_type {tcp,udp,icmp}
@attribute src_bytes numeric
@attribute label {normal,attack}

@data
0,tcp,181,normal
10,udp,0,attack
5,icmp,500,normal
"""

_NUMERIC_ONLY_ARFF = """\
@relation numeric_only

@attribute a numeric
@attribute b numeric
@attribute c numeric

@data
1.0,2.0,3.0
4.0,5.0,6.0
"""

_MISSING_DATA_ARFF = """\
@relation missing_vals

@attribute x numeric
@attribute y numeric

@data
1.0,2.0
?,4.0
3.0,?
"""

_NSLKDD_MINI_ARFF = """\
@relation NSL-KDD

@attribute duration numeric
@attribute protocol_type {tcp,udp,icmp}
@attribute service {http,ftp,smtp,ssh,domain,private,other}
@attribute flag {SF,S0,REJ,RSTO,RSTR,SH,OTH}
@attribute src_bytes numeric
@attribute dst_bytes numeric
@attribute label {normal,neptune,smurf,portsweep,back,teardrop,satan,nmap}
@attribute difficulty_level numeric

@data
0,tcp,http,SF,181,5450,normal,21
0,tcp,http,SF,239,486,normal,21
0,tcp,http,SF,235,1337,normal,21
2,tcp,smtp,SF,1228,13398,normal,15
0,tcp,private,S0,0,0,neptune,19
0,tcp,private,S0,0,0,neptune,19
"""


def _write_arff(tmp_path: Path, name: str, content: str) -> Path:
    file_path = tmp_path / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# FileNotFoundError
# ---------------------------------------------------------------------------


def test_missing_file_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_arff(tmp_path / "nonexistent.arff")


def test_missing_file_accepts_str_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_arff(str(tmp_path / "missing.arff"))


# ---------------------------------------------------------------------------
# ValueError on invalid content
# ---------------------------------------------------------------------------


def test_empty_file_raises_value_error(tmp_path: Path):
    empty = tmp_path / "empty.arff"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="failed to parse"):
        load_arff(empty)


def test_invalid_arff_content_raises_value_error(tmp_path: Path):
    bad = tmp_path / "bad.arff"
    bad.write_text("this is not arff content\njust random text\n", encoding="utf-8")
    with pytest.raises(ValueError, match="failed to parse"):
        load_arff(bad)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_returns_dataframe(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert isinstance(result, pd.DataFrame)


def test_accepts_path_object(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert isinstance(result, pd.DataFrame)


def test_accepts_str_path(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(str(path))
    assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# Row and column counts
# ---------------------------------------------------------------------------


def test_row_count_matches_data_section(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert len(result) == 3


def test_column_count_matches_attributes(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert len(result.columns) == 4


def test_column_names_match_arff_attributes(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert list(result.columns) == ["duration", "protocol_type", "src_bytes", "label"]


# ---------------------------------------------------------------------------
# Numeric dtype
# ---------------------------------------------------------------------------


def test_numeric_columns_are_float64(tmp_path: Path):
    path = _write_arff(tmp_path, "numeric.arff", _NUMERIC_ONLY_ARFF)
    result = load_arff(path)
    assert all(result[col].dtype == "float64" for col in result.columns)


def test_numeric_values_are_correct(tmp_path: Path):
    path = _write_arff(tmp_path, "numeric.arff", _NUMERIC_ONLY_ARFF)
    result = load_arff(path)
    assert result["a"].tolist() == [1.0, 4.0]
    assert result["b"].tolist() == [2.0, 5.0]


# ---------------------------------------------------------------------------
# Nominal (categorical) columns decoded to str
# ---------------------------------------------------------------------------


def test_nominal_columns_are_str_dtype(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert pd.api.types.is_string_dtype(result["protocol_type"])
    assert pd.api.types.is_string_dtype(result["label"])


def test_nominal_values_are_str_not_bytes(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    for val in result["protocol_type"]:
        assert isinstance(val, str), f"expected str, got {type(val)}"


def test_nominal_values_match_arff_data(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert result["protocol_type"].tolist() == ["tcp", "udp", "icmp"]
    assert result["label"].tolist() == ["normal", "attack", "normal"]


# ---------------------------------------------------------------------------
# Mixed numeric + nominal
# ---------------------------------------------------------------------------


def test_mixed_types_preserved(tmp_path: Path):
    path = _write_arff(tmp_path, "simple.arff", _SIMPLE_ARFF)
    result = load_arff(path)
    assert result["duration"].dtype == "float64"
    assert pd.api.types.is_string_dtype(result["protocol_type"])


# ---------------------------------------------------------------------------
# Missing values (ARFF uses '?' for missing)
# ---------------------------------------------------------------------------


def test_missing_values_load_as_nan(tmp_path: Path):
    path = _write_arff(tmp_path, "missing.arff", _MISSING_DATA_ARFF)
    result = load_arff(path)
    assert result.shape == (3, 2)
    assert pd.isna(result.loc[1, "x"])
    assert pd.isna(result.loc[2, "y"])


def test_non_missing_values_unaffected(tmp_path: Path):
    path = _write_arff(tmp_path, "missing.arff", _MISSING_DATA_ARFF)
    result = load_arff(path)
    assert result.loc[0, "x"] == 1.0
    assert result.loc[0, "y"] == 2.0


# ---------------------------------------------------------------------------
# Numeric-only ARFF (no nominal columns)
# ---------------------------------------------------------------------------


def test_numeric_only_arff_no_decode_error(tmp_path: Path):
    path = _write_arff(tmp_path, "numeric.arff", _NUMERIC_ONLY_ARFF)
    result = load_arff(path)
    assert list(result.columns) == ["a", "b", "c"]
    assert len(result) == 2


# ---------------------------------------------------------------------------
# NSL-KDD mini fixture
# ---------------------------------------------------------------------------


def test_nslkdd_mini_row_count(tmp_path: Path):
    path = _write_arff(tmp_path, "nsl_mini.arff", _NSLKDD_MINI_ARFF)
    result = load_arff(path)
    assert len(result) == 6


def test_nslkdd_mini_has_label_column(tmp_path: Path):
    path = _write_arff(tmp_path, "nsl_mini.arff", _NSLKDD_MINI_ARFF)
    result = load_arff(path)
    assert "label" in result.columns


def test_nslkdd_mini_label_is_str(tmp_path: Path):
    path = _write_arff(tmp_path, "nsl_mini.arff", _NSLKDD_MINI_ARFF)
    result = load_arff(path)
    assert all(isinstance(v, str) for v in result["label"])


def test_nslkdd_mini_label_values(tmp_path: Path):
    path = _write_arff(tmp_path, "nsl_mini.arff", _NSLKDD_MINI_ARFF)
    result = load_arff(path)
    labels = result["label"].tolist()
    assert labels == ["normal", "normal", "normal", "normal", "neptune", "neptune"]


def test_nslkdd_mini_numeric_field(tmp_path: Path):
    path = _write_arff(tmp_path, "nsl_mini.arff", _NSLKDD_MINI_ARFF)
    result = load_arff(path)
    assert result["src_bytes"].dtype == "float64"
    assert result["src_bytes"].iloc[0] == 181.0
