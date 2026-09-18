# 48-Hour Team Plan

| When | Member 1: Data and parsing | Member 2: RAG and evaluation | Member 3: App, deployment, report |
|---|---|---|---|
| Day 1 morning | Download the zip from email, unzip in the home folder, run `bash setup.sh` on the lab machine. Screenshot every step for `INSTALL_DOCLING.md` | Get an Ollama Cloud key, run `scripts/check_ollama.py`, set `OLLAMA_MODEL` | Start the report from `docs/REPORT_OUTLINE.md` (sections 1 to 3) |
| Day 1 afternoon | `python -m src.parser`, `scripts/validate_markdown.py`. Screenshot PDF next to Markdown. Fix anything that fails | `python -m src.indexing --recreate`, try 10 questions with `src.rag`, tune `SIMILARITY_CUTOFF` | Run Streamlit, set up the Cloudflare tunnel, test on two phones |
| Day 2 morning (off-peak) | `scripts/benchmark_vector_dbs.py`, fill the benchmark table | `run_eval --ablation`, then `run_eval --judge` | Screenshots of the app on laptop and phone, `scripts/get_ip.sh` screenshot |
| Day 2 afternoon | Report sections 4 and 5 | Report sections 7, 9 and 10 including failure analysis | Report sections 6, 8, 11 to 14. Fill `CODING_AGENT_PROMPTS.md`. Submit |

## Checks before submitting

- [ ] `evaluation/results/` contains only numbers from the lab machine
- [ ] `.env`, `.venv` and `qdrant_storage` are not in the submission zip (use the zip command in README)
- [ ] IP screenshot taken while the app is running
- [ ] All prompts from every member are in `docs/CODING_AGENT_PROMPTS.md`
- [ ] Demo script in `docs/DEPLOYMENT.md` rehearsed once
