"""
JSON utility functions for parsing and extracting JSON data.

Provides helpers for:
- Extracting JSON from markdown code blocks
- Safe JSON parsing with error handling
- LLM response JSON extraction
"""

import json
from typing import Any

from app.services.exceptions import LLMInvalidResponseError


def extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON string from markdown code blocks.

    Handles common LLM response formats:
    - ```json ... ```
    - ``` ... ```
    - Plain JSON text

    Args:
        text: Text potentially containing JSON in markdown blocks

    Returns:
        Extracted JSON string

    Examples:
        >>> extract_json_from_markdown('```json\\n{"key": "value"}\\n```')
        '{"key": "value"}'
        >>> extract_json_from_markdown('{"key": "value"}')
        '{"key": "value"}'
    """
    text = text.strip()

    # Try extracting from ```json blocks (first occurrence only)
    if "```json" in text:
        try:
            # Find the first ```json block
            start_marker = "```json"
            end_marker = "```"
            start_idx = text.find(start_marker) + len(start_marker)
            end_idx = text.find(end_marker, start_idx)

            if end_idx != -1:
                return text[start_idx:end_idx].strip()
        except (ValueError, IndexError):
            pass  # Fall through to next method

    # Try extracting from ``` blocks (first occurrence only)
    if "```" in text:
        try:
            # Find the first ``` block
            marker = "```"
            start_idx = text.find(marker) + len(marker)
            # Skip the language identifier if present (e.g., ```python)
            newline_idx = text.find("\n", start_idx)
            if newline_idx != -1 and newline_idx - start_idx < 20:
                start_idx = newline_idx + 1

            end_idx = text.find(marker, start_idx)
            if end_idx != -1:
                return text[start_idx:end_idx].strip()
        except (ValueError, IndexError):
            pass  # Fall through to plain text

    # Return as-is (assume plain JSON)
    return text


def safe_json_parse(
    text: str, extract_markdown: bool = True, error_context: str = ""
) -> dict[str, Any]:
    """
    Safely parse JSON with markdown extraction and error handling.

    Args:
        text: JSON text to parse
        extract_markdown: Whether to extract from markdown blocks first
        error_context: Additional context for error messages

    Returns:
        Parsed JSON as dictionary

    Raises:
        LLMInvalidResponseError: If JSON parsing fails

    Examples:
        >>> safe_json_parse('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_parse('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
    """
    try:
        # Extract from markdown if requested
        json_str = extract_json_from_markdown(text) if extract_markdown else text.strip()

        # Parse JSON
        return json.loads(json_str)

    except json.JSONDecodeError as e:
        error_msg = "Invalid JSON response"
        if error_context:
            error_msg += f" ({error_context})"
        error_msg += f": {e}"
        raise LLMInvalidResponseError(error_msg) from e
    except Exception as e:
        error_msg = "Unexpected error parsing JSON"
        if error_context:
            error_msg += f" ({error_context})"
        error_msg += f": {e}"
        raise LLMInvalidResponseError(error_msg) from e


def validate_json_fields(data: dict[str, Any], required_fields: list[str]) -> None:
    """
    Validate that required fields exist in JSON data.

    Args:
        data: JSON data dictionary
        required_fields: List of required field names

    Raises:
        LLMInvalidResponseError: If required fields are missing

    Examples:
        >>> validate_json_fields({"name": "John", "age": 30}, ["name", "age"])
        >>> validate_json_fields({"name": "John"}, ["name", "age"])
        Traceback (most recent call last):
            ...
        LLMInvalidResponseError: Missing required fields: age
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        msg = f"Missing required fields: {', '.join(missing_fields)}"
        raise LLMInvalidResponseError(msg)
