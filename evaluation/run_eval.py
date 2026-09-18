"""
RAG evaluation on the ground-truth question set (evaluation/questions.jsonl).

Metrics
  Retrieval   Hit@1, Hit@3, Hit@5 (any expected document in top k), MRR, expected-document coverage@5
  Access      restricted documents never retrieved for roles without access
  Answers     answer accuracy (expected keywords present, or correct "not found"), citation accuracy
  Judge       faithfulness and relevancy with LlamaIndex evaluators (optional, uses Ollama Cloud)
  Speed       mean and p95 latency

Modes
  python -m evaluation.run_eval                    full run (retrieval + answers)
  python -m evaluation.run_eval --judge            also run LLM-as-judge faithfulness/relevancy
  python -m evaluation.run_eval --retrieval-only   no LLM calls (free, fast)
  python -m evaluation.run_eval --ablation         chunking strategy x chunk size study (retrieval only)

Run full and judge modes at off-peak hours: they call Ollama Cloud. Responses are cached in .cache/.
"""
import argparse
import csv
import json
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

from src.config import settings
from src.indexing import build_index
from src.rag import NexaCoreRAG

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "evaluation" / "questions.jsonl"
RESULTS = ROOT / "evaluation" / "results"


def load_questions() -> list:
    return [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("**", ""))


def keywords_ok(answer: str, groups: list) -> bool:
    a = norm(answer)
    return all(any(norm(alt) in a for alt in group) for group in groups)


def retrieval_metrics(q: dict, ranked_docs: list, retrieved_meta: list) -> dict:
    expected = set(q.get("expected_docs", []))
    out = {}
    if expected:
        first = next((i for i, d in enumerate(ranked_docs, 1) if d in expected), None)
        for k in (1, 3, 5):
            out[f"hit@{k}"] = int(first is not None and first <= k)
        out["rr"] = 1.0 / first if first else 0.0
        out["coverage@5"] = len(expected & set(ranked_docs[:5])) / len(expected)
    restricted = set(q.get("restricted_docs", []))
    if restricted:
        out["access_ok"] = int(not (restricted & {m["doc_id"] for m in retrieved_meta}))
    return out


def unique_in_order(items: list) -> list:
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def evaluate_retrieval(engine: NexaCoreRAG, questions: list) -> list:
    rows = []
    for q in questions:
        t0 = time.perf_counter()
        nodes = engine.retrieve(q["question"], q.get("role", "Employee"), q.get("department", "All"),
                                q.get("include_superseded", False))
        meta = [n.node.metadata for n in nodes]
        ranked = unique_in_order([m["doc_id"] for m in meta])
        rows.append({"id": q["id"], "category": q["category"], "retrieved_docs": ranked[:5],
                     "top_score": round(float(nodes[0].score), 4) if nodes else 0.0,
                     "retrieval_ms": round((time.perf_counter() - t0) * 1000, 1),
                     **retrieval_metrics(q, ranked, meta)})
    return rows


def summarise(rows: list) -> dict:
    def mean(key):
        vals = [r[key] for r in rows if key in r and r[key] is not None]
        return round(statistics.mean(vals), 3) if vals else None

    def p95(key):
        vals = sorted(r[key] for r in rows if key in r)
        return round(vals[max(0, int(len(vals) * 0.95) - 1)], 1) if vals else None

    s = {"questions": len(rows)}
    for k in ("hit@1", "hit@3", "hit@5", "rr", "coverage@5", "access_ok", "answer_correct",
              "citation_correct", "faithfulness", "relevancy"):
        s["mrr" if k == "rr" else k] = mean(k)
    for k in ("retrieval_ms", "total_ms"):
        s[f"mean_{k}"] = mean(k)
        s[f"p95_{k}"] = p95(k)
    return s


def by_category(rows: list) -> dict:
    cats = {}
    for r in rows:
        cats.setdefault(r["category"], []).append(r)
    return {c: summarise(rs) for c, rs in cats.items()}


def write_outputs(name: str, rows: list, summary: dict, extra_md: str = "") -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("id", "category", "question"), k))
    with (RESULTS / f"{name}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in r.items()})
    (RESULTS / f"{name}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if extra_md:
        (RESULTS / f"{name}.md").write_text(extra_md, encoding="utf-8")


def md_table(header: list, rows: list) -> str:
    fmt = lambda v: "" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def run_full(judge: bool, retrieval_only: bool) -> None:
    engine = NexaCoreRAG()
    questions = load_questions()
    if retrieval_only:
        rows = evaluate_retrieval(engine, questions)
    else:
        rows = []
        if judge:
            from llama_index.core.evaluation import FaithfulnessEvaluator, RelevancyEvaluator
            faith = FaithfulnessEvaluator(llm=engine.llm.llm)
            relev = RelevancyEvaluator(llm=engine.llm.llm)
        for q in questions:
            r = engine.answer(q["question"], q.get("role", "Employee"), q.get("department", "All"),
                              q.get("include_superseded", False))
            meta = [{"doc_id": Path(s.source_file).stem} for s in r.sources]
            ranked = unique_in_order([m["doc_id"] for m in meta])
            row = {"id": q["id"], "category": q["category"], "question": q["question"], "role": r.role,
                   "status": r.status, "answer": r.answer, "retrieved_docs": ranked[:5],
                   "top_score": r.sources[0].score if r.sources else 0.0,
                   "cited_docs": unique_in_order([Path(s.source_file).stem for s in r.sources if s.cited]),
                   "retrieval_ms": r.retrieval_ms, "total_ms": r.total_ms, "cache_hit": r.cache_hit,
                   **retrieval_metrics(q, ranked, meta)}
            if q.get("expect_not_found"):
                row["answer_correct"] = int(r.status in ("not_found", "restricted"))
            else:
                row["answer_correct"] = int(r.status == "answered" and keywords_ok(r.answer, q.get("expected_keywords", [])))
                row["citation_correct"] = int(bool(set(row["cited_docs"]) & set(q.get("expected_docs", []))))
            if judge and r.status == "answered" and engine.llm.llm is not None:
                contexts = [s.text for s in r.sources]
                row["faithfulness"] = float(faith.evaluate(query=q["question"], response=r.answer, contexts=contexts).score or 0)
                row["relevancy"] = float(relev.evaluate(query=q["question"], response=r.answer, contexts=contexts).score or 0)
            rows.append(row)
            print(f"{q['id']} {q['category']:<20} {r.status:<10} correct={row['answer_correct']} "
                  f"hit@5={row.get('hit@5', '-')} {r.total_ms:.0f}ms")

    summary = {"run_at": datetime.now().isoformat(timespec="seconds"), "model": engine.llm.model_name,
               "embed_model": settings.embed_model if settings.embed_backend != "hash" else "hash-test",
               "collection": engine.collection, "chunk_size": settings.chunk_size,
               "overall": summarise(rows), "by_category": by_category(rows)}
    name = "retrieval_eval" if retrieval_only else "rag_eval"
    cols = ["hit@1", "hit@3", "hit@5", "mrr", "coverage@5", "answer_correct", "citation_correct", "mean_total_ms"]
    table_rows = [["overall"] + [summary["overall"].get(c) for c in cols]]
    table_rows += [[c] + [s.get(k) for k in cols] for c, s in summary["by_category"].items()]
    md = (f"# NexaCore RAG Evaluation ({name})\n\nModel: {summary['model']}  \nEmbeddings: {summary['embed_model']}  \n"
          f"Run at: {summary['run_at']}\n\n" + md_table(["scope"] + cols, table_rows) + "\n")
    write_outputs(name, rows, summary, md)
    print("\n" + md)


def run_ablation(strategies: list, sizes: list) -> None:
    questions = [q for q in load_questions() if q.get("expected_docs")]
    results = []
    for strategy in strategies:
        for size in sizes:
            collection = f"ablation_{strategy}_{size}"
            stats = build_index(strategy, size, max(16, size // 8), collection, recreate=True)
            summary = summarise(evaluate_retrieval(NexaCoreRAG(collection), questions))
            results.append({"strategy": strategy, "chunk_size": size, "nodes": stats["nodes"], **summary})
            print(f"{strategy:<10} {size:>5}  nodes={stats['nodes']:<4} hit@1={summary['hit@1']} "
                  f"hit@5={summary['hit@5']} mrr={summary['mrr']} coverage@5={summary['coverage@5']}")
    cols = ["strategy", "chunk_size", "nodes", "hit@1", "hit@3", "hit@5", "mrr", "coverage@5", "mean_retrieval_ms"]
    md = ("# Chunking Ablation (retrieval only)\n\n"
          f"Embeddings: {settings.embed_model if settings.embed_backend != 'hash' else 'hash-test'}  \n"
          f"Questions with a known source: {len(questions)}\n\n"
          + md_table(cols, [[r.get(c) for c in cols] for r in results]) + "\n")
    write_outputs("ablation", results, {"results": results}, md)
    print("\n" + md)


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate the NexaCore RAG engine")
    ap.add_argument("--judge", action="store_true", help="LLM-as-judge faithfulness and relevancy")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--strategies", nargs="*", default=["fixed", "structure_no_rows", "structure"])
    ap.add_argument("--sizes", nargs="*", type=int, default=[128, 256, 512])
    args = ap.parse_args()
    if args.ablation:
        run_ablation(args.strategies, args.sizes)
    else:
        run_full(args.judge, args.retrieval_only)


if __name__ == "__main__":
    main()
