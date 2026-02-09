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
        "raw_query": query_intent.raw_query,
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }

    # Add optional fields if present
    if query_intent.themes:
        interpretation["themes"] = query_intent.themes
    if query_intent.reference_titles:
        interpretation["reference_titles"] = query_intent.reference_titles
    if query_intent.keywords:
        interpretation["keywords"] = query_intent.keywords
    if query_intent.plot_elements:
        interpretation["plot_elements"] = query_intent.plot_elements
    if query_intent.tones:
        interpretation["tones"] = [str(t) for t in query_intent.tones]
    if query_intent.emotions:
        interpretation["emotions"] = [str(e) for e in query_intent.emotions]

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
        "raw_query": query_intent.raw_query,
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }
