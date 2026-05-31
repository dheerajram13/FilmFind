"""
Parser consistency check — runs a fixed set of queries through QueryParser
3x each and reports field variance and confidence scores.

Usage:
    docker compose exec backend python scripts/utils/check_parser_consistency.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.query_parser import QueryParser

QUERIES = [
    "dark sci-fi movies like Interstellar with less romance",
    "lighthearted comedies like Friends about a group of friends",
    "Telugu action movies from 2020-2023 with high ratings",
    "thriller without jump scares and no violence",
    "animated movies for kids that are not too scary",
    "Korean drama series about love and loss",
    "90s crime movies like Pulp Fiction",
    "feel-good movies to watch on a rainy Sunday",
    "psychological horror with a twist ending",
    "documentaries about climate change",
    "superhero movies without too much CGI",
    "classic black and white films",
    "movies about AI and robots",
    "romantic comedies set in New York",
    "action movies with strong female leads",
]

RUNS = 3


def parse_n_times(parser: QueryParser, query: str, n: int) -> list[dict]:
    results = []
    for _ in range(n):
        try:
            parsed = parser.parse(query)
            results.append({
                "method": parsed.parsing_method,
                "confidence": round(parsed.confidence_score, 3),
                "themes": sorted(parsed.intent.themes),
                "tones": sorted([t.value if hasattr(t, "value") else str(t) for t in parsed.intent.tones]),
                "genres": sorted(parsed.constraints.genres),
                "search_text": parsed.search_text,
            })
        except Exception as e:
            results.append({"error": str(e)})
    return results


def field_variance(runs: list[dict], field: str) -> bool:
    """Returns True if the field value differs across runs."""
    values = [json.dumps(r.get(field), sort_keys=True) for r in runs if "error" not in r]
    return len(set(values)) > 1


def main() -> None:
    parser = QueryParser()
    print(f"\n{'='*70}")
    print(f"Parser Consistency Check — {RUNS} runs per query, {len(QUERIES)} queries")
    print(f"{'='*70}\n")

    total_variance = 0
    total_checks = 0

    for query in QUERIES:
        runs = parse_n_times(parser, query, RUNS)
        errors = [r for r in runs if "error" in r]
        good_runs = [r for r in runs if "error" not in r]

        method = good_runs[0]["method"] if good_runs else "error"
        confidences = [r["confidence"] for r in good_runs]
        mean_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0

        varied_fields = []
        for field in ("themes", "tones", "genres", "search_text"):
            if field_variance(good_runs, field):
                varied_fields.append(field)
                total_variance += 1
            total_checks += 1

        status = "STABLE" if not varied_fields else f"VARIES: {', '.join(varied_fields)}"
        error_note = f" [{len(errors)} error(s)]" if errors else ""
        print(f"  [{method:10s}] conf={mean_conf:.3f}  {status}{error_note}")
        print(f"  Query: {query[:60]}")
        if varied_fields:
            for field in varied_fields:
                vals = [json.dumps(r.get(field)) for r in good_runs]
                print(f"    {field}:")
                for i, v in enumerate(vals):
                    print(f"      run {i+1}: {v}")
        print()

    print(f"{'='*70}")
    print(f"Summary: {total_variance}/{total_checks} field checks varied across runs")
    print(f"Stability: {round((1 - total_variance/total_checks)*100, 1)}%")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
