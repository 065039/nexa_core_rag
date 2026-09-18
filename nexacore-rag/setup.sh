#!/usr/bin/env bash
# NexaCore RAG: one-command setup for Ubuntu 22.04 / 24.04 (Classroom 2 lab or WSL Ubuntu).
# Usage:  bash setup.sh
# Safe to re-run. Logs go to setup.log.
set -euo pipefail
cd "$(dirname "$0")"
exec > >(tee -a setup.log) 2>&1

step() { echo; echo "==== $1"; }

step "1/8 System information (screenshot this for the report)"
lsb_release -a 2>/dev/null || cat /etc/os-release
uname -a
python3 --version
echo "Machine IP: $(hostname -I | awk '{print $1}')"

step "2/8 System packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git curl libgl1 libglib2.0-0

step "3/8 Python virtual environment"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install --upgrade pip wheel

step "4/8 PyTorch (CPU build, much smaller than the default CUDA build)"
if ! python -c "import torch" 2>/dev/null; then
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

step "5/8 Project requirements (Docling, LlamaIndex, Qdrant client, Streamlit)"
pip install -r requirements.txt
pip show docling | head -2
docling --version || true

step "6/8 Pre-download Docling models and the embedding model"
docling-tools models download
python - <<'EOF'
from sentence_transformers import SentenceTransformer
SentenceTransformer("BAAI/bge-small-en-v1.5", cache_folder=".cache/hf")
print("bge-small-en-v1.5 cached")
EOF

step "7/8 Environment file"
if [ ! -f .env ]; then cp .env.example .env; echo "Created .env. Add your OLLAMA_API_KEY to it."; fi

step "8/8 Qdrant vector database (Docker)"
if command -v docker >/dev/null 2>&1; then
  docker compose up -d || sudo docker compose up -d
  sleep 5
  curl -s http://localhost:6333/collections && echo
else
  echo "Docker not found. Either install Docker or set QDRANT_PATH=.qdrant_local in .env"
fi

cat <<'EOF'

Setup complete. Next steps:
  source .venv/bin/activate
  nano .env                                   # add OLLAMA_API_KEY
  python scripts/check_ollama.py              # confirm Ollama Cloud access and pick a model
  python -m src.parser                        # Part-I: Docling conversion to Markdown
  python scripts/validate_markdown.py         # parser fidelity report
  python -m src.indexing --recreate           # chunk, embed, store in Qdrant
  python -m src.rag "Who approves a purchase of INR 3,00,000?"
  streamlit run app/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
EOF
