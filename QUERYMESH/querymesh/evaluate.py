"""Measure QueryMesh like a research lab: retrieval quality per search mode, then end-to-end.
  python -m querymesh.evaluate build --n 30     (make a test set from your own index)
  python -m querymesh.evaluate retrieval        (BM25 vs vector vs hybrid: hit@5 and MRR)
  python -m querymesh.evaluate e2e --n 10       (full agents: grounded rate, citation hit, latency)
"""
import argparse
import asyncio
import json
import random
import statistics
import time
from pathlib import Path

from querymesh import config, search
from querymesh.embeddings import embed
from querymesh.graph import ask
from querymesh.llm import get_llm

EVAL_FILE = Path("data/eval.jsonl")


def build(n: int) -> None:
    """Pick random chunks and let the LLM write one question each chunk answers."""
    hits = search.client.search(index=config.INDEX_NAME, body={
        "size": n, "_source": ["paper_id", "title", "text"],
        "query": {"function_score": {"random_score": {"seed": 42, "field": "_seq_no"}}}})["hits"]["hits"]
    EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_FILE.open("w") as out:
        for hit in hits:
            chunk = hit["_source"]
            question = get_llm(0.3).invoke(
                "Write one specific question that this passage from a research paper answers. "
                "Do not mention 'the passage' or 'the paper'. Return only the question.\n\n"
                f"{chunk['title']}\n{chunk['text'][:1500]}").content.strip()
            out.write(json.dumps({"question": question, "paper_id": chunk["paper_id"]}) + "\n")
    print(f"wrote {n} questions to {EVAL_FILE}")


def load() -> list[dict]:
    return [json.loads(line) for line in EVAL_FILE.open()]


def run_mode(query: str, mode: str, k: int) -> list[str]:
    if mode == "hybrid":
        return [h["paper_id"] for h in search.hybrid_search(query, k)]
    if mode == "bm25":
        body = {"size": k, "query": {"multi_match": {"query": query, "fields": ["title^2", "text"]}}}
    else:
        body = {"size": k, "query": {"knn": {"embedding": {"vector": embed([query], "retrieval.query")[0], "k": k}}}}
    body["_source"] = ["paper_id"]
    return [h["_source"]["paper_id"] for h in search.client.search(index=config.INDEX_NAME, body=body)["hits"]["hits"]]


def retrieval(k: int = 5) -> None:
    rows = load()
    print(f"{'mode':8} hit@{k}  MRR   (n={len(rows)})")
    for mode in ("bm25", "vector", "hybrid"):
        hit, reciprocal = 0, 0.0
        for row in rows:
            ranked = run_mode(row["question"], mode, k)
            if row["paper_id"] in ranked:
                hit += 1
                reciprocal += 1 / (ranked.index(row["paper_id"]) + 1)
        print(f"{mode:8} {hit / len(rows):.2f}   {reciprocal / len(rows):.2f}")


def e2e(n: int) -> None:
    rows = load()[:n]
    grounded, cited, seconds = 0, 0, []
    for row in rows:
        start = time.perf_counter()
        result = asyncio.run(ask(row["question"]))
        seconds.append(time.perf_counter() - start)
        grounded += bool(result.get("grounded"))
        cited += any(c["paper_id"] == row["paper_id"] for c in result.get("citations", []))
    print(f"grounded rate      {grounded / n:.2f}")
    print(f"cites gold paper   {cited / n:.2f}")
    print(f"latency p50 / max  {statistics.median(seconds):.1f}s / {max(seconds):.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "retrieval", "e2e"])
    parser.add_argument("--n", type=int, default=30)
    args = parser.parse_args()
    {"build": lambda: build(args.n), "retrieval": retrieval, "e2e": lambda: e2e(args.n)}[args.command]()
