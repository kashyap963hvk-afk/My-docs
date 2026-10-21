"""Turn text into vectors with the Jina AI embeddings API."""
import httpx

from querymesh import config

JINA_URL = "https://api.jina.ai/v1/embeddings"
BATCH_SIZE = 32


def embed(texts: list[str], task: str) -> list[list[float]]:
    """task = "retrieval.passage" for paper chunks, "retrieval.query" for questions."""
    if not config.JINA_API_KEY:
        raise RuntimeError("JINA_API_KEY is empty: put your key in the .env file")
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        response = httpx.post(
            JINA_URL,
            headers={"Authorization": f"Bearer {config.JINA_API_KEY}"},
            json={
                "model": config.EMBED_MODEL,
                "task": task,
                "dimensions": config.EMBED_DIM,
                "normalized": True,
                "input": batch,
            },
            timeout=120,
        )
        response.raise_for_status()
        rows = sorted(response.json()["data"], key=lambda row: row["index"])
        vectors.extend(row["embedding"] for row in rows)
    return vectors


if __name__ == "__main__":
    vector = embed(["hybrid search combines keywords and meaning"], "retrieval.query")[0]
    print(f"dimensions={len(vector)} first_values={[round(v, 4) for v in vector[:5]]}")
