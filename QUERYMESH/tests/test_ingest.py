"""Test the chunker and the arXiv query builder (no network needed)."""
from querymesh.ingest import CHUNK_CHARS, chunk_markdown
from querymesh.skills import topic_to_arxiv_query


def test_chunks_split_on_headings_and_drop_references():
    markdown = "# Title\n\n" + "intro " * 50 + "\n## Method\n\n" + "method " * 400 + "\n## References\n\n[1] x"
    chunks = chunk_markdown(markdown)
    assert all(len(c) <= CHUNK_CHARS for c in chunks)
    assert chunks[0].startswith("# Title") and any(c.startswith("## Method") for c in chunks)
    assert not any("[1] x" in c for c in chunks)


def test_topic_to_arxiv_query():
    assert topic_to_arxiv_query("What is reciprocal rank fusion?") == (
        "all:reciprocal AND all:rank AND all:fusion")
