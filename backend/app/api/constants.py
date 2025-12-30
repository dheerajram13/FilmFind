"""
API-related constants.

Centralized constants for API configuration and behavior.
"""

# =============================================================================
# Search Configuration
# =============================================================================

# Minimum query length for search
MIN_QUERY_LENGTH = 3

# Retrieval multiplier for search (retrieve N times the limit for filtering)
RETRIEVAL_MULTIPLIER = 3

# Re-ranking multiplier (re-rank N times the limit)
RERANK_MULTIPLIER = 2

# Similar movies - add extra to account for self-reference
SIMILAR_MOVIES_BUFFER = 1
