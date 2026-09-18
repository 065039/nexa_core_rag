# Installing the Parser (Docling) on Ubuntu

Deliverable (d). These are the exact steps run on the Classroom 2 Ubuntu machine. `setup.sh` performs all of them; this page lists them one by one so each can be shown with a screenshot.

## 1. Check the machine

```bash
lsb_release -a
python3 --version        # needs 3.10 or newer
hostname -I              # machine IP for deliverable (e)
```

## 2. System packages

Docling uses OpenCV internally, which needs `libgl1` and `libglib2.0-0`.

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git curl libgl1 libglib2.0-0
```

## 3. Virtual environment

```bash
cd nexacore-rag
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
```

## 4. PyTorch, CPU build

Docling's layout and table models run on PyTorch. The default PyPI wheel bundles CUDA libraries and is several GB. The lab machine does not need them, so install the CPU wheel first:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## 5. Docling

```bash
pip install "docling>=2.128,<3"
pip show docling
docling --version
```

## 6. Download the models once

Docling fetches its layout (Heron) and TableFormer models from Hugging Face on first use. Downloading them up front avoids a slow first run:

```bash
docling-tools models download
ls ~/.cache/docling/models
```

## 7. Smoke test from the command line

```bash
docling data/raw/HR/HR_Leave_Policy_2026.pdf --to md --output /tmp/docling_test
cat /tmp/docling_test/HR_Leave_Policy_2026.md
```

The Markdown should show the headings, the leave entitlement table with four rows, and the bullet list.

## 8. Convert the whole repository

```bash
python -m src.parser                  # all departments
python -m src.parser --dept Legal     # one department
python -m src.parser --force --ocr    # redo everything with OCR, for scanned PDFs
```

Output per document in `data/converted/<Department>/`: a `.md` file and a `.json` DoclingDocument. `data/converted/catalog.json` records department, version, status, access level, page and table counts, SHA-256 hash and conversion time. Unchanged files are skipped on the next run because their hash matches.

## 9. Check fidelity

```bash
python scripts/validate_markdown.py
```

This compares each Markdown file with the ground truth in `data/fact_sheet.yaml` and with the source structure: facts found, headings, tables, table cell recall and bullet counts. The report is written to `evaluation/results/parser_fidelity.md`.

## Pipeline settings used

| Setting | Value | Reason |
|---|---|---|
| `do_table_structure` | True | Approval matrices and SLAs are tables |
| `TableFormerMode` | ACCURATE | Small corpus, so accuracy matters more than speed |
| `do_cell_matching` | True | Maps predicted cells back to PDF text |
| `do_ocr` | False by default | Generated PDFs are digital. Turn on for scans |
| XLSX | Sheet names kept as `## Sheet: <name>` headings | Docling maps each sheet to a page but does not print its name |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ImportError: libGL.so.1` | `sudo apt-get install -y libgl1` |
| Hangs on first PDF | It is downloading models. Run step 6 first |
| `403` or timeout reaching huggingface.co | Lab proxy. Export `HTTPS_PROXY` or download models on another network and copy `~/.cache/docling` |
| Very slow PDF conversion | Expected on CPU for the first file while models load. Later files are faster |
