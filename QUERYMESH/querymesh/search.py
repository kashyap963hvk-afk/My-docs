"""OpenSearch: create the index, store chunks, and run hybrid (BM25 + vector + RRF) search."""
import sys

from opensearchpy import OpenSearch, helpers

from querymesh import config
from querymesh.embeddings import embed

client = OpenSearch(hosts=[config.OPENSEARCH_URL], timeout=60)

INDEX_BODY = {
    "settings": {"index": {"knn": True, "number_of_shards": 1, "number_of_replicas": 0}},
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "paper_id": {"type": "keyword"},
            "title": {"type": "text"},
            "authors": {"type": "keyword"},
            "published": {"type": "date"},
            "url": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "english"},
            "embedding": {
                "type": "knn_vector",
                "dimension": config.EMBED_DIM,
                "method": {"name": "hnsw", "engine": "lucene", "space_type": "cosinesimil"},
            },
        }
    },
}

PIPELINE_BODY = {
    "description": "QueryMesh hybrid search: merge BM25 and vector results with Reciprocal Rank Fusion",
    "phase_results_processors": [
        {"score-ranker-processor": {"combination": {"technique": "rrf", "rank_constant": 60}}}
    ],
}


def setup() -> None:
    """Create the index and the RRF search pipeline (safe to run many times)."""
    if not client.indices.exists(index=config.INDEX_NAME):
        client.indices.create(index=config.INDEX_NAME, body=INDEX_BODY)
        print(f"created index {config.INDEX_NAME}")
    client.transport.perform_request(
        "PUT", f"/_search/pipeline/{config.SEARCH_PIPELINE}", body=PIPELINE_BODY
    )
    print(f"search pipeline {config.SEARCH_PIPELINE} is ready")


def paper_exists(paper_id: str) -> bool:
    result = client.count(index=config.INDEX_NAME, body={"query": {"term": {"paper_id": paper_id}}})
    return result["count"] > 0


def index_chunks(chunks: list[dict]) -> int:
    """Embed every chunk and store it. Each chunk needs chunk_id, paper_id, title, text..."""
    if not chunks:
        return 0
    vectors = embed([c["title"] + "\n" + c["text"] for c in chunks], "retrieval.passage")
    actions = [
        {"_index": config.INDEX_NAME, "_id": c["chunk_id"], "_source": {**c, "embedding": v}}
        for c, v in zip(chunks, vectors)
    ]
    ok, _ = helpers.bulk(client, actions, refresh=True)
    return ok


def hybrid_search(query: str, k: int = config.TOP_K) -> list[dict]:
    """Keyword search + meaning search, merged by RRF. Returns the best k chunks."""
    vector = embed([query], "retrieval.query")[0]
    body = {
        "size": k,
        "_source": {"excludes": ["embedding"]},
        "query": {
            "hybrid": {
                "queries": [
                    {"multi_match": {"query": query, "fields": ["title^2", "text"]}},
                    {"knn": {"embedding": {"vector": vector, "k": k * 5}}},
                ]
            }
        },
    }
    response = client.search(
        index=config.INDEX_NAME, body=body, params={"search_pipeline": config.SEARCH_PIPELINE}
    )
    return [{**hit["_source"], "score": hit["_score"]} for hit in response["hits"]["hits"]]


if __name__ == "__main__":
    if sys.argv[1:] == ["setup"]:
        setup()
    else:
        question = " ".join(sys.argv[1:]) or "What is retrieval-augmented generation?"
        for n, hit in enumerate(hybrid_search(question, k=5), start=1):
            print(f"[{n}] {hit['score']:.4f} {hit['paper_id']} {hit['title'][:70]}")
            print("    " + hit["text"][:160].replace("\n", " "))
