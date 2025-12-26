"""
String utility functions for text processing and normalization.

Provides common string operations used across the application:
- Case-insensitive normalization
- List deduplication and sorting
- Fuzzy matching
"""


def normalize_string(text: str) -> str:
    """
    Normalize a string for comparison (lowercase, trimmed).

    Args:
        text: String to normalize

    Returns:
        Normalized string (lowercase, no leading/trailing whitespace)

    Examples:
        >>> normalize_string("  Hello World  ")
        'hello world'
        >>> normalize_string("PYTHON")
        'python'
    """
    return text.lower().strip()


def normalize_string_list(items: list[str]) -> list[str]:
    """
    Normalize, deduplicate, and sort a list of strings.

    Args:
        items: List of strings to normalize

    Returns:
        Sorted list of unique normalized strings

    Examples:
        >>> normalize_string_list(["Python", "JAVA", "python", "  Go  "])
        ['go', 'java', 'python']
        >>> normalize_string_list([])
        []
    """
    return sorted({normalize_string(item) for item in items})


def case_insensitive_match(text: str, target: str) -> bool:
    """
    Check if two strings match (case-insensitive).

    Args:
        text: First string
        target: Second string

    Returns:
        True if strings match (case-insensitive), False otherwise

    Examples:
        >>> case_insensitive_match("Hello", "hello")
        True
        >>> case_insensitive_match("World", "earth")
        False
    """
    return normalize_string(text) == normalize_string(target)


def case_insensitive_in(text: str, items: list[str]) -> bool:
    """
    Check if a string is in a list (case-insensitive).

    Args:
        text: String to search for
        items: List of strings to search in

    Returns:
        True if text is in items (case-insensitive), False otherwise

    Examples:
        >>> case_insensitive_in("Python", ["java", "PYTHON", "Go"])
        True
        >>> case_insensitive_in("Rust", ["java", "python", "go"])
        False
    """
    normalized_text = normalize_string(text)
    normalized_items = {normalize_string(item) for item in items}
    return normalized_text in normalized_items
