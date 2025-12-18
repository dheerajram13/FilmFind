"""
Tests for math utility functions.
"""

import math

import pytest

from app.utils.math_utils import clamp, log_normalize, normalize_to_range, sigmoid


class TestClamp:
    """Tests for clamp function."""

    def test_clamp_within_range(self):
        """Test value within range is unchanged."""
        assert clamp(0.5, 0.0, 1.0) == 0.5
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_clamp_above_max(self):
        """Test value above max is clamped to max."""
        assert clamp(1.5, 0.0, 1.0) == 1.0
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_clamp_below_min(self):
        """Test value below min is clamped to min."""
        assert clamp(-0.5, 0.0, 1.0) == 0.0
        assert clamp(-5.0, 0.0, 10.0) == 0.0

    def test_clamp_at_boundaries(self):
        """Test values exactly at boundaries."""
        assert clamp(0.0, 0.0, 1.0) == 0.0
        assert clamp(1.0, 0.0, 1.0) == 1.0

    def test_clamp_custom_range(self):
        """Test clamping with custom range."""
        assert clamp(5.0, 10.0, 20.0) == 10.0
        assert clamp(15.0, 10.0, 20.0) == 15.0
        assert clamp(25.0, 10.0, 20.0) == 20.0


class TestSigmoid:
    """Tests for sigmoid function."""

    def test_sigmoid_zero(self):
        """Test sigmoid(0) = 0.5."""
        assert sigmoid(0.0) == 0.5

    def test_sigmoid_positive(self):
        """Test sigmoid of positive values."""
        assert sigmoid(1.0) > 0.5
        assert sigmoid(10.0) > 0.9

    def test_sigmoid_negative(self):
        """Test sigmoid of negative values."""
        assert sigmoid(-1.0) < 0.5
        assert sigmoid(-10.0) < 0.1

    def test_sigmoid_large_positive(self):
        """Test sigmoid handles large positive values."""
        result = sigmoid(100.0)
        assert result == 1.0  # Should saturate at 1.0

    def test_sigmoid_large_negative(self):
        """Test sigmoid handles large negative values."""
        result = sigmoid(-100.0)
        assert result < 1e-40  # Should be very close to 0

    def test_sigmoid_range(self):
        """Test sigmoid output is in (0, 1)."""
        for x in [-100, -10, -1, 0, 1, 10, 100]:
            result = sigmoid(x)
            assert 0.0 <= result <= 1.0


class TestNormalizeToRange:
    """Tests for normalize_to_range function."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        # 5 is 50% of [0, 10], so should map to 50% of [0, 1] = 0.5
        assert normalize_to_range(5, 0, 10, 0, 1) == 0.5

    def test_normalize_to_different_range(self):
        """Test normalization to different output range."""
        # 50 is 50% of [0, 100], so should map to 50% of [0, 10] = 5.0
        assert normalize_to_range(50, 0, 100, 0, 10) == 5.0

    def test_normalize_at_boundaries(self):
        """Test normalization at input boundaries."""
        assert normalize_to_range(0, 0, 10, 0, 1) == 0.0
        assert normalize_to_range(10, 0, 10, 0, 1) == 1.0

    def test_normalize_negative_range(self):
        """Test normalization with negative ranges."""
        # 0 is 50% of [-10, 10], so should map to 50% of [0, 1] = 0.5
        assert normalize_to_range(0, -10, 10, 0, 1) == 0.5

    def test_normalize_zero_range(self):
        """Test normalization when old_min == old_max."""
        # Should return new_min when range is zero
        result = normalize_to_range(5, 10, 10, 0, 1)
        assert result == 0.0

    def test_normalize_clamps_output(self):
        """Test that output is clamped to target range."""
        # Input outside range should be clamped
        result = normalize_to_range(15, 0, 10, 0, 1)
        assert result == 1.0

        result = normalize_to_range(-5, 0, 10, 0, 1)
        assert result == 0.0


class TestLogNormalize:
    """Tests for log_normalize function."""

    def test_log_normalize_zero(self):
        """Test log normalization of zero."""
        assert log_normalize(0.0) == 0.0

    def test_log_normalize_negative(self):
        """Test log normalization of negative values."""
        assert log_normalize(-10.0) == 0.0

    def test_log_normalize_one(self):
        """Test log normalization of 1.0."""
        # log(1 + 1) / 7.0 = log(2) / 7.0 ≈ 0.099
        result = log_normalize(1.0)
        assert 0.0 < result < 0.2

    def test_log_normalize_large_value(self):
        """Test log normalization of large values."""
        # log(1001) / 7.0 ≈ 6.9 / 7.0 ≈ 0.98
        result = log_normalize(1000.0)
        assert 0.9 < result <= 1.0

    def test_log_normalize_output_range(self):
        """Test output is in [0, 1]."""
        for value in [0, 1, 10, 100, 1000, 10000]:
            result = log_normalize(value)
            assert 0.0 <= result <= 1.0

    def test_log_normalize_custom_base(self):
        """Test log normalization with custom base."""
        result_e = log_normalize(100.0, base=math.e)
        result_10 = log_normalize(100.0, base=10)
        # Different bases should give different results
        assert result_e != result_10

    def test_log_normalize_custom_max(self):
        """Test log normalization with custom max."""
        result_default = log_normalize(100.0)
        result_custom = log_normalize(100.0, max_log=10.0)
        # Larger max_log should give smaller result
        assert result_custom < result_default


class TestIntegration:
    """Integration tests combining multiple utilities."""

    def test_clamp_sigmoid_combination(self):
        """Test combining sigmoid with clamp."""
        # Sigmoid should already be in (0, 1), clamping shouldn't change it
        x = sigmoid(5.0)
        assert clamp(x, 0.0, 1.0) == x

    def test_normalize_then_clamp(self):
        """Test normalizing then clamping."""
        # Normalize value, then ensure it's clamped
        normalized = normalize_to_range(15, 0, 10, 0, 1)  # Would be > 1 without clamp
        assert normalized == 1.0

    def test_log_normalize_is_clamped(self):
        """Test that log_normalize output is always clamped."""
        # Very large value should clamp to 1.0
        result = log_normalize(1000000.0)
        assert result == 1.0
