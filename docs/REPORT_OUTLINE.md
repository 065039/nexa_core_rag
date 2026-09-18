# Report Outline: Architecture and Results

Deliverable (f). Target length 15 to 20 pages. Each section lists what to write and which file or screenshot supplies it. Only report numbers measured on the lab machine.

## 1. Abstract (150 words)
Problem, approach (Docling, LlamaIndex, Qdrant, Ollama Cloud, Streamlit), three headline results (fact recall, Hit@5, answer accuracy).

## 2. Problem Statement and Objectives
Employees search across six departments' documents in three formats. Objectives: faithful conversion, grounded answers with sources, access by role, cross-department questions, web access.

## 3. Organization and Dataset
- NexaCore's six departments and document owners
- Table of 18 documents: department, format, version, status, access level (`data/document_registry.csv`)
- Why synthetic: no confidential data, and a known ground truth (`data/fact_sheet.yaml`)
- Planted test cases: 2025 vs 2026 leave policy, HR vs Finance expense deadline conflict, 3 restricted documents, vendor onboarding across 4 departments

## 4. Document Parsing (Part-I)
- Why Docling: layout model, TableFormer, DOCX/XLSX backends, Markdown and JSON export, runs locally. One paragraph on MinerU as the alternative and why it was not chosen (heavier install aimed at GPU machines, and focused on PDFs and images while this corpus also has DOCX and XLSX).
- Installation summary (`docs/INSTALL_DOCLING.md`), screenshot of `pip show docling`
- Pipeline settings table
- Screenshot: original PDF page next to its Markdown
- **Results:** `evaluation/results/parser_fidelity.md` (fact recall, table cell recall, heading and bullet counts, conversion time from `catalog.json`)

## 5. Vector Database Selection
Copy `docs/VECTOR_DB_COMPARISON.md`: needs, feature table, weighted scores, benchmark table, decision.

## 6. System Architecture
- Mermaid diagram from `README.md` exported as an image
- Component table: file, responsibility, technology
- Metadata schema stored in Qdrant (department, status, access_key, section, version, chunk_kind)

## 7. RAG Pipeline (Part-II)
- Chunking: headings first, then 512-token splits with 64 overlap, plus table-row nodes. Show one table-row node.
- Embeddings: bge-small-en-v1.5 (384 dimensions, CPU)
- Retrieval: role filter, department filter, status filter, cross-department fan-out with a 0.15 score window, similarity cutoff
- Generation: Ollama Cloud model name, temperature 0.1, prompt rules (quote the prompt from `src/rag.py`), caching and retry for free-tier limits
- Not-found and restricted handling

## 8. Web Interface and Deployment
Screenshots on laptop and phone, role and department selectors, sources panel, Cloudflare Tunnel setup, audit log sample.

## 9. Evaluation Method
- 23 questions in 9 categories (`evaluation/questions.jsonl`)
- Metric definitions: Hit@k, MRR, coverage@5, access_ok, answer accuracy (keyword match or correct refusal), citation accuracy, faithfulness and relevancy (LlamaIndex evaluators with the Ollama model as judge), latency

## 10. Results
- Overall and per-category table (`evaluation/results/rag_eval.md`)
- Chunking ablation table (`evaluation/results/ablation.md`) and 3 to 4 sentences on what it shows, especially the effect of table-row nodes on table questions
- Three worked examples with full answers: cross-department, conflict, restricted
- Failure analysis: list each wrong answer, why it failed (retrieval miss, generation error, keyword too strict), and the fix

## 11. Security and Governance
Role-based filtering at retrieval time (not only in the UI), prompt-injection rule, audit log without storing answers, API keys in `.env`, local vector DB, version status.

## 12. Limitations
Synthetic and short documents, small question set, keyword-based answer scoring, LLM judge uses the same model family, free-tier latency, roles chosen in the UI without login.

## 13. Future Scope
Login with SSO mapped to roles, hybrid search with Qdrant sparse vectors, reranker, page-level citations from Docling JSON, scanned-document OCR, document upload flow with automatic re-indexing, conflict detection as a separate check.

## 14. Conclusion

## Appendices
A. Installation steps  B. Machine IP screenshot (`scripts/get_ip.sh`)  C. Coding agent prompts  D. Full question set
