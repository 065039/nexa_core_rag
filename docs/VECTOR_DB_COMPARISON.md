# Vector Database Comparison and Selection

The brief allows PostgreSQL (pgvector), Qdrant, Chroma or Supabase (online). We compared them on the needs of this project, then measured the two that run locally without extra database administration.

## What the project needs

1. **Metadata filtering during vector search.** Role-based access, department filters and version status all run as filters on every query. This is the deciding requirement.
2. **Runs on the lab machine.** One Docker container or less, no managed service required.
3. **LlamaIndex support** for filters, including `IN` for the list of allowed access keys.
4. **Data stays on campus.** Policy, contract and salary-band documents should not be sent to a third-party database for a demo.
5. **Room to grow.** Hybrid (dense + sparse) search and a larger corpus later.

## Feature comparison

| Criterion | Qdrant | Chroma | PostgreSQL + pgvector | Supabase (online) |
|---|---|---|---|---|
| What it is | Purpose-built vector DB (Rust), Apache 2.0 | Embedded vector DB for AI apps, Apache 2.0 | Postgres extension adding a vector type and HNSW/IVFFlat indexes | Managed Postgres with pgvector |
| Local setup | One Docker container, or embedded mode in the Python client | `pip install chromadb`, embedded or server | Install Postgres and the extension, create schema | Hosted; self-hosting is a multi-container stack |
| Filtering during search | Payload filters applied inside HNSW search, with payload indexes | `where` filters on metadata | Full SQL `WHERE`, joins | Full SQL via Postgres |
| Filter operators used here (`EQ`, `IN`) | Yes | Yes | Yes | Yes |
| Hybrid search | Native sparse vectors | Mainly dense vector search | Full-text search (`tsvector`) plus vectors, combined manually | Same as Postgres |
| LlamaIndex integration | `llama-index-vector-stores-qdrant` | `llama-index-vector-stores-chroma` | `llama-index-vector-stores-postgres` | Postgres store or `vecs` |
| Admin UI | Built-in web dashboard | None built in | pgAdmin or psql | Supabase Studio |
| Data location | Lab machine | Lab machine | Lab machine | Supabase cloud region |
| Free tier limits | Not applicable locally | Not applicable locally | Not applicable locally | Limited storage; inactive free projects can be paused |
| Best fit | Filter-heavy RAG, growth to hybrid search | Prototypes and notebooks | Teams already running Postgres who want vectors next to relational data | Web apps that want hosted Postgres, auth and APIs together |

## Weighted scoring

Scores from 1 to 5 against the needs above.

| Criterion | Weight | Qdrant | Chroma | pgvector | Supabase |
|---|---|---|---|---|---|
| Filtered search quality and speed | 30% | 5 | 4 | 4 | 4 |
| Ease of setup in the lab | 20% | 4 | 5 | 3 | 3 |
| LlamaIndex filter support | 15% | 5 | 4 | 5 | 4 |
| Data stays local | 15% | 5 | 5 | 5 | 2 |
| Hybrid search and scale later | 10% | 5 | 3 | 4 | 4 |
| Tooling and observability | 10% | 4 | 2 | 4 | 5 |
| **Weighted total** | 100% | **4.70** | **4.05** | **4.10** | **3.60** |

## Measured results

`python scripts/benchmark_vector_dbs.py` indexes the same chunks with the same bge-small embeddings into Qdrant (Docker) and Chroma, then times plain and department-filtered queries and checks Hit@5 on the evaluation questions. Paste `evaluation/results/vector_db_benchmark.md` here after running it in the lab.

| database | nodes | index_seconds | mean_query_ms | p95_query_ms | mean_filtered_query_ms | hit@5 |
|---|---|---|---|---|---|---|
| Qdrant | | | | | | |
| Chroma | | | | | | |

Retrieval quality (Hit@5) should be nearly identical because both use the same embeddings and cosine similarity. The difference shows up in filtering, operations and future features, which is why the weighted table above carries the decision.

## Decision

**Qdrant.** Every query in this system is a filtered query (role, department, status), and Qdrant applies those filters inside the vector search with indexed payload fields. It runs as a single container on the lab machine, so the documents never leave campus. The dashboard at `http://localhost:6333/dashboard` makes it easy to show the stored chunks and their metadata during the demo. Native sparse vectors mean hybrid search can be added without changing databases.

pgvector (4.10) and Chroma (4.05) finished close together. Chroma is the easiest to start with and suits a notebook prototype. pgvector makes sense when the organization already runs Postgres, but it costs more setup time in the lab. Supabase was ruled out for this project because it sends internal documents to a hosted service and its free tier pauses inactive projects, which is a risk for a scheduled demo.
