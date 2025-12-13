"""
Tests for JSON utility functions.

Tests cover:
- Markdown extraction with various formats
- Multiple code blocks handling
- Edge cases and error handling
"""

import pytest

from app.services.exceptions import LLMInvalidResponseError
from app.utils.json_utils import (
    extract_json_from_markdown,
    safe_json_parse,
    validate_json_fields,
)


class TestExtractJsonFromMarkdown:
    """Test markdown JSON extraction"""

    def test_extract_from_json_code_block(self):
        """Test extracting from ```json block"""
        text = '```json\n{"key": "value"}\n```'
        result = extract_json_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_from_plain_code_block(self):
        """Test extracting from ``` block without language"""
        text = '```\n{"key": "value"}\n```'
        result = extract_json_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_plain_json(self):
        """Test with plain JSON (no markdown)"""
        text = '{"key": "value"}'
        result = extract_json_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_with_surrounding_text(self):
        """Test extraction with surrounding text"""
        text = 'Here is the JSON:\n```json\n{"key": "value"}\n```\nEnd of response'
        result = extract_json_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_first_block_only(self):
        """Test that only first code block is extracted"""
        text = '```json\n{"a": 1}\n```\nSome text\n```json\n{"b": 2}\n```'
        result = extract_json_from_markdown(text)
        assert result == '{"a": 1}'

    def test_extract_with_language_identifier(self):
        """Test extraction from block with language identifier"""
        text = '```python\n{"key": "value"}\n```'
        result = extract_json_from_markdown(text)
        # Should still extract the content
        assert '{"key": "value"}' in result or result == '{"key": "value"}'

    def test_extract_multiline_json(self):
        """Test extracting multiline JSON"""
        text = """```json
{
  "key1": "value1",
  "key2": "value2"
}
```"""
        result = extract_json_from_markdown(text)
        assert "key1" in result
        assert "key2" in result

    def test_extract_with_whitespace(self):
        """Test extraction handles whitespace correctly"""
        text = '  ```json  \n  {"key": "value"}  \n  ```  '
        result = extract_json_from_markdown(text)
        assert result.strip() == '{"key": "value"}'


class TestSafeJsonParse:
    """Test safe JSON parsing"""

    def test_parse_valid_json(self):
        """Test parsing valid JSON"""
        result = safe_json_parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_from_markdown(self):
        """Test parsing JSON from markdown block"""
        result = safe_json_parse('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_without_markdown_extraction(self):
        """Test parsing with markdown extraction disabled"""
        result = safe_json_parse('{"key": "value"}', extract_markdown=False)
        assert result == {"key": "value"}

    def test_parse_invalid_json_raises(self):
        """Test that invalid JSON raises LLMInvalidResponseError"""
        with pytest.raises(LLMInvalidResponseError, match="Invalid JSON response"):
            safe_json_parse("This is not JSON")

    def test_parse_with_error_context(self):
        """Test error message includes context"""
        with pytest.raises(LLMInvalidResponseError, match="test context"):
            safe_json_parse("invalid", error_context="test context")

    def test_parse_complex_json(self):
        """Test parsing complex nested JSON"""
        json_str = '{"nested": {"key": "value"}, "array": [1, 2, 3]}'
        result = safe_json_parse(json_str)
        assert result == {"nested": {"key": "value"}, "array": [1, 2, 3]}

    def test_parse_json_array(self):
        """Test parsing JSON array"""
        result = safe_json_parse("[1, 2, 3, 4]")
        assert result == [1, 2, 3, 4]


class TestValidateJsonFields:
    """Test JSON field validation"""

    def test_validate_all_fields_present(self):
        """Test validation passes when all fields present"""
        data = {"name": "John", "age": 30, "city": "NYC"}
        validate_json_fields(data, ["name", "age"])
        # Should not raise

    def test_validate_missing_field_raises(self):
        """Test validation raises when field missing"""
        data = {"name": "John"}
        with pytest.raises(LLMInvalidResponseError, match="Missing required fields: age"):
            validate_json_fields(data, ["name", "age"])

    def test_validate_multiple_missing_fields(self):
        """Test error message lists all missing fields"""
        data = {"name": "John"}
        with pytest.raises(LLMInvalidResponseError, match="Missing required fields: age, city"):
            validate_json_fields(data, ["name", "age", "city"])

    def test_validate_empty_required_list(self):
        """Test validation with no required fields"""
        data = {"name": "John"}
        validate_json_fields(data, [])
        # Should not raise

    def test_validate_extra_fields_allowed(self):
        """Test that extra fields don't cause errors"""
        data = {"name": "John", "age": 30, "extra": "value"}
        validate_json_fields(data, ["name", "age"])
        # Should not raise


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    def test_empty_string(self):
        """Test handling empty string"""
        with pytest.raises(LLMInvalidResponseError):
            safe_json_parse("")

    def test_whitespace_only(self):
        """Test handling whitespace-only string"""
        with pytest.raises(LLMInvalidResponseError):
            safe_json_parse("   ")

    def test_malformed_markdown(self):
        """Test handling malformed markdown (unclosed block)"""
        text = '```json\n{"key": "value"}'
        result = extract_json_from_markdown(text)
        # Should return as-is since no closing marker
        assert result == text

    def test_nested_code_blocks(self):
        """Test handling nested/multiple code blocks"""
        text = '```json\n{"outer": "value"}\n```\nText\n```\n{"inner": "value"}\n```'
        result = extract_json_from_markdown(text)
        # Should extract first block only
        assert "outer" in result
        assert "inner" not in result
