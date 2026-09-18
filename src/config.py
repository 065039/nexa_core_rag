"""Central configuration. Values come from environment variables or the .env file."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    # Paths
    raw_dir: Path = ROOT / "data" / "raw"
    converted_dir: Path = ROOT / "data" / "converted"
    registry_csv: Path = ROOT / "data" / "document_registry.csv"
    roles_file: Path = ROOT / "config" / "roles.yaml"
    cache_dir: Path = ROOT / ".cache"

    # Docling
    docling_ocr: bool = _env("DOCLING_OCR", "false").lower() == "true"
    docling_artifacts_path: str = _env("DOCLING_ARTIFACTS_PATH", "")

    # Vector store (Qdrant server by default; QDRANT_PATH switches to embedded local mode)
    qdrant_url: str = _env("QDRANT_URL", "http://localhost:6333")
    qdrant_path: str = _env("QDRANT_PATH", "")
    collection: str = _env("QDRANT_COLLECTION", "nexacore_docs")

    # Embeddings: "huggingface" (BAAI/bge-small-en-v1.5, runs locally on CPU)
    # "hash" is an offline test backend only, not for the real project run.
    embed_backend: str = _env("EMBED_BACKEND", "huggingface")
    embed_model: str = _env("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    embed_cache_dir: str = _env("EMBED_CACHE_DIR", str(ROOT / ".cache" / "hf"))

    # LLM: "ollama" (Ollama Cloud) or "mock" (offline test backend)
    llm_backend: str = _env("LLM_BACKEND", "ollama")
    ollama_base_url: str = _env("OLLAMA_BASE_URL", "https://ollama.com")
    ollama_api_key: str = _env("OLLAMA_API_KEY", "")
    ollama_model: str = _env("OLLAMA_MODEL", "gpt-oss:120b")
    llm_timeout: float = float(_env("LLM_TIMEOUT", "120"))
    llm_temperature: float = float(_env("LLM_TEMPERATURE", "0.1"))

    # Chunking and retrieval
    chunk_size: int = int(_env("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(_env("CHUNK_OVERLAP", "64"))
    top_k: int = int(_env("TOP_K", "6"))
    top_k_per_department: int = int(_env("TOP_K_PER_DEPARTMENT", "3"))
    similarity_cutoff: float = float(_env("SIMILARITY_CUTOFF", "0.45"))

    departments: tuple = field(default=("HR", "Finance", "IT", "Procurement", "Legal", "Customer_Service"))


settings = Settings()
