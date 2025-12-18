"""
Math utility functions for scoring and normalization.

Provides common mathematical operations used across scoring modules:
- Clamping values to ranges
- Sigmoid function
- Score normalization
"""

import math


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """
    Clamp value to range [min_value, max_value].

    Args:
        value: Value to clamp
        min_value: Minimum allowed value (default: 0.0)
        max_value: Maximum allowed value (default: 1.0)

    Returns:
        Clamped value

    Examples:
        >>> clamp(1.5, 0.0, 1.0)
        1.0
        >>> clamp(-0.5, 0.0, 1.0)
        0.0
        >>> clamp(0.5, 0.0, 1.0)
        0.5
    """
    return max(min_value, min(max_value, value))


def sigmoid(x: float) -> float:
    """
    Sigmoid function: 1 / (1 + e^-x).

    Maps any real number to range (0, 1).
    Handles overflow gracefully.

    Args:
        x: Input value

    Returns:
        Sigmoid of x in range (0, 1)

    Examples:
        >>> sigmoid(0)
        0.5
        >>> sigmoid(100)  # Large positive
        1.0
        >>> sigmoid(-100)  # Large negative
        0.0
    """
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        # For very large negative x, exp(-x) overflows to inf
        # In this case, sigmoid approaches 0
        return 0.0 if x < 0 else 1.0


def normalize_to_range(
    value: float,
    old_min: float,
    old_max: float,
    new_min: float = 0.0,
    new_max: float = 1.0,
) -> float:
    """
    Normalize value from one range to another using linear scaling.

    Args:
        value: Value to normalize
        old_min: Minimum of original range
        old_max: Maximum of original range
        new_min: Minimum of target range (default: 0.0)
        new_max: Maximum of target range (default: 1.0)

    Returns:
        Normalized value in [new_min, new_max]

    Examples:
        >>> normalize_to_range(5, 0, 10, 0, 1)
        0.5
        >>> normalize_to_range(50, 0, 100, 0, 10)
        5.0
    """
    if old_max == old_min:
        # Avoid division by zero
        return new_min

    # Linear scaling
    normalized = ((value - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min

    # Clamp to target range
    return clamp(normalized, new_min, new_max)


def log_normalize(value: float, base: float = math.e, max_log: float = 7.0) -> float:
    """
    Normalize value using logarithmic scaling.

    Useful for compressing wide ranges (e.g., popularity scores).

    Args:
        value: Value to normalize (must be >= 0)
        base: Logarithm base (default: e for natural log)
        max_log: Maximum log value for normalization (default: 7.0)

    Returns:
        Log-normalized value in [0.0, 1.0]

    Examples:
        >>> log_normalize(1.0)  # log(1+1) / 7.0
        0.099...
        >>> log_normalize(100.0)
        0.664...
    """
    if value <= 0:
        return 0.0

    log_value = math.log(value + 1, base)
    return clamp(log_value / max_log, 0.0, 1.0)
