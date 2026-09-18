"""
Parser fidelity check: compares Docling Markdown output against the ground truth.

Checks per document:
  1. Fact recall   - every "must_contain" string from data/fact_sheet.yaml appears in the Markdown
  2. Headings      - number of headings in the source vs the Markdown
  3. Tables        - number of tables in the source vs the Markdown
  4. Table cells   - share of source table cell values found in the Markdown
  5. Bullets       - number of bullet items in the source vs the Markdown

Writes evaluation/results/parser_fidelity.csv and evaluation/results/parser_fidelity.md

Usage:
    python scripts/validate_markdown.py
"""
import csv
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from corpus import DOCUMENTS  # noqa: E402

CONVERTED = ROOT / "data" / "converted"
OUT = ROOT / "evaluation" / "results"


def normalise(text: str) -> str:
    text = text.replace("**", "").replace("\\_", "_").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text)


def source_structure(doc: dict) -> dict:
    if "sheets" in doc:
        tables = list(doc["sheets"].values())
        return {"headings": 0, "tables": len(tables), "bullets": 0, "cells": [c for t in tables for r in t for c in r]}
    blocks = doc["blocks"]
    tables = [c for k, c in blocks if k == "table"]
    return {
        "headings": sum(1 for k, _ in blocks if k in ("h1", "h2")),
        "tables": len(tables),
        "bullets": sum(len(c) for k, c in blocks if k == "bullets"),
        "cells": [c for t in tables for r in t for c in r],
    }


def markdown_structure(md: str) -> dict:
    lines = md.splitlines()
    table_count, in_table = 0, False
    for line in lines:
        is_row = line.strip().startswith("|")
        if is_row and not in_table:
            table_count += 1
        in_table = is_row
    return {
        "headings": sum(1 for l in lines if re.match(r"^#{1,6} ", l) and not l.startswith("## Sheet:")),
        "tables": table_count,
        "bullets": sum(1 for l in lines if re.match(r"^\s*[-*] ", l)),
    }


def main() -> None:
    facts = yaml.safe_load((ROOT / "data" / "fact_sheet.yaml").read_text())["facts"]
    rows = []
    for doc in DOCUMENTS:
        stem = Path(doc["file"]).stem
        md_path = CONVERTED / doc["department"] / f"{stem}.md"
        if not md_path.exists():
            rows.append({"document": Path(doc["file"]).name, "status": "MISSING"})
            continue
        md = md_path.read_text(encoding="utf-8")
        norm = normalise(md)
        src, out = source_structure(doc), markdown_structure(md)

        doc_facts = facts.get(stem, [])
        found = sum(1 for f in doc_facts if all(normalise(s) in norm for s in f["must_contain"]))
        missed = [f["fact"] for f in doc_facts if not all(normalise(s) in norm for s in f["must_contain"])]
        cells_found = sum(1 for c in src["cells"] if normalise(str(c)) in norm)

        rows.append({
            "document": Path(doc["file"]).name,
            "status": "OK",
            "fact_recall": f"{found}/{len(doc_facts)}",
            "headings_src_md": f"{src['headings']}/{out['headings']}",
            "tables_src_md": f"{src['tables']}/{out['tables']}",
            "table_cell_recall": f"{(cells_found / len(src['cells']) * 100):.0f}%" if src["cells"] else "n/a",
            "bullets_src_md": f"{src['bullets']}/{out['bullets']}",
            "missed_facts": "; ".join(missed),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["document", "status", "fact_recall", "headings_src_md", "tables_src_md",
              "table_cell_recall", "bullets_src_md", "missed_facts"]
    with (OUT / "parser_fidelity.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    ok = [r for r in rows if r["status"] == "OK"]
    total_found = sum(int(r["fact_recall"].split("/")[0]) for r in ok)
    total_facts = sum(int(r["fact_recall"].split("/")[1]) for r in ok)
    lines = ["# Docling Parser Fidelity Report", "",
             f"Documents converted: {len(ok)}/{len(rows)}  ",
             f"Overall fact recall: {total_found}/{total_facts}"
             + (f" ({total_found / total_facts * 100:.1f}%)" if total_facts else ""), "",
             "| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    lines += ["| " + " | ".join(str(r.get(f, "")) for f in fields) + " |" for r in rows]
    (OUT / "parser_fidelity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
