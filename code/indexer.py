"""
indexer.py — Corpus loading, section chunking, embedding, and ChromaDB indexing.

Usage:
    python indexer.py           # builds index using PROVIDER from .env
    python indexer.py --force   # re-indexes even if collection exists
"""

import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

import chromadb

from config import (
    DATA_DIR,
    CHROMA_DIR,
    CHROMA_COLLECTION,
    PROVIDER,
    EMBED_MODEL_LOCAL,
    EMBED_MODEL_CLOUD,
    COMPANY_MAP,
)

# ---------------------------------------------------------------------------
# 1. Corpus Loader
# ---------------------------------------------------------------------------

def _company_from_path(path: Path) -> str:
    """Infer company name from the file's location under data/."""
    parts = path.relative_to(DATA_DIR).parts
    # parts[0] is the top-level folder: hackerrank, claude, visa
    key = parts[0].lower()
    return COMPANY_MAP.get(key, parts[0])


def _category_from_path(path: Path) -> str:
    """Return the immediate subfolder under the company dir as category."""
    parts = path.relative_to(DATA_DIR).parts
    # parts[0]=company, parts[1]=category (if exists), parts[-1]=file
    if len(parts) >= 3:
        return parts[1]          # e.g. "screen", "interviews", "pricing-and-billing"
    elif len(parts) == 2:
        return parts[0]          # file sits directly under company dir
    return "general"


def _extract_title(frontmatter: dict, body: str, path: Path) -> str:
    """Extract article title: frontmatter title → first # heading → filename."""
    if frontmatter.get("title"):
        # Frontmatter titles are sometimes very long; take up to first sentence
        raw = frontmatter["title"].strip().strip('"').strip("'")
        # Truncate at first period or after 120 chars
        if len(raw) > 120:
            raw = raw[:120]
        return raw

    # Look for first markdown heading
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()

    # Fallback to filename without numeric prefix and extension
    stem = path.stem
    # Strip leading numeric slug like "9684438314-"
    stem = re.sub(r"^\d+-", "", stem)
    return stem.replace("-", " ").title()


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split YAML frontmatter from body.
    Returns (frontmatter_dict, body_text).
    Frontmatter is minimal — we only need 'title'.
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body = text[end + 4:].strip()  # skip closing ---\n

    fm = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")

    return fm, body


def load_corpus() -> list[dict]:
    """
    Walk data/ and return a list of article dicts:
      {title, body, company, category, source_path}
    """
    articles = []
    counts = defaultdict(int)

    for md_file in sorted(DATA_DIR.rglob("*.md")):
        # Skip index files — they are navigation, not content
        if md_file.name in ("index.md",):
            continue

        raw = md_file.read_text(encoding="utf-8", errors="ignore")
        frontmatter, body = _parse_frontmatter(raw)

        # Skip empty files
        if len(body.strip()) < 50:
            continue

        company = _company_from_path(md_file)
        category = _category_from_path(md_file)
        title = _extract_title(frontmatter, body, md_file)
        source_path = str(md_file.relative_to(DATA_DIR))

        articles.append({
            "title": title,
            "body": body,
            "company": company,
            "category": category,
            "source_path": source_path,
        })
        counts[company] += 1

    print(f"Loaded {len(articles)} articles:")
    for company, count in sorted(counts.items()):
        print(f"  {company}: {count}")

    return articles


# ---------------------------------------------------------------------------
# 2. Section Chunker
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
MIN_CHUNK_CHARS = 100   # ignore tiny sections (e.g. a heading with no content)
MAX_CHUNK_CHARS = 3000  # guard against very long sections; split on blank lines if exceeded


def _split_long_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split text that exceeds max_chars on paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def chunk_article(article: dict) -> list[dict]:
    """
    Split one article into section chunks.
    - Split on ## and ### headings.
    - Short articles (< 800 chars) stay as one chunk.
    - Very long sections are split further on paragraph boundaries.
    - Each chunk inherits article metadata plus section_heading and chunk_index.
    """
    body = article["body"]
    title = article["title"]

    # Short articles: keep whole
    if len(body) < 800:
        return [{
            **article,
            "text": f"{title}\n\n{body}",
            "section_heading": title,
            "chunk_index": 0,
        }]

    # Find all heading positions
    matches = list(_HEADING_RE.finditer(body))

    # No subheadings — treat whole body as one chunk (or split if long)
    if not matches:
        texts = _split_long_text(body)
        return [
            {
                **article,
                "text": f"{title}\n\n{part}",
                "section_heading": title,
                "chunk_index": i,
            }
            for i, part in enumerate(texts)
        ]

    # Build sections: (heading_text, section_body)
    sections = []

    # Content before the first heading
    preamble = body[: matches[0].start()].strip()
    if len(preamble) >= MIN_CHUNK_CHARS:
        sections.append((title, preamble))

    for idx, match in enumerate(matches):
        heading_text = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()

        if len(section_body) < MIN_CHUNK_CHARS:
            continue  # skip stub sections

        # Prefix each section with article title for context
        full_text = f"{title} — {heading_text}\n\n{section_body}"
        sections.append((heading_text, full_text))

    # Split any oversized sections further
    chunks = []
    chunk_index = 0
    for heading, text in sections:
        parts = _split_long_text(text)
        for part in parts:
            chunks.append({
                **article,
                "text": part,
                "section_heading": heading,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    # Fallback: if nothing made it through (all sections were stubs)
    if not chunks:
        chunks.append({
            **article,
            "text": f"{title}\n\n{body}",
            "section_heading": title,
            "chunk_index": 0,
        })

    return chunks


def chunk_corpus(articles: list[dict]) -> list[dict]:
    """Chunk all articles. Returns flat list of chunk dicts."""
    all_chunks = []
    for article in articles:
        all_chunks.extend(chunk_article(article))
    print(f"Chunked into {len(all_chunks)} sections")
    return all_chunks


# ---------------------------------------------------------------------------
# 3. Embedding Function
# ---------------------------------------------------------------------------

def embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts. Switches on PROVIDER env var.
    Local:  Ollama mxbai-embed-large (one at a time)
    Cloud:  Voyage AI voyage-3-large (batched)
    """
    if PROVIDER == "cloud":
        return _embed_voyage(texts)
    else:
        return _embed_ollama(texts)


def _clean_for_embed(text: str) -> str:
    """Strip token-dense noise (image URLs, bare URLs, code blocks) before embedding.
    Full text is still stored in ChromaDB — only embedding input is cleaned.
    mxbai-embed-large has a 512 token context. Dense content (code, tables, JSON)
    tokenizes at ~2 chars/token so we cap at 800 chars to stay safely under limit.
    """
    # Remove markdown images: ![alt](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Remove bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove fenced code blocks (token-dense)
    text = re.sub(r"```.*?```", "[code block]", text, flags=re.DOTALL)
    # Collapse excess whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    # Hard cap: 800 chars guarantees < 512 tokens even for dense content
    return text[:800].strip()


def _embed_ollama(texts: list[str]) -> list[list[float]]:
    import ollama
    vectors = []
    for i, text in enumerate(texts):
        clean = _clean_for_embed(text)
        response = ollama.embed(model=EMBED_MODEL_LOCAL, input=clean)
        vectors.append(response["embeddings"][0])
        if (i + 1) % 200 == 0:
            print(f"  Embedded {i + 1}/{len(texts)}...")
    return vectors


def _embed_voyage(texts: list[str]) -> list[list[float]]:
    import voyageai
    client = voyageai.Client()
    batch_size = 128
    vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.embed(batch, model=EMBED_MODEL_CLOUD, input_type="document")
        vectors.extend(result.embeddings)
        if i + batch_size < len(texts):
            print(f"  Embedded {i + batch_size}/{len(texts)}...")
    return vectors


# ---------------------------------------------------------------------------
# 4. ChromaDB Indexing
# ---------------------------------------------------------------------------

def build_index(force: bool = False) -> chromadb.Collection:
    """
    Build (or load) the ChromaDB index.
    - Persistent storage at CHROMA_DIR.
    - Single collection named CHROMA_COLLECTION.
    - Skips re-indexing if the collection already exists (unless force=True).
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Use try/except instead of list_collections() — works across all ChromaDB versions
    try:
        collection = client.get_collection(CHROMA_COLLECTION)
        if not force:
            count = collection.count()
            if count > 0:
                print(f"Index already exists: {count} chunks in '{CHROMA_COLLECTION}'. Skipping re-index.")
                print("Run with --force to re-index.")
                return collection
        # force=True or empty collection — delete and rebuild
        client.delete_collection(CHROMA_COLLECTION)
        if force:
            print(f"Deleted existing collection '{CHROMA_COLLECTION}' (--force).")
    except Exception:
        pass  # Collection does not exist yet — create it below

    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    # Load and chunk
    articles = load_corpus()
    chunks = chunk_corpus(articles)

    # Embed
    print(f"Embedding {len(chunks)} chunks via {PROVIDER} ({EMBED_MODEL_CLOUD if PROVIDER == 'cloud' else EMBED_MODEL_LOCAL})...")
    texts = [c["text"] for c in chunks]
    vectors = embed(texts)

    # Insert into ChromaDB in batches
    batch_size = 500
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        batch_vectors = vectors[i : i + batch_size]

        collection.add(
            ids=[f"chunk_{i + j}" for j in range(len(batch_chunks))],  # i is the batch start offset, j is position within batch
            embeddings=batch_vectors,
            documents=[c["text"] for c in batch_chunks],
            metadatas=[
                {
                    "company": c["company"],
                    "category": c["category"],
                    "title": c["title"],
                    "source_path": c["source_path"],
                    "section_heading": c["section_heading"],
                    "chunk_index": c["chunk_index"],
                }
                for c in batch_chunks
            ],
        )

    print(f"\nIndexed {collection.count()} chunks into collection '{CHROMA_COLLECTION}'")
    print(f"Provider: {PROVIDER} | Stored at: {CHROMA_DIR}")
    return collection


# ---------------------------------------------------------------------------
# 5. Retrieval (used by agent.py)
# ---------------------------------------------------------------------------

def get_collection() -> chromadb.Collection:
    """Load the existing ChromaDB collection. Raises if not yet indexed."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        return client.get_collection(CHROMA_COLLECTION)
    except Exception:
        raise RuntimeError(
            f"Collection '{CHROMA_COLLECTION}' not found. Run: python indexer.py"
        )


def retrieve(query: str, company: str | None = None, k: int = 5) -> list[dict]:
    """
    Retrieve top-k chunks for a query.
    If company is provided (e.g. "HackerRank"), filter to that company only.
    Returns list of dicts: {text, company, category, title, source_path, score}
    """
    collection = get_collection()

    query_vector = embed([query])[0]

    where = {"company": company} if company and company.lower() != "none" else None

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": doc,
            "company": meta.get("company"),
            "category": meta.get("category"),
            "title": meta.get("title"),
            "source_path": meta.get("source_path"),
            "section_heading": meta.get("section_heading"),
            "score": round(1 - dist, 4),  # cosine distance → similarity
        })

    return hits


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the support corpus index.")
    parser.add_argument("--force", action="store_true", help="Re-index even if collection exists.")
    parser.add_argument("--test", action="store_true", help="Run retrieval smoke tests after indexing.")
    args = parser.parse_args()

    build_index(force=args.force)

    if args.test:
        print("\n--- Retrieval Smoke Tests ---")
        tests = [
            ("how to remove a user from HackerRank", "HackerRank"),
            ("delete a conversation history", "Claude"),
            ("lost stolen visa card emergency", "Visa"),
            ("payment billing issue invoice", "HackerRank"),
            ("it is not working help", None),
        ]
        for query, company in tests:
            print(f"\nQuery: '{query}' | Company filter: {company}")
            hits = retrieve(query, company=company, k=3)
            for i, h in enumerate(hits, 1):
                print(f"  {i}. [{h['company']}] {h['title']} (score={h['score']:.3f})")
                print(f"     {h['source_path']}")
