"""
Tests for LLM Client

Tests cover:
- Groq API integration (mocked)
- Ollama integration (mocked)
- Error handling and retries
- JSON generation
"""

import json
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from app.services.exceptions import LLMClientError, LLMInvalidResponseError, LLMRateLimitError
from app.services.llm_client import LLMClient


# --- Fixtures ---


@pytest.fixture()
def groq_client():
    """Create Groq LLM client"""
    return LLMClient(provider="groq", api_key="test_api_key", model="llama-3.1-70b-versatile")


@pytest.fixture()
def ollama_client():
    """Create Ollama LLM client"""
    return LLMClient(provider="ollama", base_url="http://localhost:11434", model="llama3.2")


@pytest.fixture()
def mock_groq_response():
    """Mock successful Groq API response"""
    return {"choices": [{"message": {"content": "This is a test response"}}]}


@pytest.fixture()
def mock_groq_json_response():
    """Mock successful Groq API JSON response"""
    json_content = {"themes": ["action", "thriller"], "tones": ["dark"]}
    return {"choices": [{"message": {"content": json.dumps(json_content)}}]}


@pytest.fixture()
def mock_ollama_response():
    """Mock successful Ollama API response"""
    return {"response": "This is a test response from Ollama"}


# --- Initialization Tests ---


class TestLLMClientInit:
    """Test LLM client initialization"""

    def test_init_groq_with_api_key(self):
        """Test initializing Groq client with API key"""
        client = LLMClient(provider="groq", api_key="test_key")
        assert client.provider == "groq"
        assert client.api_key == "test_key"
        assert client.model == "llama-3.1-70b-versatile"

    def test_init_groq_without_api_key_raises(self):
        """Test initializing Groq without API key raises error"""
        with patch("app.services.llm_client.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "groq"
            mock_settings.GROQ_API_KEY = ""
            mock_settings.GROQ_MODEL = "llama-3.1-70b-versatile"

            with pytest.raises(LLMClientError, match="Groq API key is required"):
                LLMClient(provider="groq", api_key=None)

    def test_init_ollama(self):
        """Test initializing Ollama client"""
        client = LLMClient(provider="ollama")
        assert client.provider == "ollama"
        assert client.api_key is None
        assert client.base_url == "http://localhost:11434"

    def test_init_unsupported_provider(self):
        """Test initializing with unsupported provider raises error"""
        with pytest.raises(LLMClientError, match="Unsupported provider"):
            LLMClient(provider="invalid_provider")

    def test_init_custom_parameters(self):
        """Test initializing with custom parameters"""
        client = LLMClient(
            provider="groq",
            api_key="custom_key",
            base_url="https://custom.api.com",
            model="custom-model",
            timeout=60,
        )
        assert client.api_key == "custom_key"
        assert client.base_url == "https://custom.api.com"
        assert client.model == "custom-model"
        assert client.timeout == 60


# --- Groq API Tests ---


class TestGroqAPI:
    """Test Groq API interactions"""

    def test_groq_completion_success(self, groq_client, mock_groq_response):
        """Test successful Groq completion"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_groq_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = groq_client.generate_completion("Test prompt")
            assert result == "This is a test response"

    def test_groq_completion_with_system_prompt(self, groq_client, mock_groq_response):
        """Test Groq completion with system prompt"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_groq_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = groq_client.generate_completion(
                "Test prompt", system_prompt="You are a helpful assistant"
            )
            assert result == "This is a test response"

            # Verify system prompt was included in request
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert len(payload["messages"]) == 2
            assert payload["messages"][0]["role"] == "system"

    def test_groq_completion_rate_limit(self, groq_client):
        """Test Groq rate limit error"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 429
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(LLMRateLimitError, match="Rate limit exceeded"):
                groq_client.generate_completion("Test prompt")

    def test_groq_completion_http_error(self, groq_client):
        """Test Groq HTTP error handling"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            )
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(LLMClientError, match="Groq API error"):
                groq_client.generate_completion("Test prompt")

    def test_groq_completion_timeout(self, groq_client):
        """Test Groq timeout handling"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(LLMClientError, match="timed out"):
                groq_client.generate_completion("Test prompt")


# --- Ollama API Tests ---


class TestOllamaAPI:
    """Test Ollama API interactions"""

    def test_ollama_completion_success(self, ollama_client, mock_ollama_response):
        """Test successful Ollama completion"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = ollama_client.generate_completion("Test prompt")
            assert result == "This is a test response from Ollama"

    def test_ollama_completion_with_system_prompt(self, ollama_client, mock_ollama_response):
        """Test Ollama completion combines system and user prompts"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = ollama_client.generate_completion(
                "Test prompt", system_prompt="You are helpful"
            )
            assert result == "This is a test response from Ollama"

            # Verify prompts were combined
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert "You are helpful" in payload["prompt"]
            assert "Test prompt" in payload["prompt"]

    def test_ollama_connection_error(self, ollama_client):
        """Test Ollama connection error"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(LLMClientError, match="Cannot connect to Ollama"):
                ollama_client.generate_completion("Test prompt")

    def test_ollama_http_error(self, ollama_client):
        """Test Ollama HTTP error handling"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Model not found"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=mock_response
            )
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(LLMClientError, match="Ollama API error"):
                ollama_client.generate_completion("Test prompt")


# --- JSON Generation Tests ---


class TestJSONGeneration:
    """Test structured JSON generation"""

    def test_generate_json_success(self, groq_client, mock_groq_json_response):
        """Test successful JSON generation"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_groq_json_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = groq_client.generate_json("Generate JSON")
            assert isinstance(result, dict)
            assert "themes" in result
            assert result["themes"] == ["action", "thriller"]

    def test_generate_json_with_markdown_blocks(self, groq_client):
        """Test JSON extraction from markdown code blocks"""
        json_content = {"test": "value"}
        markdown_response = f"```json\n{json.dumps(json_content)}\n```"
        mock_response_data = {"choices": [{"message": {"content": markdown_response}}]}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = groq_client.generate_json("Generate JSON")
            assert result == json_content

    def test_generate_json_invalid_json(self, groq_client):
        """Test JSON parsing error handling"""
        mock_response_data = {"choices": [{"message": {"content": "This is not valid JSON"}}]}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(LLMInvalidResponseError, match="Invalid JSON response"):
                groq_client.generate_json("Generate JSON")

    def test_generate_json_adds_instruction(self, groq_client, mock_groq_json_response):
        """Test that JSON instruction is added to prompt"""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_groq_json_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            groq_client.generate_json("Simple prompt")

            # Verify "json" instruction was added
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            user_message = payload["messages"][-1]["content"]
            assert "json" in user_message.lower()


# --- Context Manager Tests ---


class TestContextManager:
    """Test LLM client as context manager"""

    def test_context_manager_groq(self):
        """Test Groq client as context manager"""
        with LLMClient(provider="groq", api_key="test_key") as client:
            assert client.provider == "groq"
            assert client.api_key == "test_key"

    def test_context_manager_ollama(self):
        """Test Ollama client as context manager"""
        with LLMClient(provider="ollama") as client:
            assert client.provider == "ollama"
            assert client.api_key is None
