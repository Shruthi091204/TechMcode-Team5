from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_parquet(path: str | Path) -> pd.DataFrame:
    """Load a Parquet file and return its contents as a pandas DataFrame.

    Wraps ``pandas.read_parquet``, which delegates to the PyArrow engine by
    default.  All columns and dtypes declared in the Parquet schema are
    preserved without any transformation or normalisation — callers own the
    feature engineering.

    Primary use-case: loading the UNSW-NB15 dataset
    (``UNSW_NB15_training-set.parquet``, ``UNSW_NB15_testing-set.parquet``)
    for the supervised anomaly-detection classifier in ``eval/run_eval.py``.
    The 49 raw feature columns and the ``Label`` / ``attack_cat`` attributes
    are returned as-is so the classifier can apply its own preprocessing.

    Args:
        path: Filesystem path to the ``.parquet`` file.  Accepts ``str`` or
              ``pathlib.Path``.

    Returns:
        ``pd.DataFrame`` with one column per Parquet field and one row per
        data record.  Column names and dtypes match the Parquet schema
        exactly:

        - integer / float columns → their declared numeric dtype
        - string / categorical columns → ``object`` or ``pd.StringDtype``

    Raises:
        FileNotFoundError: if *path* does not exist on the filesystem.
        ValueError: if *path* exists but cannot be parsed as a valid Parquet
                    file (e.g. corrupted footer or unsupported encoding).
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Parquet file not found: {resolved}")

    try:
        return pd.read_parquet(resolved, engine="pyarrow")
    except Exception as exc:
        raise ValueError(f"failed to parse Parquet file {resolved}: {exc}") from exc
