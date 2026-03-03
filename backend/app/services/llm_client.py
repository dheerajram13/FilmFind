"""
LLM client for interacting with Gemini, Groq API, and Ollama.

Provides a unified interface for LLM inference with support for:
- Google Gemini (primary, free tier: 15 RPM / 1500 RPD)
- Groq API (fallback, free tier: 30 req/min)
- Ollama (local, unlimited)
- Automatic provider chain fallback and retry logic
"""

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.services.exceptions import (
    LLMClientError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMRetriableError,
)
from app.utils.json_utils import safe_json_parse
from app.utils.retry import retry_with_backoff


class LLMClient:
    """
    Unified LLM client supporting Gemini, Groq, and Ollama.

    Automatically tries providers in order (primary → fallback) until one succeeds.
    Default chain when primary="gemini": gemini → groq.

    Provides methods for:
    - Generating completions
    - Structured JSON output
    - Automatic provider chain fallback
    - Per-provider retry logic
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
            provider: Primary LLM provider ('gemini', 'groq', or 'ollama').
                      Defaults to settings.LLM_PROVIDER
            api_key: API key override for the primary provider
            base_url: Base URL override (applies to Groq/Ollama only)
            model: Model name override for the primary provider
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._api_key_override = api_key
        self._base_url_override = base_url
        self._model_override = model

        requested = provider or settings.LLM_PROVIDER
        self._provider_chain = self._build_provider_chain(requested)
        # Keep self.provider as the first valid provider for logging/backward compat
        self.provider = self._provider_chain[0]

        logger.info(
            f"Initialized LLM client: primary={self.provider}, "
            f"chain={self._provider_chain}"
        )

    def _build_provider_chain(self, primary: str) -> list[str]:
        """
        Build the ordered list of providers to try, skipping any without credentials.

        When primary is 'gemini': chain is [gemini, groq] (if keys available).
        When primary is 'groq': chain is [groq].
        When primary is 'ollama': chain is [ollama].
        """
        chain: list[str] = []

        if primary == "gemini":
            gemini_key = self._api_key_override or settings.GEMINI_API_KEY
            if gemini_key:
                chain.append("gemini")
            else:
                logger.warning("GEMINI_API_KEY not set — skipping Gemini provider")
            # Always add Groq as fallback if key exists
            if settings.GROQ_API_KEY:
                chain.append("groq")
            elif not chain:
                pass  # Will raise below if chain is empty
        elif primary == "groq":
            groq_key = self._api_key_override or settings.GROQ_API_KEY
            if groq_key:
                chain.append("groq")
            else:
                logger.warning("GROQ_API_KEY not set — skipping Groq provider")
        elif primary == "ollama":
            chain.append("ollama")
        else:
            msg = f"Unsupported provider: {primary}"
            raise LLMClientError(msg)

        if not chain:
            msg = "No LLM providers configured with valid credentials. Set GEMINI_API_KEY or GROQ_API_KEY."
            raise LLMClientError(msg)

        return chain

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate completion from LLM, trying providers in chain order.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Response format hint ({"type": "json_object"} for JSON mode)

        Returns:
            Generated text completion

        Raises:
            LLMClientError: If all providers in the chain fail
        """
        use_json_mode = response_format is not None and response_format.get("type") == "json_object"
        last_error: Exception | None = None

        for provider in self._provider_chain:
            try:
                logger.debug(f"Trying LLM provider: {provider}")

                if provider == "gemini":
                    result = self._gemini_completion_with_retry(
                        prompt, system_prompt, temperature, max_tokens, use_json_mode
                    )
                elif provider == "groq":
                    result = self._groq_completion_with_retry(
                        prompt, system_prompt, temperature, max_tokens,
                        {"type": "json_object"} if use_json_mode else None,
                    )
                elif provider == "ollama":
                    result = self._ollama_completion_with_retry(
                        prompt, system_prompt, temperature, max_tokens
                    )
                else:
                    continue

                logger.info(f"LLM call succeeded with provider: {provider}")
                return result

            except Exception as e:
                logger.warning(
                    f"LLM provider '{provider}' failed: {e}. "
                    f"{'Trying next provider...' if provider != self._provider_chain[-1] else 'No more providers.'}"
                )
                last_error = e
                continue

        msg = f"All LLM providers failed. Last error: {last_error}"
        raise LLMClientError(msg) from last_error

    # -------------------------------------------------------------------------
    # Gemini
    # -------------------------------------------------------------------------

    @retry_with_backoff(max_retries=2, initial_delay=1.0, exceptions=(LLMRetriableError,))
    def _gemini_completion_with_retry(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        use_json_mode: bool,
    ) -> str:
        """Wrapper with retry logic for Gemini completions."""
        return self._gemini_completion(
            prompt, system_prompt, temperature, max_tokens, use_json_mode
        )

    def _gemini_completion(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        use_json_mode: bool,
    ) -> str:
        """Generate completion using Google Gemini API (google-genai SDK)."""
        try:
            from google import genai  # lazy import
            from google.genai import types as genai_types
        except ImportError as e:
            msg = "google-genai package not installed. Run: pip install google-genai>=1.0.0"
            raise LLMClientError(msg) from e

        api_key = self._api_key_override or settings.GEMINI_API_KEY
        model_name = self._model_override or settings.GEMINI_MODEL

        try:
            client = genai.Client(api_key=api_key)

            config = genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json" if use_json_mode else "text/plain",
                system_instruction=system_prompt,
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            if not response.text:
                msg = "Gemini returned empty response (possibly blocked by safety filters)"
                raise LLMClientError(msg)

            return response.text

        except LLMClientError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            # Detect rate limit / quota errors
            if "429" in str(e) or "quota" in error_str or ("rate" in error_str and "limit" in error_str):
                logger.warning(f"Gemini rate limit hit: {e}")
                msg = "Rate limit exceeded for Gemini API"
                raise LLMRateLimitError(msg) from e
            logger.error(f"Gemini API error: {e}")
            msg = f"Gemini API error: {e}"
            raise LLMClientError(msg) from e

    # -------------------------------------------------------------------------
    # Groq
    # -------------------------------------------------------------------------

    @retry_with_backoff(max_retries=2, initial_delay=1.0, exceptions=(LLMRetriableError,))
    def _groq_completion_with_retry(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> str:
        """
        Wrapper with retry logic for Groq completions.

        Only catches LLMRetriableError (LLMClientError, LLMInvalidResponseError).
        LLMRateLimitError inherits from LLMNonRetriableError and will propagate.
        """
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
        api_key = self._api_key_override or settings.GROQ_API_KEY
        base_url = self._base_url_override or "https://api.groq.com/openai/v1"
        model = self._model_override or settings.GROQ_MODEL

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

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
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Groq: {e}")
            msg = f"Unexpected error: {e}"
            raise LLMClientError(msg) from e

    # -------------------------------------------------------------------------
    # Ollama
    # -------------------------------------------------------------------------

    @retry_with_backoff(max_retries=2, initial_delay=1.0, exceptions=(LLMRetriableError,))
    def _ollama_completion_with_retry(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Wrapper with retry logic for Ollama completions.

        Only catches LLMRetriableError (LLMClientError, LLMInvalidResponseError).
        LLMRateLimitError inherits from LLMNonRetriableError and will propagate.
        """
        return self._ollama_completion(prompt, system_prompt, temperature, max_tokens)

    def _ollama_completion(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate completion using Ollama"""
        base_url = self._base_url_override or settings.OLLAMA_BASE_URL
        model = self._model_override or settings.OLLAMA_MODEL
        url = f"{base_url}/api/generate"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": model,
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

    # -------------------------------------------------------------------------
    # JSON helper
    # -------------------------------------------------------------------------

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """
        Generate structured JSON output from LLM.

        Enables JSON mode for providers that support it (Gemini, Groq).

        Args:
            prompt: User prompt (should ask for JSON output)
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON as dictionary

        Raises:
            LLMClientError: If all providers fail or JSON parsing fails
        """
        # Signal JSON mode — each provider interprets this in its own way
        response_format = {"type": "json_object"}

        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nRespond with valid JSON only."

        completion = self.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        try:
            return safe_json_parse(
                text=completion, extract_markdown=True, error_context=f"{self.provider} LLM"
            )
        except LLMInvalidResponseError:
            logger.error(f"Failed to parse JSON from LLM\nResponse: {completion}")
            raise

    def __enter__(self) -> "LLMClient":
        """Context manager entry"""
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Context manager exit"""
