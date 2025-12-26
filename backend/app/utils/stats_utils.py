"""
Statistical utility functions for data analysis.

Provides common statistical operations:
- Median calculation
- Percentile calculation
- Basic statistics
"""

from collections.abc import Sequence


def calculate_median(values: Sequence[float]) -> float:
    """
    Calculate the median of a sequence of numbers.

    Args:
        values: Sequence of numeric values

    Returns:
        Median value

    Raises:
        ValueError: If values is empty

    Examples:
        >>> calculate_median([1, 2, 3, 4, 5])
        3.0
        >>> calculate_median([1, 2, 3, 4])
        2.5
        >>> calculate_median([5, 1, 3, 2, 4])
        3.0
    """
    if not values:
        msg = "Cannot calculate median of empty sequence"
        raise ValueError(msg)

    sorted_values = sorted(values)
    n = len(sorted_values)

    if n % 2 == 1:
        # Odd number of elements - return middle element
        return float(sorted_values[n // 2])

    # Even number of elements - return average of two middle elements
    mid1 = sorted_values[n // 2 - 1]
    mid2 = sorted_values[n // 2]
    return (mid1 + mid2) / 2.0


def calculate_percentile(values: Sequence[float], percentile: float) -> float:
    """
    Calculate the specified percentile of a sequence of numbers.

    Args:
        values: Sequence of numeric values
        percentile: Percentile to calculate (0-100)

    Returns:
        Value at the specified percentile

    Raises:
        ValueError: If values is empty or percentile is out of range

    Examples:
        >>> calculate_percentile([1, 2, 3, 4, 5], 50)
        3.0
        >>> calculate_percentile([1, 2, 3, 4, 5], 75)
        4.0
        >>> calculate_percentile([1, 2, 3, 4, 5], 25)
        2.0
    """
    if not values:
        msg = "Cannot calculate percentile of empty sequence"
        raise ValueError(msg)

    if not 0 <= percentile <= 100:
        msg = f"Percentile must be between 0 and 100, got {percentile}"
        raise ValueError(msg)

    sorted_values = sorted(values)
    n = len(sorted_values)

    # Calculate index (using linear interpolation method)
    index = (percentile / 100) * (n - 1)

    if index.is_integer():
        return float(sorted_values[int(index)])

    # Interpolate between two values
    lower_index = int(index)
    upper_index = lower_index + 1
    weight = index - lower_index
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


def calculate_mean(values: Sequence[float]) -> float:
    """
    Calculate the arithmetic mean of a sequence of numbers.

    Args:
        values: Sequence of numeric values

    Returns:
        Mean value

    Raises:
        ValueError: If values is empty

    Examples:
        >>> calculate_mean([1, 2, 3, 4, 5])
        3.0
        >>> calculate_mean([10, 20, 30])
        20.0
    """
    if not values:
        msg = "Cannot calculate mean of empty sequence"
        raise ValueError(msg)

    return sum(values) / len(values)
