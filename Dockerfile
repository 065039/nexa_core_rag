# NexaCore RAG image: Ubuntu 22.04 + Docling + LlamaIndex + Streamlit, with all models baked in.
# Build it on a machine WITH internet (e.g. Windows Docker Desktop). Once built, it runs Part-I
# (parsing) and indexing with NO internet. Only the Ollama Cloud answer step needs internet.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip libgl1 libglib2.0-0 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && pip install --upgrade pip wheel

# CPU-only PyTorch keeps the image several GB smaller than the default CUDA build
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download Docling layout/table models and the bge-small embedding model into the image
RUN docling-tools models download -o /opt/models/docling \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5', cache_folder='/opt/models/hf')"

# From here on, never try to reach Hugging Face: use the baked-in models
ENV DOCLING_ARTIFACTS_PATH=/opt/models/docling \
    EMBED_CACHE_DIR=/opt/models/hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY . /app

EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
