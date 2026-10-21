"""Ingestion: arXiv API -> PDF -> Docling -> chunks -> Jina vectors -> OpenSearch (+ S3 copy)."""
import argparse
import re
from pathlib import Path

import arxiv
import boto3
import httpx

from querymesh import config, search

DATA_DIR = Path("data/pdfs")
CHUNK_CHARS = 1500
OVERLAP_CHARS = 200
_converter = None  # Docling is slow to load, so we create it once, the first time we need it


def fetch_papers(query: str, max_papers: int) -> list[dict]:
    """Ask the arXiv API for the newest papers that match the query."""
    arxiv_client = arxiv.Client(page_size=min(max_papers, 100), delay_seconds=3.0, num_retries=3)
    search_spec = arxiv.Search(
        query=query, max_results=max_papers, sort_by=arxiv.SortCriterion.SubmittedDate
    )
    papers = []
    for result in arxiv_client.results(search_spec):
        papers.append({
            "paper_id": result.get_short_id(),
            "title": " ".join(result.title.split()),
            "authors": [a.name for a in result.authors][:10],
            "published": result.published.date().isoformat(),
            "url": result.entry_id,
            "pdf_url": result.pdf_url,
            "summary": " ".join(result.summary.split()),
        })
    return papers


def download_pdf(paper: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{paper['paper_id'].replace('/', '_')}.pdf"
    if not path.exists():
        response = httpx.get(paper["pdf_url"], follow_redirects=True, timeout=120)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def pdf_to_markdown(path: Path) -> str:
    """Docling reads the PDF layout (headings, paragraphs, tables) and returns Markdown."""
    global _converter
    if _converter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
        _converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
    return _converter.convert(str(path)).document.export_to_markdown()


def chunk_markdown(markdown: str) -> list[str]:
    """Split by headings, then cut long sections into overlapping windows."""
    markdown = markdown.split("\n## References")[0]  # the reference list is noise for search
    sections = [s.strip() for s in re.split(r"\n(?=#{1,3} )", markdown) if s.strip()]
    chunks = []
    for section in sections:
        start = 0
        while start < len(section):
            piece = section[start:start + CHUNK_CHARS].strip()
            if len(piece) > 100:
                chunks.append(piece)
            start += CHUNK_CHARS - OVERLAP_CHARS
    return chunks


def upload_pdf(path: Path) -> None:
    """Keep the original PDF in S3 (FakeCloud or AWS). AWS_ENDPOINT_URL decides which one."""
    if config.PAPERS_BUCKET:
        boto3.client("s3").upload_file(str(path), config.PAPERS_BUCKET, f"pdfs/{path.name}")


def make_chunks(paper: dict, texts: list[str]) -> list[dict]:
    keep = ("paper_id", "title", "authors", "published", "url")
    return [
        {**{k: paper[k] for k in keep}, "chunk_id": f"{paper['paper_id']}-{n}", "text": text}
        for n, text in enumerate(texts)
    ]


def ingest_full_text(query: str, max_papers: int) -> dict:
    """Nightly job: full PDFs, parsed by Docling."""
    search.setup()
    added, skipped = [], []
    for paper in fetch_papers(query, max_papers):
        if search.paper_exists(paper["paper_id"]):
            skipped.append(paper["paper_id"])
            continue
        path = download_pdf(paper)
        texts = chunk_markdown(pdf_to_markdown(path))
        count = search.index_chunks(make_chunks(paper, texts))
        upload_pdf(path)
        added.append(paper["paper_id"])
        print(f"indexed {paper['paper_id']}: {count} chunks  {paper['title'][:60]}")
    return {"added": added, "skipped": skipped}


def ingest_abstracts(query: str, max_papers: int) -> dict:
    """Fast path used by the Scout agent: index title + abstract only (no PDF)."""
    search.setup()
    added = []
    for paper in fetch_papers(query, max_papers):
        if search.paper_exists(paper["paper_id"]):
            continue
        search.index_chunks(make_chunks(paper, [paper["summary"]]))
        added.append(paper["paper_id"])
    return {"added": added}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load arXiv papers into OpenSearch")
    parser.add_argument("--query", default="cat:cs.CL AND abs:retrieval")
    parser.add_argument("--max-papers", type=int, default=5)
    parser.add_argument("--abstracts-only", action="store_true")
    args = parser.parse_args()
    run = ingest_abstracts if args.abstracts_only else ingest_full_text
    print(run(args.query, args.max_papers))
