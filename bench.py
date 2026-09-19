from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from src.chunking import HeadingBasedChunker
from src.embeddings import (
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    MockEmbedder,
    OpenAIEmbedder,
)
from src.models import Document
from src.store import EmbeddingStore


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "data" / "library"
DEFAULT_OUTPUT = ROOT / "report" / "heading_benchmark_results.json"

BENCHMARKS = [
    {
        "query": "Với giáo trình tại phòng 111, được mượn tối đa bao nhiêu cuốn, trong bao lâu và được gia hạn thế nào?",
        "gold_doc_id": "student-textbook-borrowing",
        "answer_marker": "tối đa 8 cuốn",
        "metadata_filter": {"audience": "student"},
    },
    {
        "query": "Chính sách mượn sách tham khảo tại phòng 102 quy định số lượng, thời hạn và gia hạn như thế nào?",
        "gold_doc_id": "student-reference-book-borrowing",
        "answer_marker": "tối đa 5 cuốn",
        "metadata_filter": None,
    },
    {
        "query": "Phòng học nhóm phục vụ vào thời gian nào và quy trình nhận trả chìa khóa ra sao?",
        "gold_doc_id": "group-study-room",
        "answer_marker": "Trả lại chìa khóa sau sử dụng và lấy lại thẻ",
        "metadata_filter": None,
    },
    {
        "query": "Khi quên mật khẩu tài khoản thư viện, bạn đọc cần thực hiện các bước nào?",
        "gold_doc_id": "library-account",
        "answer_marker": "Quên mật khẩu / Quên mã PIN",
        "metadata_filter": None,
    },
    {
        "query": "Bạn đọc ngoài HUST có thể đọc toàn văn tài nguyên số không và cần điều kiện gì?",
        "gold_doc_id": "digital-resource-faq",
        "answer_marker": "có thể đọc toàn văn tài liệu số nếu đăng ký làm thẻ/tài khoản thư viện",
        "metadata_filter": None,
    },
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the flat YAML frontmatter used by this lab without extra packages."""
    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", text, re.DOTALL)
    if not match:
        return {}, text.strip()

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata, text[match.end() :].strip()


def load_chunk_documents(data_dir: Path, chunker: HeadingBasedChunker) -> tuple[list[Document], dict[str, int]]:
    documents: list[Document] = []
    counts: dict[str, int] = {}

    for path in sorted(data_dir.glob("*.md")):
        metadata, content = parse_frontmatter(path.read_text(encoding="utf-8"))
        source_doc_id = metadata.get("doc_id", path.stem)
        chunks = chunker.chunk(content)
        counts[source_doc_id] = len(chunks)
        for index, chunk in enumerate(chunks):
            chunk_metadata = {
                **metadata,
                "doc_id": source_doc_id,
                "chunk_index": index,
                "strategy": "heading_based",
                "source": str(path.relative_to(ROOT)),
            }
            documents.append(Document(f"{source_doc_id}#{index}", chunk, chunk_metadata))

    return documents, counts


def select_embedder(provider: str) -> tuple[Callable[[str], list[float]], str, str | None]:
    provider = provider.strip().lower()
    try:
        if provider == "local":
            embedder = LocalEmbedder(os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        elif provider == "openai":
            embedder = OpenAIEmbedder(os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        elif provider == "gemini":
            embedder = GeminiEmbedder(os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
        elif provider == "mock":
            embedder = MockEmbedder()
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
        return embedder, getattr(embedder, "_backend_name", provider), None
    except Exception as exc:
        fallback = MockEmbedder()
        warning = f"Could not initialize provider '{provider}' ({exc}); using mock embeddings."
        return fallback, fallback._backend_name, warning


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def score_results(results: list[dict], benchmark: dict) -> tuple[int, int | None, int | None]:
    gold_doc_id = benchmark["gold_doc_id"]
    gold_rank = next(
        (index for index, result in enumerate(results, start=1) if result["metadata"].get("doc_id") == gold_doc_id),
        None,
    )
    answer_rank = next(
        (
            index
            for index, result in enumerate(results, start=1)
            if result["metadata"].get("doc_id") == gold_doc_id
            and normalize(benchmark["answer_marker"]) in normalize(result["content"])
        ),
        None,
    )
    if answer_rank is None:
        return 0, gold_rank, answer_rank
    return (2 if answer_rank == 1 else 1), gold_rank, answer_rank


def run_benchmark(
    data_dir: Path,
    chunk_size: int,
    provider: str,
    top_k: int,
) -> dict:
    chunker = HeadingBasedChunker(chunk_size=chunk_size)
    documents, counts = load_chunk_documents(data_dir, chunker)
    if not documents:
        raise RuntimeError(f"No Markdown documents found in {data_dir}")

    embedder, backend_name, warning = select_embedder(provider)
    store = EmbeddingStore(collection_name="heading_benchmark", embedding_fn=embedder)
    store.add_documents(documents)

    print("=== Heading-based Chunking Benchmark ===")
    print(f"Data directory : {data_dir}")
    print(f"Chunk size     : {chunk_size}")
    print(f"Embedding      : {backend_name}")
    if warning:
        print(f"WARNING        : {warning}")
    if isinstance(embedder, MockEmbedder):
        print("NOTE           : mock embeddings are deterministic but do not measure semantic similarity.")
    print(f"Loaded         : {len(documents)} chunks from {len(counts)} documents")
    print("Chunks/document: " + ", ".join(f"{doc_id}={count}" for doc_id, count in counts.items()))

    output_rows = []
    total_score = 0
    for number, benchmark in enumerate(BENCHMARKS, start=1):
        results = store.search_with_filter(
            benchmark["query"],
            top_k=top_k,
            metadata_filter=benchmark["metadata_filter"],
        )
        score, gold_rank, answer_rank = score_results(results, benchmark)
        total_score += score

        print(f"\nQ{number}: {benchmark['query']}")
        print(f"Filter: {benchmark['metadata_filter'] or 'none'}")
        for rank, result in enumerate(results, start=1):
            metadata = result["metadata"]
            preview = " ".join(result["content"].split())[:150]
            print(
                f"  {rank}. score={result['score']:.4f} "
                f"doc_id={metadata.get('doc_id')} chunk={metadata.get('chunk_index')} | {preview}"
            )
        print(f"Evaluation: {score}/2 (gold_doc_rank={gold_rank}, answer_chunk_rank={answer_rank})")

        unfiltered_results = None
        if benchmark["metadata_filter"]:
            unfiltered_results = store.search_with_filter(benchmark["query"], top_k=top_k, metadata_filter=None)
            print("A/B without filter:")
            for rank, result in enumerate(unfiltered_results, start=1):
                metadata = result["metadata"]
                print(
                    f"  {rank}. score={result['score']:.4f} "
                    f"doc_id={metadata.get('doc_id')} chunk={metadata.get('chunk_index')}"
                )

        output_rows.append(
            {
                **benchmark,
                "score": score,
                "gold_rank": gold_rank,
                "answer_rank": answer_rank,
                "results": [
                    {
                        "rank": rank,
                        "score": result["score"],
                        "doc_id": result["metadata"].get("doc_id"),
                        "chunk_index": result["metadata"].get("chunk_index"),
                        "content": result["content"],
                    }
                    for rank, result in enumerate(results, start=1)
                ],
                "unfiltered_results": [
                    {
                        "rank": rank,
                        "score": result["score"],
                        "doc_id": result["metadata"].get("doc_id"),
                        "chunk_index": result["metadata"].get("chunk_index"),
                    }
                    for rank, result in enumerate(unfiltered_results or [], start=1)
                ],
            }
        )

    print(f"\nTOTAL: {total_score}/10")
    return {
        "strategy": "heading_based",
        "chunk_size": chunk_size,
        "embedding_backend": backend_name,
        "embedding_warning": warning,
        "semantic_similarity_valid": not isinstance(embedder, MockEmbedder),
        "document_count": len(counts),
        "chunk_count": len(documents),
        "chunks_per_document": counts,
        "total_score": total_score,
        "max_score": len(BENCHMARKS) * 2,
        "benchmarks": output_rows,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description="Run the Heading-based Chunking retrieval benchmark.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--provider", choices=("mock", "local", "openai", "gemini"), default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    provider = args.provider or os.getenv("EMBEDDING_PROVIDER", "mock")
    result = run_benchmark(args.data_dir.resolve(), args.chunk_size, provider, args.top_k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved results: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
