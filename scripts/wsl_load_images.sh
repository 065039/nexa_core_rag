#!/usr/bin/env bash
# Run in UBUNTU (WSL). Loads the images built on Windows. No internet needed.
# Usage:  bash scripts/wsl_load_images.sh [path/to/nexacore-images.tar]
set -euo pipefail
cd "$(dirname "$0")/.."

TAR="${1:-docker-images/nexacore-images.tar}"
[ -f "$TAR" ] || { echo "Not found: $TAR (build it on Windows first)"; exit 1; }

DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

echo "==== Loading $TAR (a few minutes)"
$DOCKER load -i "$TAR"
$DOCKER image ls | grep -E "REPOSITORY|nexacore-rag|qdrant"

[ -f .env ] || cp .env.example .env

echo "==== Checking Docling and models inside the image (offline)"
$DOCKER run --rm --network none nexacore-rag:latest bash -c \
  "pip show docling | head -2 && ls /opt/models/docling && ls /opt/models/hf"

cat <<'EOF'

Images loaded. Next:
  docker compose -f docker-compose.offline.yml up -d qdrant
  docker compose -f docker-compose.offline.yml run --rm app python -m src.parser
  docker compose -f docker-compose.offline.yml run --rm app python scripts/validate_markdown.py
  docker compose -f docker-compose.offline.yml run --rm app python -m src.indexing --recreate
EOF
