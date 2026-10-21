"""The brains of the five agents. Each skill is a plain Python function you can test alone."""
import re

from pydantic import BaseModel, Field

from querymesh import config, ingest, search
from querymesh.llm import get_llm


def numbered(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{n}] ({c['paper_id']}) {c['title']}\n{c['text'][:1200]}"
        for n, c in enumerate(chunks, start=1)
    )


# 1. Retriever agent
def retrieve(query: str, k: int = config.TOP_K) -> list[dict]:
    """Hybrid search (BM25 + vectors + RRF) over the indexed arXiv chunks."""
    return search.hybrid_search(query, k)


# 2. Grader agent
class GradeResult(BaseModel):
    relevant: list[int] = Field(description="Numbers of the passages that help answer the question")


def grade(question: str, chunks: list[dict]) -> list[dict]:
    """Keep only the chunks that really help to answer the question."""
    if not chunks:
        return []
    prompt = (
        "You grade search results for a research assistant.\n"
        f"Question: {question}\n\nPassages:\n{numbered(chunks)}\n\n"
        "Return the numbers of the passages that contain information useful for answering "
        "the question. Return an empty list if none are useful."
    )
    result = get_llm().with_structured_output(GradeResult).invoke(prompt)
    keep = {n for n in result.relevant if 1 <= n <= len(chunks)}
    return [c for n, c in enumerate(chunks, start=1) if n in keep]


# 3. Writer agent
def write(question: str, chunks: list[dict], feedback: str = "") -> dict:
    """Write an answer that cites the passages as [1], [2], ..."""
    prompt = (
        "You are QueryMesh, a research assistant for arXiv papers.\n"
        "Answer the question using ONLY the passages below. After every claim put the "
        "passage number in square brackets, like [2]. If the passages are not enough, say "
        "what is missing. Use at most 250 words.\n\n"
        f"Question: {question}\n\nPassages:\n{numbered(chunks)}\n"
    )
    if feedback:
        prompt += f"\nA reviewer rejected your previous answer for this reason: {feedback}\nFix it.\n"
    answer = get_llm(temperature=0.2).invoke(prompt).content
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(chunks)})
    citations = [
        {"n": n, "paper_id": chunks[n - 1]["paper_id"], "title": chunks[n - 1]["title"],
         "url": chunks[n - 1]["url"]}
        for n in cited
    ]
    return {"answer": answer, "citations": citations}


# 4. Critic agent
class Verdict(BaseModel):
    grounded: bool = Field(description="True if every claim is supported by the passages")
    feedback: str = Field(description="If not grounded: which claim is unsupported, else empty")


def critic(question: str, answer: str, chunks: list[dict]) -> dict:
    """Check that the answer only says things the passages support (no hallucination)."""
    prompt = (
        "You are a strict fact checker.\n"
        f"Question: {question}\n\nPassages:\n{numbered(chunks)}\n\nAnswer to check:\n{answer}\n\n"
        "Is every claim in the answer supported by the passages?"
    )
    return get_llm().with_structured_output(Verdict).invoke(prompt).model_dump()


# 5. Scout agent
STOPWORDS = {"what", "which", "when", "where", "does", "about", "with", "from", "that",
             "this", "there", "their", "into", "have", "between", "explain", "compare"}


def topic_to_arxiv_query(topic: str) -> str:
    words = [w for w in re.findall(r"[a-zA-Z0-9-]+", topic.lower())
             if len(w) > 3 and w not in STOPWORDS]
    return " AND ".join(f"all:{w}" for w in words[:4]) or "cat:cs.CL"


def scout(topic: str, max_papers: int = 5) -> dict:
    """Find fresh papers on arXiv right now and index their abstracts."""
    return ingest.ingest_abstracts(topic_to_arxiv_query(topic), max_papers)


# Used by the supervisor itself when the first search finds too little
def rewrite_query(question: str, previous_query: str) -> str:
    prompt = (
        "A search for research papers returned too few relevant passages.\n"
        f"Original question: {question}\nPrevious search query: {previous_query}\n"
        "Write ONE better search query (keywords and synonyms, no explanation)."
    )
    return get_llm(temperature=0.3).invoke(prompt).content.strip().strip('"')[:300]
