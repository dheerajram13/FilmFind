"""
Eval harness for QueryParser — runs a fixed query set and scores field accuracy.

Usage:
    docker compose exec backend python scripts/utils/run_eval.py
    docker compose exec backend python scripts/utils/run_eval.py --prompt-version 2
    docker compose exec backend python scripts/utils/run_eval.py --json

Scoring:
    Each field check is pass/partial/fail:
    - *_any fields: pass if any expected value appears in the parsed output (case-insensitive substring)
    - Scalar fields (year_min, year_max, rating_min, media_type): exact match
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.query_parser import QueryParser
from app.prompts import load_prompt


EVAL_PATH = Path(__file__).parent / "eval_queries.json"


def load_eval_set() -> list[dict]:
    return json.loads(EVAL_PATH.read_text())


def check_any(expected: list[str], actual: list[str]) -> bool:
    """Pass if any expected value is a substring of any actual value (case-insensitive)."""
    actual_joined = " ".join(actual).lower()
    return any(e.lower() in actual_joined for e in expected)


def score_case(parsed, case: dict) -> dict:
    """Score a single eval case. None means not checked (field not in case)."""
    results = {}

    intent = parsed.intent
    constraints = parsed.constraints

    for field, actual in [
        ("themes", intent.themes),
        ("tones", [t.value if hasattr(t, "value") else str(t) for t in intent.tones]),
        ("undesired_themes", intent.undesired_themes),
        ("reference_titles", intent.reference_titles),
        ("genres", constraints.genres),
        ("languages", constraints.languages),
    ]:
        key = f"expect_{field}_any"
        if key in case:
            expected = case[key]
            if not expected:
                results[field] = True
            else:
                results[field] = check_any(expected, actual)

    for field, actual in [
        ("year_min", constraints.year_min),
        ("year_max", constraints.year_max),
        ("rating_min", constraints.rating_min),
        ("media_type", constraints.media_type.value if hasattr(constraints.media_type, "value") else str(constraints.media_type)),
    ]:
        key = f"expect_{field}"
        if key in case:
            results[field] = (actual == case[key])

    return results


def run_eval(prompt_version: str = "1", output_json: bool = False) -> dict:
    cases = load_eval_set()

    try:
        system_prompt_override = load_prompt("query_parser", prompt_version)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    parser = QueryParser()
    original_parse = parser._parse_with_llm

    def patched_parse(query: str):
        original_gen = parser.llm_client.generate_json

        def gen_with_override(prompt, system_prompt=None, **kwargs):
            return original_gen(prompt, system_prompt=system_prompt_override, **kwargs)

        parser.llm_client.generate_json = gen_with_override
        try:
            result = original_parse(query)
        finally:
            parser.llm_client.generate_json = original_gen
        return result

    parser._parse_with_llm = patched_parse

    all_results = []
    field_totals: dict = {}
    field_passes: dict = {}

    if not output_json:
        print(f"\n{'='*70}")
        print(f"Eval run — prompt version: v{prompt_version} — {len(cases)} queries")
        print(f"{'='*70}\n")

    for case in cases:
        query = case["query"]
        try:
            parsed = parser.parse(query)
            method = parsed.parsing_method
            conf = round(parsed.confidence_score, 3)
            scores = score_case(parsed, case)
        except Exception as e:
            if not output_json:
                print(f"  ERROR: {query[:60]}\n    {e}\n")
            all_results.append({"query": query, "error": str(e)})
            continue

        passed = [f for f, v in scores.items() if v is True]
        failed = [f for f, v in scores.items() if v is False]

        for field, result in scores.items():
            field_totals[field] = field_totals.get(field, 0) + 1
            if result:
                field_passes[field] = field_passes.get(field, 0) + 1

        if not output_json:
            status = "PASS" if not failed else f"FAIL: {', '.join(failed)}"
            print(f"  [{method:10s}] conf={conf:.3f}  {status}")
            print(f"  Query: {query[:65]}")
            if failed:
                for f in failed:
                    expected_key = f"expect_{f}_any" if f"expect_{f}_any" in case else f"expect_{f}"
                    print(f"    {f}: expected {case.get(expected_key)}")
            print()

        all_results.append({
            "query": query,
            "method": method,
            "confidence": conf,
            "passed": passed,
            "failed": failed,
        })

    print(f"{'='*70}")
    print(f"Per-field accuracy (prompt v{prompt_version}):")
    for field in sorted(field_totals):
        p = field_passes.get(field, 0)
        t = field_totals[field]
        pct = round(p / t * 100, 1)
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        print(f"  {field:20s} [{bar}] {p}/{t} ({pct}%)")

    total_p = sum(field_passes.values())
    total_t = sum(field_totals.values())
    overall = round(total_p / total_t * 100, 1) if total_t else 0
    print(f"\n  Overall: {total_p}/{total_t} checks passed ({overall}%)")
    print(f"{'='*70}\n")

    summary = {
        "prompt_version": prompt_version,
        "total_queries": len(cases),
        "per_field": {f: {"pass": field_passes.get(f, 0), "total": field_totals[f]} for f in field_totals},
        "overall_pct": overall,
        "results": all_results,
    }

    if output_json:
        print(json.dumps(summary, indent=2))

    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Run QueryParser eval harness")
    ap.add_argument("--prompt-version", default="1", help="Prompt version to use (default: 1)")
    ap.add_argument("--json", action="store_true", dest="output_json", help="Output results as JSON")
    args = ap.parse_args()
    run_eval(prompt_version=args.prompt_version, output_json=args.output_json)


if __name__ == "__main__":
    main()
