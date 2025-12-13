"""
LLM client for interacting with Groq API and Ollama.

Provides a unified interface for LLM inference with support for:
- Groq API (free tier: 30 req/min)
- Ollama (local, unlimited)
- Automatic fallback and retry logic
"""

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.services.exceptions import (
    LLMClientError,
    LLMInvalidResponseError,
    LLMRateLimitError,
)
from app.utils.json_utils import safe_json_parse
from app.utils.retry import retry_with_backoff


class LLMClient:
    """
    Unified LLM client supporting Groq and Ollama.

    Provides methods for:
    - Generating completions
    - Structured JSON output
    - Retry logic and fallback
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialize LLM client.

        Args:
            provider: LLM provider ('groq' or 'ollama'). Defaults to settings.LLM_PROVIDER
            api_key: API key for Groq (required for Groq)
            base_url: Base URL for API (optional, uses defaults)
            model: Model name (optional, uses defaults)
            timeout: Request timeout in seconds
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.timeout = timeout

        if self.provider == "groq":
            self.api_key = api_key or settings.GROQ_API_KEY
            self.base_url = base_url or "https://api.groq.com/openai/v1"
            self.model = model or settings.GROQ_MODEL
            if not self.api_key:
                msg = "Groq API key is required"
                raise LLMClientError(msg)
        elif self.provider == "ollama":
            self.api_key = None
            self.base_url = base_url or settings.OLLAMA_BASE_URL
            self.model = model or settings.OLLAMA_MODEL
        else:
            msg = f"Unsupported provider: {self.provider}"
            raise LLMClientError(msg)

        logger.info(f"Initialized LLM client: provider={self.provider}, model={self.model}")

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate completion from LLM.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Response format (for structured output)

        Returns:
            Generated text completion

        Raises:
            LLMClientError: If request fails
            LLMRateLimitError: If rate limit is hit
        """
        # Don't retry rate limit errors - they should be handled at app level
        try:
            if self.provider == "groq":
                return self._groq_completion_with_retry(
                    prompt, system_prompt, temperature, max_tokens, response_format
                )
            if self.provider == "ollama":
                return self._ollama_completion_with_retry(
                    prompt, system_prompt, temperature, max_tokens
                )
            msg = f"Unsupported provider: {self.provider}"
            raise LLMClientError(msg)
        except LLMRateLimitError:
            # Don't retry rate limits - re-raise immediately
            raise

    @retry_with_backoff(max_retries=2, initial_delay=1.0, exceptions=(LLMClientError,))
    def _groq_completion_with_retry(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> str:
        """Wrapper with retry logic"""
        return self._groq_completion(
            prompt, system_prompt, temperature, max_tokens, response_format
        )

    def _groq_completion(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> str:
        """Generate completion using Groq API"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add response_format if provided (for JSON mode)
        if response_format:
            payload["response_format"] = response_format

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

                if response.status_code == 429:
                    logger.warning("Groq rate limit hit")
                    msg = "Rate limit exceeded for Groq API"
                    raise LLMRateLimitError(msg)

                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except LLMRateLimitError:
            # Re-raise rate limit errors without wrapping
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API error: {e.response.status_code} - {e.response.text}")
            msg = f"Groq API error: {e.response.status_code}"
            raise LLMClientError(msg) from e
        except httpx.TimeoutException as e:
            logger.error(f"Groq API timeout: {e}")
            msg = "Groq API request timed out"
            raise LLMClientError(msg) from e
        except LLMClientError:
            # Re-raise LLMClientError as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Groq: {e}")
            msg = f"Unexpected error: {e}"
            raise LLMClientError(msg) from e

    @retry_with_backoff(max_retries=2, initial_delay=1.0, exceptions=(LLMClientError,))
    def _ollama_completion_with_retry(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Wrapper with retry logic"""
        return self._ollama_completion(prompt, system_prompt, temperature, max_tokens)

    def _ollama_completion(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate completion using Ollama"""
        url = f"{self.base_url}/api/generate"

        # Combine system and user prompts
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "num_predict": max_tokens,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["response"]

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            msg = f"Ollama API error: {e.response.status_code}"
            raise LLMClientError(msg) from e
        except httpx.TimeoutException as e:
            logger.error(f"Ollama API timeout: {e}")
            msg = "Ollama API request timed out"
            raise LLMClientError(msg) from e
        except httpx.ConnectError as e:
            logger.error("Failed to connect to Ollama. Is Ollama running?")
            msg = "Cannot connect to Ollama. Ensure Ollama is running locally."
            raise LLMClientError(msg) from e
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            msg = f"Unexpected error: {e}"
            raise LLMClientError(msg) from e

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """
        Generate structured JSON output from LLM.

        Args:
            prompt: User prompt (should ask for JSON output)
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON as dictionary

        Raises:
            LLMClientError: If JSON parsing fails
        """
        # For Groq, we can use response_format
        response_format = {"type": "json_object"} if self.provider == "groq" else None

        # Add JSON instruction to prompt if not already present
        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nRespond with valid JSON only."

        completion = self.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        # Parse JSON using utility function
        try:
            return safe_json_parse(
                text=completion, extract_markdown=True, error_context=f"{self.provider} LLM"
            )
        except LLMInvalidResponseError:
            # Log the failed response for debugging
            logger.error(f"Failed to parse JSON from {self.provider} LLM\nResponse: {completion}")
            raise

    def __enter__(self) -> "LLMClient":
        """Context manager entry"""
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Context manager exit"""
