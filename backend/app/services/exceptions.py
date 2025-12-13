"""
Custom exceptions for FilmFind services.

This module defines a hierarchy of exceptions for better error handling,
debugging, and client code clarity. All service exceptions inherit from
FilmFindServiceError for easy catching of all service-level errors.

Design Pattern: Exception Hierarchy Pattern
- Base exception for all service errors
- Specific exceptions for different error scenarios
- Preserves exception chaining with 'from' clause
"""


class FilmFindServiceError(Exception):
    """Base exception for all FilmFind service errors."""


# ============================================================================
# Vector Search Exceptions
# ============================================================================


class VectorSearchError(FilmFindServiceError):
    """Base exception for vector search service errors."""


class IndexNotFoundError(VectorSearchError):
    """
    Raised when FAISS index files are not found on disk.

    This typically occurs when trying to load an index that hasn't been
    built yet, or when the index files have been moved or deleted.
    """


class IndexNotInitializedError(VectorSearchError):
    """
    Raised when attempting to use an uninitialized index.

    This occurs when trying to search without first building or loading
    an index.
    """


class IndexBuildError(VectorSearchError):
    """
    Raised when FAISS index building or loading fails.

    This can occur due to:
    - Corrupted index files
    - Incompatible FAISS versions
    - Memory allocation failures
    - I/O errors
    """


class IndexValidationError(VectorSearchError):
    """
    Raised when index or query validation fails.

    Common scenarios:
    - Mismatched embedding dimensions
    - Mismatched number of embeddings and IDs
    - Invalid index parameters
    - Dimension incompatibility
    """


class SearchError(VectorSearchError):
    """
    Raised when a search operation fails.

    This is a catch-all for unexpected errors during search operations
    that don't fit other specific categories.
    """


# ============================================================================
# Embedding Service Exceptions
# ============================================================================


class EmbeddingError(FilmFindServiceError):
    """Base exception for embedding service errors."""


class EmbeddingGenerationError(EmbeddingError):
    """
    Raised when embedding generation fails.

    This can occur due to:
    - Model inference failures
    - GPU/CPU memory issues
    - Invalid model outputs
    """


class EmbeddingModelLoadError(EmbeddingError):
    """
    Raised when loading the sentence transformer model fails.

    Common causes:
    - Model not found or not downloaded
    - Insufficient disk space
    - Corrupted model files
    - Version incompatibilities
    """


class InvalidTextError(EmbeddingError):
    """
    Raised when input text is invalid for embedding generation.

    Examples:
    - Empty or None text
    - Text exceeding model's max sequence length
    - Invalid characters or encoding
    """


# ============================================================================
# Repository Exceptions
# ============================================================================


class RepositoryError(FilmFindServiceError):
    """Base exception for repository/database errors."""


class EntityNotFoundError(RepositoryError):
    """
    Raised when a requested entity is not found in the database.

    This exception includes the entity type and ID for better debugging.
    """

    def __init__(self, entity_type: str, entity_id: int | str):
        """
        Initialize with entity information.

        Args:
            entity_type: Type of entity (e.g., "Movie", "Genre")
            entity_id: ID of the entity that wasn't found
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with ID {entity_id} not found")


class DatabaseConnectionError(RepositoryError):
    """
    Raised when database connection fails.

    This can occur during:
    - Initial connection
    - Connection pool exhaustion
    - Network issues
    """


# ============================================================================
# Text Processing Exceptions
# ============================================================================


class TextProcessingError(FilmFindServiceError):
    """Base exception for text preprocessing errors."""


class PreprocessingError(TextProcessingError):
    """
    Raised when text preprocessing fails.

    This can occur due to:
    - Missing required fields (title, plot)
    - Encoding issues
    - Invalid characters
    """


# ============================================================================
# Batch Processing Exceptions
# ============================================================================


class BatchProcessingError(FilmFindServiceError):
    """
    Raised when batch processing fails.

    This can occur during:
    - Batch embedding generation
    - Batch database updates
    - Data validation
    """

    def __init__(self, message: str, batch_size: int = 0, failed_items: int = 0):
        """
        Initialize with batch information.

        Args:
            message: Error description
            batch_size: Total number of items in batch
            failed_items: Number of items that failed
        """
        self.batch_size = batch_size
        self.failed_items = failed_items
        super().__init__(message)


# ============================================================================
# LLM Service Exceptions
# ============================================================================


class LLMError(FilmFindServiceError):
    """
    Base exception for all LLM service errors.

    Exception Hierarchy:
    - LLMError (base)
      ├── LLMRetriableError (can be retried)
      │   ├── LLMClientError (HTTP errors, timeouts, etc.)
      │   └── LLMInvalidResponseError (malformed JSON)
      └── LLMNonRetriableError (should NOT be retried)
          └── LLMRateLimitError (HTTP 429)

    Design Pattern:
    The retry decorator should only catch LLMRetriableError and its subclasses.
    LLMNonRetriableError and its subclasses will propagate immediately.
    """


class LLMRetriableError(LLMError):
    """
    Base class for LLM errors that can be retried.

    These errors are typically transient and may succeed on retry:
    - Network errors
    - Temporary server errors (5xx)
    - Timeouts
    - Malformed responses (might be LLM hallucination)
    """


class LLMNonRetriableError(LLMError):
    """
    Base class for LLM errors that should NOT be retried.

    These errors will not be resolved by retrying:
    - Rate limits (need backoff at application level)
    - Authentication errors
    - Invalid API keys
    """


class LLMClientError(LLMRetriableError):
    """
    Exception for retriable LLM client errors.

    Raised when LLM API calls fail due to:
    - HTTP errors (5xx server errors)
    - Connection errors
    - Timeout errors
    - Unexpected provider errors

    Note: This exception is caught by retry logic and will be retried
    with exponential backoff.
    """


class LLMRateLimitError(LLMNonRetriableError):
    """
    Exception for rate limit errors (HTTP 429).

    Raised when LLM API rate limits are exceeded.
    This exception is NOT caught by retry logic and will propagate
    immediately to the caller.

    Rationale: Retrying rate-limited requests will just hit the same
    limit. The application should implement proper backoff or queuing
    at a higher level.

    Example handling:
        try:
            result = llm_client.generate_completion(prompt)
        except LLMRateLimitError:
            # Wait before retrying at application level
            time.sleep(60)
            result = llm_client.generate_completion(prompt)
    """


class LLMInvalidResponseError(LLMRetriableError):
    """
    Exception for invalid or malformed LLM responses.

    Raised when:
    - Response JSON is invalid
    - Response structure doesn't match expected format
    - Required fields are missing

    Note: Classified as retriable because:
    1. LLMs can occasionally hallucinate malformed JSON
    2. Retrying with a lower temperature might help
    3. The error might be transient

    However, if retries consistently fail, the prompt may need adjustment.
    """
