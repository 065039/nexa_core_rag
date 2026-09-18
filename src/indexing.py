"""
Part-II ingestion: Docling Markdown -> LlamaIndex nodes -> bge-small embeddings -> Qdrant.

Two chunking strategies (compared in the ablation study):
  structure  Split on Markdown headings first (MarkdownNodeParser), then by size (SentenceSplitter).
             Each table row is also indexed as its own node with the column headers repeated,
             so questions about a single row of an approval matrix still match.
  structure_no_rows  Same as structure but without the extra table-row nodes.
  fixed      Plain SentenceSplitter over the whole document (baseline).

Usage:
    python -m src.indexing --recreate
    python -m src.indexing --strategy fixed --chunk-size 256 --collection nexacore_fixed_256 --recreate
"""
import argparse
import atexit
import json
import logging
import re
import uuid

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models as qm

from src.access import access_key
from src.config import settings
from src.models import get_embed_model

log = logging.getLogger("indexing")

# Metadata stored with every chunk. Only a few fields are embedded or shown to the LLM.
EMBED_KEEP = {"title", "department", "section"}
LLM_KEEP = {"title", "department", "section", "version", "status", "effective_date"}
FILTER_FIELDS = ["department", "status", "access_key", "doc_id", "chunk_kind"]

_CLIENT = None


def get_qdrant_client() -> QdrantClient:
    """One shared client per process (embedded local mode allows only one)."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = QdrantClient(path=settings.qdrant_path) if settings.qdrant_path else QdrantClient(url=settings.qdrant_url)
        atexit.register(_CLIENT.close)
    return _CLIENT


def load_catalog() -> list:
    catalog = json.loads((settings.converted_dir / "catalog.json").read_text(encoding="utf-8"))
    return [c for c in catalog if c["conversion_status"] in ("success", "partial_success")]


def base_metadata(entry: dict) -> dict:
    keys = ["doc_id", "source_file", "source_path", "department", "doc_type", "title", "version",
            "effective_date", "status", "access_level", "owner", "file_type"]
    meta = {k: entry.get(k, "") for k in keys}
    meta["access_key"] = access_key(entry["department"], entry["access_level"])
    return meta


def table_row_texts(markdown: str) -> list:
    """Turn every Markdown table row into 'Header: value; Header: value'."""
    rows, header = [], None
    for line in markdown.splitlines() + [""]:
        s = line.strip()
        if not s.startswith("|"):
            header = None
            continue
        cells = [c.strip().replace("**", "") for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if header is None:
            header = cells
            continue
        rows.append("; ".join(f"{h}: {v}" for h, v in zip(header, cells) if v))
    return rows


def _finalise(node: TextNode, meta: dict, kind: str, idx: int) -> TextNode:
    node.metadata = {**meta, **{k: v for k, v in node.metadata.items() if k == "section"}, "chunk_kind": kind}
    node.metadata.setdefault("section", "")
    node.excluded_embed_metadata_keys = [k for k in node.metadata if k not in EMBED_KEEP]
    node.excluded_llm_metadata_keys = [k for k in node.metadata if k not in LLM_KEEP]
    node.id_ = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{meta['doc_id']}::{kind}::{idx}"))
    node.relationships = {}
    return node


def build_nodes(strategy: str, chunk_size: int, chunk_overlap: int) -> list:
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = []
    for entry in load_catalog():
        markdown = (settings.converted_dir.parent.parent / entry["markdown_path"]).read_text(encoding="utf-8")
        meta = base_metadata(entry)
        doc = Document(text=markdown, metadata={})

        if strategy == "fixed":
            for i, n in enumerate(splitter.get_nodes_from_documents([doc])):
                nodes.append(_finalise(n, meta, "text", i))
            continue

        sections = MarkdownNodeParser().get_nodes_from_documents([doc])
        idx = 0
        for sec in sections:
            heading = next((l.lstrip("#").strip() for l in sec.text.splitlines() if l.startswith("#")), "")
            path = sec.metadata.get("header_path", "").strip("/").replace("/", " > ")
            section = " > ".join(p for p in [path, heading] if p) or entry["title"]
            sec_doc = Document(text=sec.text, metadata={"section": section})
            for n in splitter.get_nodes_from_documents([sec_doc]):
                n.metadata["section"] = section
                nodes.append(_finalise(n, meta, "text", idx))
                idx += 1
            if strategy == "structure_no_rows":
                continue
            for r, row in enumerate(table_row_texts(sec.text)):
                row_node = TextNode(text=f"{entry['title']} ({section}) table row: {row}", metadata={"section": section})
                nodes.append(_finalise(row_node, meta, "table_row", idx))
                idx += 1
    return nodes


def build_index(strategy="structure", chunk_size=None, chunk_overlap=None, collection=None, recreate=False) -> dict:
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = settings.chunk_overlap if chunk_overlap is None else chunk_overlap
    collection = collection or settings.collection
    client = get_qdrant_client()

    if recreate and client.collection_exists(collection):
        client.delete_collection(collection)
        log.info("dropped collection %s", collection)

    nodes = build_nodes(strategy, chunk_size, chunk_overlap)
    log.info("strategy=%s chunk_size=%d overlap=%d -> %d nodes", strategy, chunk_size, chunk_overlap, len(nodes))

    store = QdrantVectorStore(client=client, collection_name=collection)
    VectorStoreIndex(nodes, storage_context=StorageContext.from_defaults(vector_store=store),
                     embed_model=get_embed_model(), show_progress=True)

    if not settings.qdrant_path:  # payload indexes speed up filtered search on a Qdrant server
        for field in FILTER_FIELDS:
            client.create_payload_index(collection, field_name=field, field_schema=qm.PayloadSchemaType.KEYWORD)

    stats = {"collection": collection, "strategy": strategy, "chunk_size": chunk_size,
             "chunk_overlap": chunk_overlap, "nodes": len(nodes),
             "documents": len({n.metadata["doc_id"] for n in nodes}),
             "table_row_nodes": sum(1 for n in nodes if n.metadata["chunk_kind"] == "table_row")}
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / f"index_stats_{collection}.json").write_text(json.dumps(stats, indent=2))
    log.info("indexed %s", stats)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Index Docling Markdown into Qdrant with LlamaIndex")
    ap.add_argument("--strategy", choices=["structure", "structure_no_rows", "fixed"], default="structure")
    ap.add_argument("--chunk-size", type=int)
    ap.add_argument("--chunk-overlap", type=int)
    ap.add_argument("--collection")
    ap.add_argument("--recreate", action="store_true", help="Drop and rebuild the collection")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build_index(args.strategy, args.chunk_size, args.chunk_overlap, args.collection, args.recreate)


if __name__ == "__main__":
    main()
