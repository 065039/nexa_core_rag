"""
Small, repeatable benchmark to support the vector database comparison (Qdrant vs Chroma).

Both stores get the same nodes (structure strategy) and the same bge-small embeddings, so the
only thing that changes is the database. Measures:
  - indexing time (embedding is computed once and reused, so this is storage time only)
  - mean and p95 query latency with and without a department metadata filter
  - Hit@5 on the evaluation questions that have a known source document

Postgres/pgvector and Supabase are compared on documented features in docs/VECTOR_DB_COMPARISON.md.

Install extra packages first:
    pip install chromadb llama-index-vector-stores-chroma
Usage:
    python scripts/benchmark_vector_dbs.py
"""
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llama_index.core import StorageContext, VectorStoreIndex  # noqa: E402
from llama_index.core.schema import QueryBundle  # noqa: E402
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters  # noqa: E402

from src.config import settings  # noqa: E402
from src.indexing import build_nodes, get_qdrant_client  # noqa: E402
from src.models import get_embed_model  # noqa: E402

RESULTS = ROOT / "evaluation" / "results"


def make_stores(tmp: str) -> dict:
    stores = {}
    from llama_index.vector_stores.qdrant import QdrantVectorStore
    client = get_qdrant_client()
    if client.collection_exists("bench_qdrant"):
        client.delete_collection("bench_qdrant")
    stores["Qdrant"] = QdrantVectorStore(client=client, collection_name="bench_qdrant")
    try:
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore
        chroma = chromadb.PersistentClient(path=f"{tmp}/chroma")
        stores["Chroma"] = ChromaVectorStore(chroma_collection=chroma.get_or_create_collection("bench_chroma"))
    except ImportError:
        print("Chroma not installed, skipping (pip install chromadb llama-index-vector-stores-chroma)")
    return stores


def p95(values: list) -> float:
    values = sorted(values)
    return values[max(0, int(len(values) * 0.95) - 1)]


def main() -> None:
    embed = get_embed_model()
    nodes = build_nodes("structure", settings.chunk_size, settings.chunk_overlap)
    texts = [n.get_content(metadata_mode="embed") for n in nodes]
    for node, vec in zip(nodes, embed.get_text_embedding_batch(texts)):
        node.embedding = vec

    questions = [json.loads(l) for l in (ROOT / "evaluation" / "questions.jsonl").read_text().splitlines() if l.strip()]
    questions = [q for q in questions if q.get("expected_docs")]
    bundles = [QueryBundle(q["question"], embedding=embed.get_query_embedding(q["question"])) for q in questions]

    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, store in make_stores(tmp).items():
            t0 = time.perf_counter()
            index = VectorStoreIndex(nodes, storage_context=StorageContext.from_defaults(vector_store=store),
                                     embed_model=embed)
            index_s = time.perf_counter() - t0

            plain, filtered, hits = [], [], 0
            for q, bundle in zip(questions, bundles):
                t = time.perf_counter()
                got = index.as_retriever(similarity_top_k=5).retrieve(bundle)
                plain.append((time.perf_counter() - t) * 1000)
                docs = {n.node.metadata["doc_id"] for n in got}
                hits += int(bool(docs & set(q["expected_docs"])))

                dept = q["department"] if q["department"] != "All" else "HR"
                flt = MetadataFilters(filters=[MetadataFilter(key="department", value=dept, operator=FilterOperator.EQ)])
                t = time.perf_counter()
                index.as_retriever(similarity_top_k=5, filters=flt).retrieve(bundle)
                filtered.append((time.perf_counter() - t) * 1000)

            rows.append({"database": name, "nodes": len(nodes), "index_seconds": round(index_s, 2),
                         "mean_query_ms": round(statistics.mean(plain), 1), "p95_query_ms": round(p95(plain), 1),
                         "mean_filtered_query_ms": round(statistics.mean(filtered), 1),
                         "hit@5": round(hits / len(questions), 3)})
            print(rows[-1])

    RESULTS.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    md = ["# Vector Database Benchmark", "",
          f"Embeddings: {settings.embed_model if settings.embed_backend != 'hash' else 'hash-test'}  ",
          f"Qdrant mode: {'embedded local' if settings.qdrant_path else 'Docker server ' + settings.qdrant_url}  ",
          f"Questions: {len(questions)}", "",
          "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    md += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    (RESULTS / "vector_db_benchmark.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
