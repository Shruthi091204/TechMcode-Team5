from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.io import arff


def load_arff(path: str | Path) -> pd.DataFrame:
    """Load an ARFF file and return its contents as a pandas DataFrame.

    Wraps ``scipy.io.arff.loadarff``, which handles both numeric and nominal
    (categorical) ARFF attributes.  Nominal attributes are stored as bytes by
    scipy; this function decodes them to ``str`` so downstream code does not
    need to know the internal scipy representation.

    Primary use-case: loading the NSL-KDD dataset (``KDDTrain+.arff``,
    ``KDDTest+.arff``) for the supervised anomaly-detection classifier in
    ``eval/run_eval.py``.  The raw feature columns and the ``label`` attribute
    are preserved without any transformation or normalisation — callers own the
    feature engineering.

    Args:
        path: Filesystem path to the ``.arff`` file.  Accepts ``str`` or
              ``pathlib.Path``.

    Returns:
        ``pd.DataFrame`` with one column per ARFF attribute and one row per
        data instance.  Column names match the ARFF ``@attribute`` names
        exactly.  Dtypes:

        - numeric attributes → ``float64``
        - nominal attributes → ``object`` (Python ``str``)

    Raises:
        FileNotFoundError: if *path* does not exist on the filesystem.
        ValueError: if *path* exists but is not a valid ARFF file (e.g.
                    malformed header or unsupported attribute type).
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"ARFF file not found: {resolved}")

    try:
        raw_data, _meta = arff.loadarff(str(resolved))
    except Exception as exc:
        raise ValueError(f"failed to parse ARFF file {resolved}: {exc}") from exc

    frame = pd.DataFrame(raw_data)
    for column in frame.columns:
        if frame[column].dtype == object:
            frame[column] = frame[column].str.decode("utf-8")

    return frame
