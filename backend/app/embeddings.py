"""Embedding-Client für das lokale Ollama-Modell (nomic-embed-text, 768-dim).

Vollständig lokal — keine Daten verlassen die Infrastruktur (siehe ADR 0001).
"""
from __future__ import annotations

import httpx

from .config import settings


def embed_texts(texts: list[str], batch: int = 32) -> list[list[float]]:
    """Berechnet Embeddings für eine Liste von Texten (gebatcht)."""
    out: list[list[float]] = []
    with httpx.Client(timeout=120) as client:
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            r = client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": chunk},
            )
            r.raise_for_status()
            out.extend(r.json()["embeddings"])
    return out


def embed_one(text: str) -> list[float]:
    return embed_texts([text])[0]


def to_pgvector(vec: list[float]) -> str:
    """Formatiert einen Vektor als pgvector-Literal '[...]'."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"
