# Chunking Ablation (retrieval only)

Embeddings: BAAI/bge-small-en-v1.5  
Questions with a known source: 20

| strategy | chunk_size | nodes | hit@1 | hit@3 | hit@5 | mrr | coverage@5 | mean_retrieval_ms |
|---|---|---|---|---|---|---|---|---|
| fixed | 128 | 49 | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 | 29.89 |
| fixed | 256 | 24 | 0.90 | 1 | 1 | 0.93 | 1.00 | 39.12 |
| fixed | 512 | 18 | 0.90 | 0.95 | 1 | 0.93 | 1.00 | 25.26 |
| structure_no_rows | 128 | 85 | 1 | 1 | 1 | 1.00 | 1.00 | 84.33 |
| structure_no_rows | 256 | 80 | 1 | 1 | 1 | 1.00 | 1.00 | 74.09 |
| structure_no_rows | 512 | 80 | 1 | 1 | 1 | 1.00 | 1.00 | 85.00 |
| structure | 128 | 147 | 1 | 1 | 1 | 1.00 | 1.00 | 120.19 |
| structure | 256 | 142 | 1 | 1 | 1 | 1.00 | 1.00 | 102.25 |
| structure | 512 | 142 | 1 | 1 | 1 | 1.00 | 1.00 | 105.12 |
