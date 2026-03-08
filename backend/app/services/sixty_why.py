"""
60-Second Mode why-reasons generator.

Calls Gemini (via LLMClient) to produce 3 personalised bullet reasons
explaining why a film matches the user's mood/context/craving.
Falls back to generic reasons if the LLM call fails.
"""
import json
import re

from loguru import logger

from app.services.llm_client import LLMClient


_SYSTEM_PROMPT = (
    "You are a concise film recommendation assistant. "
    "Your job is to explain in exactly 3 short bullet points why a specific film "
    "perfectly matches a viewer's current mood and craving. "
    "Each bullet must be a single sentence (max 15 words). "
    "Respond ONLY with a JSON array of exactly 3 strings, e.g. "
    '[\"reason one\", \"reason two\", \"reason three\"]. No extra text.'
)


async def generate_why_reasons(
    film: object,
    mood_label: str,
    context_label: str,
    craving_label: str,
) -> list[str]:
    """
    Generate exactly 3 why-reasons for the given film and viewer state.

    Args:
        film: SQLAlchemy Media instance (needs .title, .overview, .genres).
        mood_label: e.g. "happy", "charged"
        context_label: e.g. "solo-night", "family"
        craving_label: e.g. "mind-blown", "laugh"

    Returns:
        List of exactly 3 strings.
    """
    try:
        genre_names = ", ".join(g.name for g in (getattr(film, "genres", None) or []))
        overview = getattr(film, "overview", "") or ""
        title = getattr(film, "title", "this film")
        narrative_dna = getattr(film, "narrative_dna", "") or ""
        tone_tags = getattr(film, "tone_tags", None) or []
        tone_str = ", ".join(tone_tags) if tone_tags else ""

        prompt = (
            f'Film: "{title}"\n'
            f"Genres: {genre_names or 'unknown'}\n"
            f"Overview: {overview[:300]}\n"
            f"Narrative DNA: {narrative_dna[:200]}\n"
            f"Tone: {tone_str or 'unknown'}\n\n"
            f"Viewer mood: {mood_label}\n"
            f"Watching context: {context_label}\n"
            f"Craving: {craving_label}\n\n"
            "Explain in exactly 3 short bullet points why this film is perfect right now."
        )

        client = LLMClient()
        raw = client.generate_completion(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=256,
            response_format={"type": "json_object"},
        )

        reasons = _parse_reasons(raw)
        if reasons:
            return reasons[:3]

    except Exception as exc:
        logger.warning(f"sixty_why LLM call failed: {exc}")

    # Fallback generic reasons
    return _fallback_reasons(mood_label, craving_label)


def _parse_reasons(raw: str) -> list[str]:
    """Try to extract a list of 3 strings from the LLM response."""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            strings = [str(s).strip() for s in data if str(s).strip()]
            return strings if strings else []
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: try regex to find a JSON array anywhere in the response
    match = re.search(r'\[.*?\]', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [str(s).strip() for s in data if str(s).strip()]
        except (json.JSONDecodeError, TypeError):
            pass

    return []


def _fallback_reasons(mood: str, craving: str) -> list[str]:
    """Generic fallback reasons when LLM is unavailable."""
    return [
        f"Perfectly matched to your {mood} mood right now",
        f"Delivers exactly the {craving} experience you're craving",
        "Consistently rated as a must-watch pick",
    ]
