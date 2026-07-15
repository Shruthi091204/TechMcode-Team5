from __future__ import annotations

import numpy as np
import pytest

from src.rca.detect.baseline import MadBaseline, compute_mad_scores

# ---------------------------------------------------------------------------
# Correctness — median and MAD values
# ---------------------------------------------------------------------------

def test_median_is_correct_for_odd_length_signal() -> None:
    # sorted: [1, 2, 3, 4, 5] → median = 3.0
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result.median == pytest.approx(3.0)


def test_mad_is_correct_for_odd_length_signal() -> None:
    # abs deviations from median 3: [2, 1, 0, 1, 2]
    # sorted deviations: [0, 1, 1, 2, 2] → MAD = 1.0
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result.mad == pytest.approx(1.0)


def test_median_is_correct_for_even_length_signal() -> None:
    # [1, 2, 3, 4] → median = 2.5
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0])
    assert result.median == pytest.approx(2.5)


def test_median_is_correct_for_single_observation() -> None:
    result = compute_mad_scores([42.0])
    assert result.median == pytest.approx(42.0)
    assert result.mad == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Scores — shape and non-negativity
# ---------------------------------------------------------------------------

def test_score_count_matches_input_length() -> None:
    signal = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = compute_mad_scores(signal)
    assert result.scores.shape == (len(signal),)


def test_scores_are_non_negative_for_normal_signal() -> None:
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 5.0, 50.0])
    assert (result.scores >= 0.0).all()


def test_scores_are_non_negative_for_signal_with_negatives() -> None:
    result = compute_mad_scores([-100.0, 2.0, 3.0, 4.0, 5.0])
    assert (result.scores >= 0.0).all()


# ---------------------------------------------------------------------------
# Scores — anomaly magnitude
# ---------------------------------------------------------------------------

def test_median_observation_scores_zero() -> None:
    # signal[2] = 3.0 = median; score must be 0.0
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result.scores[2] == pytest.approx(0.0)


def test_high_side_outlier_scores_higher_than_median_neighbour() -> None:
    # [1, 2, 3, 4, 100]: index 4 is the outlier
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 100.0])
    assert result.scores[4] > result.scores[2]


def test_low_side_outlier_scores_higher_than_median_neighbour() -> None:
    # [-100, 2, 3, 4, 5]: index 0 is the outlier
    result = compute_mad_scores([-100.0, 2.0, 3.0, 4.0, 5.0])
    assert result.scores[0] > result.scores[2]


def test_symmetric_outliers_score_equally() -> None:
    # [1, 2, 5, 8, 9]: median=5, deviations=[4,3,0,3,4], MAD=3
    # score[0]=|1-5|/3=1.33..., score[4]=|9-5|/3=1.33...
    result = compute_mad_scores([1.0, 2.0, 5.0, 8.0, 9.0])
    assert result.scores[0] == pytest.approx(result.scores[4])


def test_larger_deviation_scores_proportionally_higher() -> None:
    # [3, 5, 5, 5, 7, 100]: index 5 is a strong outlier
    # median=5, abs deviations=[2,0,0,0,2,95], MAD=1.0
    result = compute_mad_scores([3.0, 5.0, 5.0, 5.0, 7.0, 100.0])
    assert result.scores[5] > result.scores[0]


# ---------------------------------------------------------------------------
# Returns correct type
# ---------------------------------------------------------------------------

def test_returns_mad_baseline_instance() -> None:
    assert isinstance(compute_mad_scores([1.0, 2.0, 3.0]), MadBaseline)


def test_scores_field_is_numpy_array() -> None:
    result = compute_mad_scores([1.0, 2.0, 3.0])
    assert isinstance(result.scores, np.ndarray)


# ---------------------------------------------------------------------------
# Accepts both list and numpy array input
# ---------------------------------------------------------------------------

def test_accepts_python_list() -> None:
    result = compute_mad_scores([1.0, 2.0, 3.0])
    assert result.scores.shape == (3,)


def test_accepts_numpy_array() -> None:
    result = compute_mad_scores(np.array([1.0, 2.0, 3.0]))
    assert result.scores.shape == (3,)


def test_list_and_array_input_produce_identical_results() -> None:
    list_result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    array_result = compute_mad_scores(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert list_result.median == pytest.approx(array_result.median)
    assert list_result.mad == pytest.approx(array_result.mad)
    np.testing.assert_array_almost_equal(list_result.scores, array_result.scores)


# ---------------------------------------------------------------------------
# Zero-MAD handling — finite raw absolute deviation, no inf, no nan
# ---------------------------------------------------------------------------

def test_zero_mad_outlier_receives_raw_absolute_deviation_score() -> None:
    # [10, 10, 10, 10, 50]: MAD=0 → fallback score = |50 - 10| = 40.0
    result = compute_mad_scores([10.0, 10.0, 10.0, 10.0, 50.0])
    assert result.mad == pytest.approx(0.0)
    assert result.scores[4] == pytest.approx(40.0)


def test_zero_mad_baseline_points_score_zero() -> None:
    # Values at the median must score 0.0 (|10 - 10| = 0)
    result = compute_mad_scores([10.0, 10.0, 10.0, 10.0, 50.0])
    for i in range(4):
        assert result.scores[i] == pytest.approx(0.0)


def test_zero_mad_scores_contain_no_inf_values() -> None:
    # Downstream PELT and JSON serialisation require finite scores
    result = compute_mad_scores([10.0, 10.0, 10.0, 10.0, 50.0])
    assert np.all(np.isfinite(result.scores))


def test_zero_mad_scores_contain_no_nan_values() -> None:
    result = compute_mad_scores([10.0, 10.0, 10.0, 10.0, 50.0])
    assert not np.any(np.isnan(result.scores))


def test_uniform_signal_all_scores_zero() -> None:
    # [5, 5, 5, 5]: MAD=0, all at median → fallback |x - median| = 0 everywhere
    result = compute_mad_scores([5.0, 5.0, 5.0, 5.0])
    assert result.mad == pytest.approx(0.0)
    assert (result.scores == 0.0).all()


def test_all_scores_are_finite_for_normal_signal() -> None:
    # Positive guarantee: every score is finite when MAD > 0
    result = compute_mad_scores([1.0, 2.0, 3.0, 4.0, 5.0, 50.0])
    assert np.all(np.isfinite(result.scores))


# ---------------------------------------------------------------------------
# Input validation — error cases
# ---------------------------------------------------------------------------

def test_empty_signal_raises_value_error() -> None:
    with pytest.raises(ValueError, match="at least one observation"):
        compute_mad_scores([])


def test_two_dimensional_array_raises_value_error() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        compute_mad_scores(np.array([[1.0, 2.0], [3.0, 4.0]]))


def test_nan_raises_value_error() -> None:
    with pytest.raises(ValueError, match="NaN"):
        compute_mad_scores([1.0, float("nan"), 3.0])


def test_positive_inf_raises_value_error() -> None:
    with pytest.raises(ValueError, match="infinite"):
        compute_mad_scores([1.0, float("inf"), 3.0])


def test_negative_inf_raises_value_error() -> None:
    with pytest.raises(ValueError, match="infinite"):
        compute_mad_scores([1.0, float("-inf"), 3.0])


def test_empty_numpy_array_raises_value_error() -> None:
    with pytest.raises(ValueError, match="at least one observation"):
        compute_mad_scores(np.array([]))
