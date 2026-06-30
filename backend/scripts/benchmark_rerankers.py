"""
Cross-encoder reranker benchmark for FilmFind.

Compares LLM reranker alternatives on movie search quality and latency.

Models tested:
  - cross-encoder/ms-marco-MiniLM-L-6-v2   (MiniLM, fast)
  - cross-encoder/ms-marco-MiniLM-L-12-v2  (MiniLM, accurate)
  - BAAI/bge-reranker-v2-m3                (BGE multilingual)
  - mixedbread-ai/mxbai-rerank-base-v1     (mxbai base)
  - mixedbread-ai/mxbai-rerank-large-v1    (mxbai large)
  - FlashRank ms-marco-TinyBERT-L-2-v2     (ultra-fast)
  - FlashRank ms-marco-MiniLM-L-12-v2      (FlashRank wrapper)

Setup — rebuild the backend image once to pick up flashrank + updated sentence-transformers:
  docker compose up --build backend -d

Usage (run inside the backend container):
  docker compose exec backend python scripts/benchmark_rerankers.py
  docker compose exec backend python scripts/benchmark_rerankers.py --models minilm-l6 bge
  docker compose exec backend python scripts/benchmark_rerankers.py --top-k 5

Available model keys: minilm-l6, minilm-l12, bge, mxbai-base, mxbai-large, flashrank-tiny, flashrank-mini
"""

from __future__ import annotations

import argparse
import math
import shutil
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
_FLASHRANK_CACHE = Path.home() / ".cache" / "flashrank"


def _clear_model_cache() -> None:
    """Delete downloaded model files to free disk between runs."""
    for cache_dir in (_HF_CACHE, _FLASHRANK_CACHE):
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
            print(f"    cleared {cache_dir}")

# ─── Evaluation dataset ──────────────────────────────────────────────────────
# Relevance labels: 2 = highly relevant, 1 = somewhat relevant, 0 = irrelevant

TEST_CASES: list[dict[str, Any]] = [
    {
        "query": "emotional drama about grief and family healing",
        "candidates": [
            {"title": "Manchester by the Sea",      "overview": "A depressed uncle must take care of his teenage nephew after the boy's father dies, forcing him to confront his tragic past.",                         "relevance": 2},
            {"title": "Ordinary People",            "overview": "The accidental drowning of one son tears a family apart, as the surviving son struggles with guilt and his mother's resentment.",                     "relevance": 2},
            {"title": "The Descendants",            "overview": "A land baron tries to reconnect with his daughters after his wife is left in a coma, uncovering a family secret along the way.",                     "relevance": 2},
            {"title": "Steel Magnolias",            "overview": "Close-knit women in a small Louisiana town share bonds of friendship and support each other through personal tragedies and loss.",                    "relevance": 2},
            {"title": "Marriage Story",             "overview": "A couple goes through a painful coast-to-coast divorce, forcing both to reexamine what they truly want from life.",                                 "relevance": 1},
            {"title": "Requiem for a Dream",        "overview": "Parallel stories of people whose lives are destroyed by drug addiction and obsessive desire.",                                                      "relevance": 1},
            {"title": "A Beautiful Mind",           "overview": "A mathematical genius struggles with schizophrenia while his devoted wife stands by him through his treatment.",                                    "relevance": 1},
            {"title": "Mad Max: Fury Road",         "overview": "In a post-apocalyptic wasteland, a woman rebels against a tyrannical ruler with the help of a drifter.",                                          "relevance": 0},
            {"title": "The Avengers",               "overview": "Earth's mightiest heroes are assembled to stop a powerful alien invasion led by the god of mischief.",                                             "relevance": 0},
            {"title": "Die Hard",                   "overview": "An off-duty cop uses his wits to save hostages taken by terrorists in a Los Angeles skyscraper on Christmas Eve.",                                "relevance": 0},
        ],
    },
    {
        "query": "mind-bending sci-fi with stunning visuals and complex plot",
        "candidates": [
            {"title": "Inception",          "overview": "A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO.",               "relevance": 2},
            {"title": "Interstellar",       "overview": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth becomes uninhabitable.",                       "relevance": 2},
            {"title": "2001: A Space Odyssey", "overview": "A mysterious black monolith influences human evolution and a space mission to Jupiter where the ship's AI turns dangerous.",                            "relevance": 2},
            {"title": "The Matrix",         "overview": "A computer hacker discovers reality is a simulation and joins a rebellion to fight the machine overlords who control humanity.",                           "relevance": 2},
            {"title": "Blade Runner 2049",  "overview": "A new blade runner discovers a long-buried secret that has the potential to plunge what's left of society into chaos.",                                   "relevance": 2},
            {"title": "Arrival",            "overview": "A linguist works with the military to communicate with alien lifeforms after mysterious spacecraft land around the world.",                                "relevance": 2},
            {"title": "Annihilation",       "overview": "A biologist signs up for a dangerous expedition into an environmental disaster zone where the laws of nature don't apply.",                               "relevance": 1},
            {"title": "Ex Machina",         "overview": "A young programmer is selected to participate in a ground-breaking experiment to evaluate the capabilities of an AI with a human face.",                  "relevance": 1},
            {"title": "Shrek",              "overview": "A green ogre agrees to rescue a princess from a dragon-guarded castle in exchange for the return of his beloved swamp.",                                  "relevance": 0},
            {"title": "Forrest Gump",       "overview": "A slow-witted but kind-hearted man from Alabama witnesses and influences several defining historical events in 20th century America.",                     "relevance": 0},
            {"title": "The Notebook",       "overview": "An old man reads to a woman with dementia the love story of a poor, passionate young man and a rich young woman who fall in love.",                       "relevance": 0},
        ],
    },
    {
        "query": "feel-good romantic comedy with witty dialogue",
        "candidates": [
            {"title": "When Harry Met Sally",       "overview": "Two people meet on a road trip, become friends over years of witty conversations, and slowly fall in love.",                                      "relevance": 2},
            {"title": "10 Things I Hate About You", "overview": "A high school student can only date once her overprotective father allows her younger sister to date, leading to arranged romance and sharp wit.",  "relevance": 2},
            {"title": "Notting Hill",               "overview": "A shy bookstore owner in London unexpectedly becomes the love interest of a famous Hollywood actress.",                                           "relevance": 2},
            {"title": "The Proposal",               "overview": "A high-powered Canadian book editor fakes an engagement with her assistant to avoid deportation, spending a weekend with his eccentric family.",   "relevance": 2},
            {"title": "Crazy, Stupid, Love",        "overview": "A middle-aged man reinvents himself after his wife asks for a divorce, getting advice from a smooth-talking bachelor.",                           "relevance": 1},
            {"title": "About Time",                 "overview": "A young man discovers he can time travel and uses the ability to improve his love life, learning what really matters.",                           "relevance": 1},
            {"title": "No Country for Old Men",     "overview": "Violence and mayhem ensue after a hunter stumbles upon a drug deal gone wrong and takes the money, pursued by a relentless killer.",              "relevance": 0},
            {"title": "Schindler's List",           "overview": "A German businessman saves the lives of more than a thousand mostly Polish-Jewish refugees during the Holocaust.",                                 "relevance": 0},
            {"title": "Alien",                      "overview": "The crew of a commercial spaceship encounters a deadly extraterrestrial creature after investigating a distress signal.",                         "relevance": 0},
            {"title": "Saving Private Ryan",        "overview": "Following D-Day, a U.S. Army Rangers captain leads his men behind enemy lines to retrieve a paratrooper whose brothers have all been killed.",    "relevance": 0},
        ],
    },
    {
        "query": "gritty crime thriller with a heist and unexpected twists",
        "candidates": [
            {"title": "The Usual Suspects",  "overview": "A sole survivor tells the story of a harbor massacre and robbery, with a narrator whose reliability becomes increasingly questionable.",                  "relevance": 2},
            {"title": "Heat",                "overview": "A seasoned detective and a professional bank robber play a cat-and-mouse game in Los Angeles as the stakes escalate.",                                   "relevance": 2},
            {"title": "Ocean's Eleven",      "overview": "A group of slick criminals plan to rob three Las Vegas casinos simultaneously under the nose of a dangerous crime lord.",                               "relevance": 2},
            {"title": "Inside Man",          "overview": "A brilliant bank robber executes what appears to be the perfect heist while a detective and a mysterious fixer play roles in the outcome.",             "relevance": 2},
            {"title": "Sicario",             "overview": "An idealistic FBI agent is enlisted by a government task force to aid in the war against a Mexican drug cartel.",                                       "relevance": 1},
            {"title": "Prisoners",           "overview": "A desperate father takes the law into his own hands when two young girls disappear and the detective on the case pursues a suspect.",                   "relevance": 1},
            {"title": "The Dark Knight",     "overview": "Batman faces a criminal genius called the Joker who plunges Gotham City into anarchy while challenging Batman's moral limits.",                         "relevance": 1},
            {"title": "Toy Story",           "overview": "A cowboy doll feels threatened when a new spaceman toy takes his place as the child's favourite and must find his way back home.",                      "relevance": 0},
            {"title": "Mamma Mia!",          "overview": "A bride-to-be invites three possible fathers to her wedding on a Greek island, setting off confusion and musical chaos.",                              "relevance": 0},
            {"title": "Finding Nemo",        "overview": "A clownfish ventures into the ocean to find his son who was taken by a scuba diver and is now in a dentist's fish tank.",                             "relevance": 0},
        ],
    },
    {
        "query": "inspiring sports underdog story with emotional moments",
        "candidates": [
            {"title": "Rocky",              "overview": "A small-time Philadelphia boxer gets a once-in-a-lifetime shot to fight the world heavyweight champion and prove himself.",                              "relevance": 2},
            {"title": "Hoosiers",           "overview": "A small-town Indiana high school basketball team defies the odds with a new coach to rise to the state championship.",                                   "relevance": 2},
            {"title": "The Blind Side",     "overview": "A homeless teenager with exceptional athletic talent is taken in by a caring family who helps him become an NFL first-round pick.",                       "relevance": 2},
            {"title": "Cool Runnings",      "overview": "A group of Jamaican sprinters qualify for the Winter Olympics as a bobsled team and overcome ridicule to earn respect.",                                 "relevance": 2},
            {"title": "The Fighter",        "overview": "A boxer struggles to overcome a dysfunctional family and his crack-addicted brother while trying to make it to the top.",                              "relevance": 2},
            {"title": "Moneyball",          "overview": "The general manager of the Oakland A's uses sabermetrics and statistical analysis to build a competitive team with a tiny budget.",                     "relevance": 2},
            {"title": "Coach Carter",       "overview": "A high school basketball coach benches his undefeated team for poor academic performance, sparking community controversy.",                             "relevance": 1},
            {"title": "Eternal Sunshine",   "overview": "A couple has each other erased from their memories through a medical procedure and then discovers they still love each other.",                          "relevance": 0},
            {"title": "The Social Network", "overview": "The story of the founding of Facebook and the subsequent legal battles between the co-founders.",                                                       "relevance": 0},
            {"title": "Pulp Fiction",       "overview": "The lives of two mob hitmen, a boxer, and a gangster's wife intertwine in four tales of violence and redemption in Los Angeles.",                      "relevance": 0},
        ],
    },
]


# ─── Model registry ───────────────────────────────────────────────────────────

MODELS: list[dict[str, Any]] = [
    {
        "key": "minilm-l6",
        "name": "MiniLM-L6",
        "model_id": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "backend": "cross-encoder",
        "desc": "MiniLM L6 — very fast, small",
    },
    {
        "key": "minilm-l12",
        "name": "MiniLM-L12",
        "model_id": "cross-encoder/ms-marco-MiniLM-L-12-v2",
        "backend": "cross-encoder",
        "desc": "MiniLM L12 — balanced speed/accuracy",
    },
    {
        "key": "bge",
        "name": "BGE-reranker-v2-m3",
        "model_id": "BAAI/bge-reranker-v2-m3",
        "backend": "cross-encoder",
        "desc": "BGE multilingual — strong quality",
    },
    {
        "key": "mxbai-base",
        "name": "mxbai-rerank-base-v1",
        "model_id": "mixedbread-ai/mxbai-rerank-base-v1",
        "backend": "cross-encoder",
        "desc": "mxbai base — strong general reranker",
    },
    {
        "key": "mxbai-large",
        "name": "mxbai-rerank-large-v1",
        "model_id": "mixedbread-ai/mxbai-rerank-large-v1",
        "backend": "cross-encoder",
        "desc": "mxbai large — best quality, slower",
    },
    {
        "key": "flashrank-tiny",
        "name": "FlashRank-TinyBERT",
        "model_id": "ms-marco-TinyBERT-L-2-v2",
        "backend": "flashrank",
        "desc": "FlashRank TinyBERT — ultra-fast",
    },
    {
        "key": "flashrank-mini",
        "name": "FlashRank-MiniLM-L12",
        "model_id": "ms-marco-MiniLM-L-12-v2",
        "backend": "flashrank",
        "desc": "FlashRank MiniLM-L12 — fast with good quality",
    },
]


# ─── Metrics ─────────────────────────────────────────────────────────────────

def _dcg(rels: list[float], k: int) -> float:
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels[:k]))


def ndcg_at_k(ranked_rels: list[float], k: int) -> float:
    ideal = sorted(ranked_rels, reverse=True)
    idcg = _dcg(ideal, k)
    return _dcg(ranked_rels, k) / idcg if idcg else 0.0


def mrr(ranked_rels: list[float]) -> float:
    for i, r in enumerate(ranked_rels):
        if r > 0:
            return 1.0 / (i + 1)
    return 0.0


def precision_at_k(ranked_rels: list[float], k: int) -> float:
    return sum(1 for r in ranked_rels[:k] if r > 0) / k


# ─── Ranker backends ─────────────────────────────────────────────────────────

@dataclass
class BenchResult:
    name: str
    desc: str
    load_s: float
    latencies_ms: list[float] = field(default_factory=list)
    ndcg5: list[float] = field(default_factory=list)
    ndcg10: list[float] = field(default_factory=list)
    mrr_scores: list[float] = field(default_factory=list)
    p5: list[float] = field(default_factory=list)
    error: str = ""


def _rank_cross_encoder(model_id: str, query: str, candidates: list[dict]) -> list[int]:
    """Returns candidate indices sorted best→worst."""
    from sentence_transformers import CrossEncoder  # type: ignore[import]
    model = CrossEncoder(model_id, max_length=512)
    pairs = [(query, c["overview"]) for c in candidates]
    scores = model.predict(pairs)
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)


def _rank_flashrank(model_id: str, query: str, candidates: list[dict]) -> list[int]:
    from flashrank import Ranker, RerankRequest  # type: ignore[import]
    ranker = Ranker(model_name=model_id)
    passages = [{"id": i, "text": c["overview"]} for i, c in enumerate(candidates)]
    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)
    return [r["id"] for r in results]


def _load_cross_encoder(model_id: str):
    from sentence_transformers import CrossEncoder  # type: ignore[import]
    return CrossEncoder(model_id, max_length=512)


def _load_flashrank(model_id: str):
    from flashrank import Ranker  # type: ignore[import]
    return Ranker(model_name=model_id)


# ─── Core benchmark loop ─────────────────────────────────────────────────────

def run_model(cfg: dict[str, Any], top_k: int = 5, clear_cache: bool = False) -> BenchResult:
    result = BenchResult(name=cfg["name"], desc=cfg["desc"], load_s=0.0)

    # Load model
    t0 = time.perf_counter()
    try:
        if cfg["backend"] == "cross-encoder":
            model = _load_cross_encoder(cfg["model_id"])
        else:
            model = _load_flashrank(cfg["model_id"])
    except Exception as exc:
        result.error = f"Load failed: {exc}"
        return result
    result.load_s = time.perf_counter() - t0

    for case in TEST_CASES:
        query = case["query"]
        candidates = case["candidates"]
        ground_truth = [c["relevance"] for c in candidates]

        t0 = time.perf_counter()
        try:
            if cfg["backend"] == "cross-encoder":
                from sentence_transformers import CrossEncoder  # type: ignore[import]
                pairs = [(query, c["overview"]) for c in candidates]
                scores = model.predict(pairs)
                ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            else:
                from flashrank import RerankRequest  # type: ignore[import]
                passages = [{"id": i, "text": c["overview"]} for i, c in enumerate(candidates)]
                request = RerankRequest(query=query, passages=passages)
                results = model.rerank(request)
                ranked_indices = [r["id"] for r in results]
        except Exception as exc:
            result.error = f"Inference failed: {exc}"
            return result

        elapsed_ms = (time.perf_counter() - t0) * 1000
        result.latencies_ms.append(elapsed_ms)

        ranked_rels = [ground_truth[i] for i in ranked_indices]
        result.ndcg5.append(ndcg_at_k(ranked_rels, 5))
        result.ndcg10.append(ndcg_at_k(ranked_rels, 10))
        result.mrr_scores.append(mrr(ranked_rels))
        result.p5.append(precision_at_k(ranked_rels, 5))

    del model  # release memory before optional cache wipe
    if clear_cache:
        _clear_model_cache()

    return result


# ─── Reporting ────────────────────────────────────────────────────────────────

def _mean(vals: list[float]) -> float:
    return statistics.mean(vals) if vals else 0.0


def _fmt(v: float) -> str:
    return f"{v:.3f}"


def print_results(results: list[BenchResult]) -> None:
    cols = ["Model", "NDCG@5", "NDCG@10", "MRR", "P@5", "Load(s)", "Lat/q(ms)", "Notes"]
    widths = [22, 7, 8, 7, 7, 8, 10, 30]

    def row(*cells: str) -> str:
        return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))

    sep = "  ".join("-" * w for w in widths)

    print()
    print("=" * sum(widths + [2 * (len(widths) - 1)]))
    print("  FilmFind — Cross-Encoder Reranker Benchmark")
    print("=" * sum(widths + [2 * (len(widths) - 1)]))
    print(row(*cols))
    print(sep)

    for r in results:
        if r.error:
            print(row(r.name, "—", "—", "—", "—", "—", "—", f"ERROR: {r.error[:28]}"))
            continue
        lat_mean = _mean(r.latencies_ms)
        lat_p95  = sorted(r.latencies_ms)[int(len(r.latencies_ms) * 0.95)] if r.latencies_ms else 0.0
        print(row(
            r.name,
            _fmt(_mean(r.ndcg5)),
            _fmt(_mean(r.ndcg10)),
            _fmt(_mean(r.mrr_scores)),
            _fmt(_mean(r.p5)),
            f"{r.load_s:.1f}",
            f"{lat_mean:.1f} (p95:{lat_p95:.0f})",
            r.desc,
        ))

    print(sep)
    print()
    print("Metrics explanation:")
    print("  NDCG@k  — ranking quality accounting for position (higher = better, max 1.0)")
    print("  MRR     — how high the first relevant result appears (higher = better)")
    print("  P@5     — fraction of top-5 results that are relevant (higher = better)")
    print("  Load(s) — one-time model download + load time")
    print("  Lat/q   — inference time per query over 5 test queries (ms)")
    print()

    # Recommendation
    ok = [r for r in results if not r.error]
    if not ok:
        print("No models ran successfully.")
        return

    best_quality = max(ok, key=lambda r: (_mean(r.ndcg5) + _mean(r.mrr_scores)) / 2)
    best_speed   = min(ok, key=lambda r: _mean(r.latencies_ms))
    balanced     = max(ok, key=lambda r: (
        (_mean(r.ndcg5) + _mean(r.mrr_scores)) / 2
        - (_mean(r.latencies_ms) / 500)  # penalise slow models lightly
    ))

    print("Recommendations:")
    print(f"  Best quality  → {best_quality.name} (NDCG@5={_fmt(_mean(best_quality.ndcg5))})")
    print(f"  Fastest       → {best_speed.name}   ({_mean(best_speed.latencies_ms):.1f} ms/query)")
    print(f"  Best balanced → {balanced.name}")
    print()


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark cross-encoder rerankers for FilmFind")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=[m["key"] for m in MODELS] + ["all"],
        default=["all"],
        metavar="MODEL",
        help=f"Models to run: {', '.join(m['key'] for m in MODELS)} (default: all)",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Top-k for NDCG/P computation")
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete each model's cached files after benchmarking it (saves disk — one model on disk at a time)",
    )
    args = parser.parse_args()

    selected_keys = set(args.models) if "all" not in args.models else {m["key"] for m in MODELS}
    selected = [m for m in MODELS if m["key"] in selected_keys]

    if args.clear_cache:
        print("  --clear-cache enabled: model files will be deleted after each run\n")

    print(f"\nRunning benchmark for {len(selected)} model(s) across {len(TEST_CASES)} queries …\n")

    results: list[BenchResult] = []
    for cfg in selected:
        print(f"  [{cfg['name']}] loading …", end="", flush=True)
        r = run_model(cfg, top_k=args.top_k, clear_cache=args.clear_cache)
        if r.error:
            print(f" FAILED — {r.error}")
        else:
            print(f" done (load {r.load_s:.1f}s, avg lat {_mean(r.latencies_ms):.0f}ms)")
        results.append(r)

    print_results(results)


if __name__ == "__main__":
    main()
