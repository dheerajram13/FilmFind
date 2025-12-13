"""
Query Understanding Service - Module 2.1

Parses natural language queries to extract:
- Intent (themes, tones, emotions, reference titles)
- Constraints (filters like language, year, genre)
- Optimized search text for embedding generation

Supports:
- LLM-based parsing (Groq/Ollama)
- Regex-based fallback for reliability
- Caching for performance
"""

import re

from loguru import logger

from app.schemas.query import (
    EmotionType,
    MediaType,
    ParsedQuery,
    QueryConstraints,
    QueryIntent,
    QueryParserConfig,
    ToneType,
)
from app.services.llm_client import LLMClient, LLMClientError


class QueryParser:
    """
    Main query parser that extracts intent and constraints from natural language.

    Uses LLM for deep understanding with regex-based pattern matching fallback for reliability.
    """

    def __init__(
        self, config: QueryParserConfig | None = None, llm_client: LLMClient | None = None
    ) -> None:
        """
        Initialize query parser.

        Args:
            config: Parser configuration (optional)
            llm_client: LLM client instance (optional, for dependency injection)
                       If not provided, a new client will be created from config
        """
        self.config = config or QueryParserConfig()
        self.llm_client = llm_client or LLMClient(
            provider=self.config.llm_provider, timeout=self.config.timeout
        )
        logger.info(f"Initialized QueryParser with provider: {self.config.llm_provider}")

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse natural language query into structured format.

        Args:
            query: Raw user query

        Returns:
            ParsedQuery with intent and constraints

        Raises:
            ValueError: If query is empty or invalid
        """
        if not query or not query.strip():
            msg = "Query cannot be empty"
            raise ValueError(msg)

        query = query.strip()
        logger.info(f"Parsing query: {query[:100]}...")

        # Try LLM-based parsing first
        try:
            parsed = self._parse_with_llm(query)
            logger.info(f"Successfully parsed query with LLM: {self.config.llm_provider}")
            return parsed
        except LLMClientError as e:
            logger.warning(f"LLM parsing failed: {e}")
            if not self.config.enable_fallback:
                raise

        # Fallback to regex-based parsing
        logger.info("Falling back to regex-based parsing")
        return self._parse_with_rules(query)

    def _parse_with_llm(self, query: str) -> ParsedQuery:
        """
        Parse query using LLM (Groq/Ollama).

        Args:
            query: User query

        Returns:
            ParsedQuery with extracted information
        """
        system_prompt = """You are an expert at understanding movie and TV show search queries.
Extract structured information from user queries including:
- Themes (e.g., "time travel", "revenge", "coming of age")
- Tones (dark, light, serious, comedic, intense, etc.)
- Emotions (joy, fear, sadness, awe, thrill, hope, romance, dark_tone)
- Reference titles (movies/shows mentioned)
- Constraints (language, year, genre, etc.)
- Undesired elements (things user wants to avoid or minimize)

CRITICAL: Pay careful attention to negative/exclusion patterns in the query.
Extract undesired elements by looking for:
1. "with less X" / "with fewer X" → extract X as undesired
2. "without X" / "with no X" → extract X as undesired
3. "no X" / "avoid X" / "not X" → extract X as undesired
4. "less X" / "fewer X" (standalone) → extract X as undesired
5. "minus the X" / "but without X" → extract X as undesired

Examples of undesired element extraction:
- "with less romance" → undesired_themes: ["romance"]
- "without violence" → undesired_themes: ["violence"]
- "no horror elements" → undesired_themes: ["horror", "horror elements"]
- "less dark tone" → undesired_tones: ["dark"]
- "avoid jump scares" → undesired_themes: ["jump scares"]
- "but without the comedy" → undesired_themes: ["comedy"]

When categorizing undesired elements:
- If it's a tone (dark, light, serious, comedic, etc.) → add to undesired_tones
- Otherwise → add to undesired_themes

Respond with valid JSON only."""

        user_prompt = f"""Parse this movie/TV show search query and extract information:

Query: "{query}"

Return a JSON object with this structure:
{{
  "themes": ["list of themes"],
  "tones": ["list of tones from: dark, light, serious, comedic, inspirational, intense, "
    "relaxing, suspenseful"],
  "emotions": ["list of emotions from: joy, fear, sadness, awe, thrill, hope, romance, dark_tone"],
  "reference_titles": ["movies/shows mentioned as references"],
  "keywords": ["important keywords"],
  "plot_elements": ["specific plot elements"],
  "undesired_themes": ["themes to avoid"],
  "undesired_tones": ["tones to avoid"],
  "is_comparison_query": true/false,
  "is_mood_query": true/false,
  "media_type": "movie" or "tv_show" or "both",
  "genres": ["list of genres"],
  "exclude_genres": ["genres to exclude"],
  "languages": ["list of language codes like 'en', 'hi', 'ko'"],
  "year_min": null or year,
  "year_max": null or year,
  "rating_min": null or rating (0-10),
  "runtime_min": null or minutes,
  "runtime_max": null or minutes,
  "streaming_providers": ["Netflix", "Prime Video", etc.],
  "popular_only": true/false,
  "hidden_gems": true/false,
  "search_text": "optimized text for semantic search"
}}

Examples:
1. Query: "dark sci-fi movies like Interstellar with less romance"
   - themes: ["space exploration", "science fiction", "time dilation"]
   - tones: ["dark", "serious"]
   - emotions: ["awe", "dark_tone"]
   - reference_titles: ["Interstellar"]
   - undesired_themes: ["romance"]  # "with less romance" indicates romance should be avoided
   - genres: ["Science Fiction"]
   - search_text: "dark science fiction space exploration time dilation cosmic themes"

2. Query: "lighthearted sitcoms like Friends about group of friends"
   - themes: ["friendship", "relationships", "comedy of life"]
   - tones: ["light", "comedic"]
   - emotions: ["joy", "hope"]
   - reference_titles: ["Friends"]
   - genres: ["Comedy"]
   - media_type: "tv_show"
   - search_text: "lighthearted sitcom friendship group friends comedy relationships"

3. Query: "Telugu action movies from 2020-2023 with high ratings"
   - themes: ["action", "heroism"]
   - languages: ["te"]
   - year_min: 2020
   - year_max: 2023
   - rating_min: 7.0
   - genres: ["Action"]
   - search_text: "action heroism intense fight sequences"

4. Query: "thriller without jump scares and no violence"
   - themes: ["suspense", "mystery"]
   - tones: ["suspenseful"]
   - emotions: ["thrill"]
   - undesired_themes: ["jump scares", "violence"]  # "without" and "no" indicate avoidance
   - genres: ["Thriller"]
   - search_text: "suspense mystery psychological thriller"

Now parse the query and respond with JSON only."""

        # Generate JSON response
        response_json = self.llm_client.generate_json(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=1024,
        )

        # Helper function to safely parse enum values
        def parse_enum_values(values: list[str], enum_class):
            """Parse list of strings to enum values, skipping invalid ones."""
            result = []
            for v in values:
                try:
                    result.append(enum_class(v))
                except ValueError:
                    logger.warning(f"Invalid {enum_class.__name__} value: {v}")
            return result

        # Build QueryIntent
        intent = QueryIntent(
            raw_query=query,
            themes=response_json.get("themes", []),
            tones=parse_enum_values(response_json.get("tones", []), ToneType),
            emotions=parse_enum_values(response_json.get("emotions", []), EmotionType),
            reference_titles=response_json.get("reference_titles", []),
            keywords=response_json.get("keywords", []),
            plot_elements=response_json.get("plot_elements", []),
            undesired_themes=response_json.get("undesired_themes", []),
            undesired_tones=parse_enum_values(response_json.get("undesired_tones", []), ToneType),
            is_comparison_query=response_json.get("is_comparison_query", False),
            is_mood_query=response_json.get("is_mood_query", False),
        )

        # Build QueryConstraints
        constraints = QueryConstraints(
            media_type=MediaType(response_json.get("media_type", "both")),
            genres=response_json.get("genres", []),
            exclude_genres=response_json.get("exclude_genres", []),
            languages=response_json.get("languages", []),
            year_min=response_json.get("year_min"),
            year_max=response_json.get("year_max"),
            rating_min=response_json.get("rating_min"),
            runtime_min=response_json.get("runtime_min"),
            runtime_max=response_json.get("runtime_max"),
            streaming_providers=response_json.get("streaming_providers", []),
            popular_only=response_json.get("popular_only", False),
            hidden_gems=response_json.get("hidden_gems", False),
        )

        # Get search text
        search_text = response_json.get("search_text", query)

        # Build ParsedQuery
        return ParsedQuery(
            intent=intent,
            constraints=constraints,
            search_text=search_text,
            confidence_score=0.9,  # High confidence for LLM parsing
            parsing_method="llm",
        )

    def _parse_with_rules(self, query: str) -> ParsedQuery:
        """
        Parse query using regex-based pattern matching (fallback).

        Args:
            query: User query

        Returns:
            ParsedQuery with basic extraction
        """
        query_lower = query.lower()

        # Extract reference titles (look for "like X" patterns)
        reference_titles = []
        # First, find the phrase after "like/similar to/such as"
        # Include "and" in the character class so it captures multiple titles
        like_pattern = (
            r"(?:like|similar to|such as)\s+"
            r"([A-Z][A-Za-z0-9\s:,and]+?)"
            r"(?:\s+(?:but|with|without|from|in|on|that)\s|\s*$)"
        )
        matches = re.findall(like_pattern, query, re.IGNORECASE)

        # Process each match to split on "and" or "," to handle multiple titles
        for match in matches:
            # Split by comma or " and " (with surrounding spaces)
            titles = re.split(r",\s*|\s+and\s+", match, flags=re.IGNORECASE)
            for title in titles:
                cleaned = title.strip()
                # Filter out very short titles and common stop words
                if cleaned and len(cleaned) > 1 and cleaned.lower() not in {"the", "a", "an"}:
                    reference_titles.append(cleaned)

        # Detect tones
        tones = []
        tone_keywords = {
            "dark": ToneType.DARK,
            "light": ToneType.LIGHT,
            "lighthearted": ToneType.LIGHT,
            "serious": ToneType.SERIOUS,
            "funny": ToneType.COMEDIC,
            "comedic": ToneType.COMEDIC,
            "comedy": ToneType.COMEDIC,
            "intense": ToneType.INTENSE,
            "suspenseful": ToneType.SUSPENSEFUL,
            "thriller": ToneType.SUSPENSEFUL,
        }
        for keyword, tone in tone_keywords.items():
            if keyword in query_lower:
                tones.append(tone)

        # Detect emotions
        emotions = []
        emotion_keywords = {
            "scary": EmotionType.FEAR,
            "horror": EmotionType.FEAR,
            "sad": EmotionType.SADNESS,
            "heartbreaking": EmotionType.SADNESS,
            "romantic": EmotionType.ROMANCE,
            "romance": EmotionType.ROMANCE,
            "thrilling": EmotionType.THRILL,
        }
        for keyword, emotion in emotion_keywords.items():
            if keyword in query_lower:
                emotions.append(emotion)

        # Detect media type
        media_type = MediaType.BOTH
        if "movie" in query_lower and "show" not in query_lower:
            media_type = MediaType.MOVIE
        elif ("show" in query_lower or "series" in query_lower) and "movie" not in query_lower:
            media_type = MediaType.TV_SHOW

        # Detect genres (basic keyword matching)
        genres = []
        genre_keywords = {
            "action": "Action",
            "comedy": "Comedy",
            "drama": "Drama",
            "horror": "Horror",
            "sci-fi": "Science Fiction",
            "science fiction": "Science Fiction",
            "thriller": "Thriller",
            "romance": "Romance",
            "fantasy": "Fantasy",
            "mystery": "Mystery",
            "crime": "Crime",
            "animation": "Animation",
            "documentary": "Documentary",
        }
        for keyword, genre in genre_keywords.items():
            if keyword in query_lower:
                genres.append(genre)

        # Detect year constraints
        year_min = None
        year_max = None
        year_pattern = r"(?:from|since|after)\s+(\d{4})"
        match = re.search(year_pattern, query_lower)
        if match:
            year_min = int(match.group(1))

        year_range_pattern = r"(\d{4})\s*-\s*(\d{4})"
        match = re.search(year_range_pattern, query)
        if match:
            year_min = int(match.group(1))
            year_max = int(match.group(2))

        # Detect undesired elements (look for "with less X", "without X", "no X", etc.)
        undesired_themes = []
        # Pattern captures multi-word phrases after negation markers
        undesired_patterns = [
            r"(?:with\s+)?(?:less|fewer)\s+([a-z\s]+?)(?:\s+(?:and|or|but|with|,)|$)",
            r"(?:with(?:out)?|avoid|minus)\s+(?:the\s+)?([a-z\s]+?)(?:\s+(?:and|or|but|with|,)|$)",
            r"\bno\s+([a-z\s]+?)(?:\s+(?:and|or|but|with|elements|scenes|,)|$)",
        ]
        for pattern in undesired_patterns:
            matches = re.findall(pattern, query_lower)
            undesired_themes.extend([m.strip() for m in matches if m.strip()])

        # Extract basic keywords (remove stop words)
        stop_words = {
            "like",
            "with",
            "without",
            "about",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "from",
            "to",
            "in",
        }
        words = re.findall(r"\b\w+\b", query_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 2][:10]

        # Build intent
        intent = QueryIntent(
            raw_query=query,
            themes=keywords[:5],  # Use top keywords as themes
            tones=tones,
            emotions=emotions,
            reference_titles=reference_titles,
            keywords=keywords,
            undesired_themes=undesired_themes,
            is_comparison_query=len(reference_titles) > 0,
            is_mood_query=len(emotions) > 0 or len(tones) > 0,
        )

        # Build constraints
        constraints = QueryConstraints(
            media_type=media_type,
            genres=genres,
            year_min=year_min,
            year_max=year_max,
        )

        # Build search text
        search_text = " ".join(keywords[:10])

        # Build ParsedQuery
        return ParsedQuery(
            intent=intent,
            constraints=constraints,
            search_text=search_text,
            confidence_score=0.5,  # Lower confidence for rule-based
            parsing_method="rule-based",
        )

    def __enter__(self) -> "QueryParser":
        """Context manager entry"""
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Context manager exit"""
