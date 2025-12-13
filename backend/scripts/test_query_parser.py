#!/usr/bin/env python
"""
CLI tool for testing the Query Parser (Module 2.1)

Usage:
    python scripts/test_query_parser.py "dark sci-fi movies like Interstellar"
    python scripts/test_query_parser.py --provider ollama "action movies from 2020"
    python scripts/test_query_parser.py --no-fallback "comedy tv shows"
"""

import argparse
import json
from pathlib import Path
import sys


# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.schemas.query import QueryParserConfig
from app.services.query_parser import QueryParser


def print_parsed_query(parsed, detailed: bool = False):
    """
    Pretty print the parsed query.

    Args:
        parsed: ParsedQuery object
        detailed: Whether to show detailed output
    """
    print("\n" + "=" * 80)
    print("PARSED QUERY RESULTS")
    print("=" * 80)

    # Basic Info
    print(f"\nRaw Query: {parsed.intent.raw_query}")
    print(f"Parsing Method: {parsed.parsing_method}")
    print(f"Confidence Score: {parsed.confidence_score:.2f}")

    # Intent
    print("\n--- INTENT ---")
    if parsed.intent.themes:
        print(f"Themes: {', '.join(parsed.intent.themes)}")
    if parsed.intent.tones:
        print(f"Tones: {', '.join(parsed.intent.tones)}")
    if parsed.intent.emotions:
        print(f"Emotions: {', '.join(parsed.intent.emotions)}")
    if parsed.intent.reference_titles:
        print(f"Reference Titles: {', '.join(parsed.intent.reference_titles)}")
    if parsed.intent.keywords:
        print(f"Keywords: {', '.join(parsed.intent.keywords)}")
    if parsed.intent.plot_elements:
        print(f"Plot Elements: {', '.join(parsed.intent.plot_elements)}")

    # Undesired elements
    if parsed.intent.undesired_themes or parsed.intent.undesired_tones:
        print("\n--- UNDESIRED ELEMENTS ---")
        if parsed.intent.undesired_themes:
            print(f"Themes to Avoid: {', '.join(parsed.intent.undesired_themes)}")
        if parsed.intent.undesired_tones:
            print(f"Tones to Avoid: {', '.join(parsed.intent.undesired_tones)}")

    # Constraints
    print("\n--- CONSTRAINTS ---")
    print(f"Media Type: {parsed.constraints.media_type}")
    if parsed.constraints.genres:
        print(f"Genres: {', '.join(parsed.constraints.genres)}")
    if parsed.constraints.exclude_genres:
        print(f"Exclude Genres: {', '.join(parsed.constraints.exclude_genres)}")
    if parsed.constraints.languages:
        print(f"Languages: {', '.join(parsed.constraints.languages)}")
    if parsed.constraints.year_min or parsed.constraints.year_max:
        year_range = (
            f"{parsed.constraints.year_min or 'Any'} - {parsed.constraints.year_max or 'Any'}"
        )
        print(f"Year Range: {year_range}")
    if parsed.constraints.rating_min:
        print(f"Min Rating: {parsed.constraints.rating_min}")
    if parsed.constraints.runtime_min or parsed.constraints.runtime_max:
        runtime_range = (
            f"{parsed.constraints.runtime_min or 'Any'} - "
            f"{parsed.constraints.runtime_max or 'Any'} minutes"
        )
        print(f"Runtime: {runtime_range}")
    if parsed.constraints.streaming_providers:
        print(f"Streaming: {', '.join(parsed.constraints.streaming_providers)}")

    # Context Flags
    print("\n--- CONTEXT FLAGS ---")
    print(f"Is Comparison Query: {parsed.intent.is_comparison_query}")
    print(f"Is Mood Query: {parsed.intent.is_mood_query}")

    # Search Text
    print("\n--- OPTIMIZED SEARCH TEXT ---")
    print(parsed.search_text)

    # Detailed JSON output
    if detailed:
        print("\n--- FULL JSON OUTPUT ---")
        print(json.dumps(parsed.model_dump(), indent=2, default=str))

    print("\n" + "=" * 80 + "\n")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Test the Query Parser with various queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with Groq (default)
  python scripts/test_query_parser.py "dark sci-fi movies like Interstellar"

  # Test with Ollama
  python scripts/test_query_parser.py --provider ollama "action movies from 2020"

  # Disable fallback (only use LLM)
  python scripts/test_query_parser.py --no-fallback "comedy tv shows"

  # Show detailed JSON output
  python scripts/test_query_parser.py --detailed "thriller movies"
        """,
    )

    parser.add_argument("query", type=str, help="Natural language query to parse")
    parser.add_argument(
        "--provider",
        type=str,
        choices=["groq", "ollama"],
        default="groq",
        help="LLM provider to use (default: groq)",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable rule-based fallback (LLM-only mode)",
    )
    parser.add_argument("--detailed", "-d", action="store_true", help="Show detailed JSON output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress info logging")

    args = parser.parse_args()

    # Configure logging
    if args.quiet:
        logger.remove()
        logger.add(sys.stderr, level="WARNING")

    # Create parser config
    config = QueryParserConfig(
        llm_provider=args.provider,
        enable_fallback=not args.no_fallback,
        max_retries=2,
        timeout=10,
    )

    # Parse the query
    try:
        with QueryParser(config=config) as query_parser:
            logger.info(f"Parsing query with provider: {args.provider}")
            parsed = query_parser.parse(args.query)
            print_parsed_query(parsed, detailed=args.detailed)

    except Exception as e:
        logger.error(f"Failed to parse query: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
