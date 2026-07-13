"""Deterministic, offline embedding backend (MASTER_SPEC §30.2, epic #34).

The semantic fallback needs to compare an unknown concept against Knowledge Base
entries **without any network call, extra dependency, or nondeterminism**. This
module provides a small ``embed(texts) -> vectors`` abstraction and a default
character-n-gram implementation that satisfies those constraints:

- **Offline & dependency-free** — pure standard library; no model download.
- **Deterministic** — the same text always maps to the same vector (no random
  seed, no hardware-dependent floats beyond IEEE arithmetic).
- **Sparse** — a vector is a mapping of character n-gram → weight, so the committed
  Knowledge Base index (epic #34, #115) stays small.

Because the index embeds each entry's canonical text **and its aliases**, a query
matches an entry when it is lexically close to any of the entry's surface forms
(e.g. ``stockings`` matches the ``thighhighs`` entry via its ``stockings`` alias).
Retrieval therefore never invents a tag — it can only return an existing entry.
"""

from __future__ import annotations

import math
import unicodedata
from typing import Protocol

# A sparse embedding: character n-gram -> L2-normalized weight.
SparseVector = dict[str, float]

DEFAULT_BACKEND = "char_ngram"
_NGRAM_SIZE = 3
_PAD = "\x02"  # a boundary marker so prefixes/suffixes get their own n-grams


class EmbeddingBackend(Protocol):
    """A text embedding backend: turn texts into comparable sparse vectors."""

    def embed(self, texts: list[str]) -> list[SparseVector]: ...


def _normalize_text(text: str) -> str:
    """Lowercase, NFKC-normalize, and collapse whitespace/underscores."""
    folded = unicodedata.normalize("NFKC", text).replace("_", " ").lower()
    return " ".join(folded.split())


class CharNGramEmbeddingBackend:
    """Character-n-gram bag-of-features embedding (deterministic, offline)."""

    def __init__(self, ngram_size: int = _NGRAM_SIZE) -> None:
        self._n = ngram_size

    def embed(self, texts: list[str]) -> list[SparseVector]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> SparseVector:
        normalized = _normalize_text(text)
        if not normalized:
            return {}
        padded = _PAD + normalized + _PAD
        counts: SparseVector = {}
        for i in range(len(padded) - self._n + 1):
            gram = padded[i : i + self._n]
            counts[gram] = counts.get(gram, 0.0) + 1.0
        norm = math.sqrt(sum(weight * weight for weight in counts.values()))
        return {gram: weight / norm for gram, weight in counts.items()}


def get_backend(backend_id: str = DEFAULT_BACKEND) -> EmbeddingBackend:
    """Return the embedding backend for a config id.

    Raises:
        ValueError: If ``backend_id`` is not a known backend.
    """
    if backend_id == DEFAULT_BACKEND:
        return CharNGramEmbeddingBackend()
    raise ValueError(f"Unknown embedding backend '{backend_id}'.")


def cosine_similarity(a: SparseVector, b: SparseVector) -> float:
    """Cosine similarity of two L2-normalized sparse vectors (their dot product)."""
    if not a or not b:
        return 0.0
    # Iterate the smaller vector for speed; both are unit-normalized.
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    return sum(weight * large.get(gram, 0.0) for gram, weight in small.items())
