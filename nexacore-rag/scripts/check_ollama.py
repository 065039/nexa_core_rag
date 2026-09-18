"""
Check Ollama Cloud access before building anything on top of it.

  1. Lists the models your API key can see
  2. Sends one short test prompt to OLLAMA_MODEL and reports latency

Usage:
    python scripts/check_ollama.py
    python scripts/check_ollama.py --model gemma4:31b
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama import Client  # installed with llama-index-llms-ollama

from src.config import settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=settings.ollama_model)
    args = ap.parse_args()

    if not settings.ollama_api_key:
        sys.exit("OLLAMA_API_KEY is empty. Create a key at https://ollama.com/settings/keys and put it in .env")

    client = Client(host=settings.ollama_base_url, headers={"Authorization": f"Bearer {settings.ollama_api_key}"})

    print(f"Models available at {settings.ollama_base_url}:")
    names = []
    for m in client.list().models:
        names.append(m.model)
        print(f"  - {m.model}")
    if args.model not in names:
        print(f"\nWARNING: '{args.model}' is not in the list above. Set OLLAMA_MODEL in .env to one that is.")

    print(f"\nTest prompt to {args.model} ...")
    start = time.perf_counter()
    reply = client.chat(model=args.model, messages=[{"role": "user", "content": "Reply with the word READY only."}])
    print(f"Reply: {reply.message.content.strip()!r}  ({time.perf_counter() - start:.1f}s)")
    print("Ollama Cloud is working.")


if __name__ == "__main__":
    main()
