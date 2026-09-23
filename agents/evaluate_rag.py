"""Offline leave-one-out retrieval evaluation for the 1,000-question corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rag import load_chunks, retrieve_from_chunks


def evaluate(knowledge: str | Path, corpus: str | Path, limit: int = 3) -> dict:
    knowledge = Path(knowledge)
    corpus = Path(corpus)
    records = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines() if line]
    chunks, document_frequency = load_chunks(knowledge)
    relative_corpus = str(corpus.relative_to(knowledge))
    category_by_location = {
        (relative_corpus, line): record["category"]
        for line, record in enumerate(records, 1)
    }
    at_1 = 0
    at_k = 0
    reciprocal_rank = 0.0
    misses = []
    for line, record in enumerate(records, 1):
        hits = retrieve_from_chunks(
            record["question"], chunks, document_frequency, limit=limit + 1
        )
        hits = [
            hit for hit in hits
            if not (hit["source"] == relative_corpus and hit["line"] == line)
        ][:limit]
        categories = [category_by_location.get((hit["source"], hit["line"])) for hit in hits]
        expected = record["category"]
        if categories and categories[0] == expected:
            at_1 += 1
        if expected in categories:
            rank = categories.index(expected) + 1
            at_k += 1
            reciprocal_rank += 1 / rank
        elif len(misses) < 20:
            misses.append({
                "id": record["id"],
                "category": expected,
                "retrieved_categories": categories,
            })
    total = len(records)
    return {
        "evaluation": "leave-one-out category retrieval",
        "questions": total,
        "top_k": limit,
        "category_at_1": round(at_1 / total, 4) if total else 0,
        "category_at_k": round(at_k / total, 4) if total else 0,
        "mean_reciprocal_rank": round(reciprocal_rank / total, 4) if total else 0,
        "misses_sample": misses,
        "model_called": False,
        "cost": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge", default="agents/knowledge")
    parser.add_argument(
        "--corpus", default="agents/knowledge/arbor3d-qa-1000.jsonl"
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = evaluate(args.knowledge, args.corpus, args.top_k)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
