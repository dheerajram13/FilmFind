"""
Query interpretation utilities.

Provides DRY utilities for building query interpretation responses.
"""

from app.schemas.query import QueryConstraints, QueryIntent


def build_query_interpretation(
    query_intent: QueryIntent,
    validated_constraints: QueryConstraints,
) -> dict:
    """
    Build query interpretation dict for search response.

    Args:
        query_intent: Parsed query intent
        validated_constraints: Validated and normalized constraints

    Returns:
        Dictionary with query interpretation details
    """
    interpretation = {
        "semantic_query": query_intent.semantic_query,
        "intent": query_intent.intent_type.value if query_intent.intent_type else None,
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }

    # Add optional fields if present
    if query_intent.reference_titles:
        interpretation["reference_titles"] = query_intent.reference_titles
    if query_intent.genres:
        interpretation["genres"] = query_intent.genres
    if query_intent.tones:
        interpretation["tones"] = [t.value for t in query_intent.tones]
    if query_intent.emotions:
        interpretation["emotions"] = [e.value for e in query_intent.emotions]

    return interpretation


def build_empty_query_interpretation(
    query_intent: QueryIntent,
    validated_constraints: QueryConstraints,
) -> dict:
    """
    Build minimal query interpretation for empty results.

    Args:
        query_intent: Parsed query intent
        validated_constraints: Validated and normalized constraints

    Returns:
        Dictionary with minimal query interpretation details
    """
    return {
        "semantic_query": query_intent.semantic_query,
        "intent": query_intent.intent_type.value if query_intent.intent_type else None,
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }
