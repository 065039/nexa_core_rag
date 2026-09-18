"""Embedding model and LLM factories, plus a cached, retrying LLM call for Ollama Cloud."""
import hashlib
import json
import logging
import re
import threading
from typing import List

import numpy as np
from llama_index.core.base.embeddings.base import BaseEmbedding
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

log = logging.getLogger("models")


# ----------------------------------------------------------------------------- embeddings
class HashEmbedding(BaseEmbedding):
    """Offline lexical embedding (hashed unigrams + bigrams). Only for testing without internet.
    The real project uses BAAI/bge-small-en-v1.5."""

    dim: int = 2048

    def _vec(self, text: str) -> List[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        v = np.zeros(self.dim, dtype=np.float32)
        for g in grams:
            v[int(hashlib.md5(g.encode()).hexdigest(), 16) % self.dim] += 1.0
        n = np.linalg.norm(v)
        return (v / n if n else v).tolist()

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._vec(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._vec(text)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._vec(query)


def get_embed_model():
    if settings.embed_backend == "hash":
        log.warning("Using offline HashEmbedding test backend")
        return HashEmbedding(model_name="hash-test")
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    return HuggingFaceEmbedding(model_name=settings.embed_model, device="cpu",
                                cache_folder=settings.embed_cache_dir)


# ----------------------------------------------------------------------------- LLM
def get_llm():
    if settings.llm_backend == "mock":
        return None
    from llama_index.llms.ollama import Ollama
    headers = {"Authorization": f"Bearer {settings.ollama_api_key}"} if settings.ollama_api_key else None
    return Ollama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        headers=headers,
        request_timeout=settings.llm_timeout,
        temperature=settings.llm_temperature,
        context_window=32000,
    )


class CachedLLM:
    """Wraps the LLM with a disk cache and exponential-backoff retries.
    The cache keeps repeated evaluation runs off the Ollama Cloud free-tier quota."""

    def __init__(self):
        self.llm = get_llm()
        self.model_name = "mock-extractive" if self.llm is None else settings.ollama_model
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.cache_dir / "llm_cache.jsonl"
        self.lock = threading.Lock()
        self.cache = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    self.cache[row["key"]] = row["response"]
                except (json.JSONDecodeError, KeyError):
                    continue

    def _key(self, prompt: str) -> str:
        return hashlib.sha256(f"{self.model_name}\n{prompt}".encode()).hexdigest()

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30), reraise=True)
    def _call(self, prompt: str) -> str:
        return self.llm.complete(prompt).text

    def complete(self, prompt: str, use_cache: bool = True, mock_context: list = None) -> tuple:
        """Returns (text, cache_hit)."""
        if self.llm is None:
            return self._mock(mock_context or []), False
        key = self._key(prompt)
        if use_cache and key in self.cache:
            return self.cache[key], True
        text = self._call(prompt)
        with self.lock:
            self.cache[key] = text
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"key": key, "model": self.model_name, "response": text}) + "\n")
        return text, False

    @staticmethod
    def _mock(context: list) -> str:
        """Extractive stand-in used only for offline tests: returns the best source chunk."""
        if not context:
            return "INSUFFICIENT_EVIDENCE"
        return f"{context[0][:400]} [S1]"
