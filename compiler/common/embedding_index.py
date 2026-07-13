"""Knowledge Base embedding index (MASTER_SPEC §30.2, epic #34, #115).

A committed snapshot that maps embedding vectors back to **existing** Knowledge
Base entry ids, so the semantic fallback can only ever return a real entry — it
can never invent a tag. Each entry contributes one row per surface form (its
canonical id-as-words, its tags, and its aliases), so a query matches an entry
when it is close to any of that entry's surfaces (``stockings`` → the
``thighhighs`` entry via its ``stockings`` alias).

The index is built offline by ``scripts/build_embedding_index.py`` and committed
under ``data/`` so CI never recomputes embeddings. :class:`EmbeddingIndex` reads
it once and reuses it for nearest-neighbour search.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from compiler.common.embedding import (
    DEFAULT_BACKEND,
    EmbeddingBackend,
    SparseVector,
    cosine_similarity,
    get_backend,
)
from compiler.common.knowledge_base import KnowledgeBase

# Weights are rounded when serialized to keep the committed artifact compact and
# its regeneration byte-stable.
_WEIGHT_PRECISION = 6


def _entry_surfaces(entry) -> list[str]:
    """The distinct surface texts of an entry: id-as-words, tags, and aliases."""
    surfaces = [entry.id.replace("_", " "), *entry.tags, *entry.aliases]
    seen: set[str] = set()
    ordered: list[str] = []
    for surface in surfaces:
        if surface not in seen:
            seen.add(surface)
            ordered.append(surface)
    return ordered


def build_index_rows(
    knowledge_base: KnowledgeBase, backend: EmbeddingBackend | None = None
) -> list[dict]:
    """Build the index rows ``[{"id", "surface", "vector"}, ...]`` deterministically.

    Entries are visited in sorted id order and surfaces in their listed order, so
    the artifact is byte-stable for a given Knowledge Base.
    """
    backend = backend or get_backend(DEFAULT_BACKEND)
    rows: list[dict] = []
    for entry_id in sorted(knowledge_base.by_id):
        entry = knowledge_base.by_id[entry_id]
        surfaces = _entry_surfaces(entry)
        vectors = backend.embed(surfaces)
        for surface, vector in zip(surfaces, vectors, strict=True):
            if not vector:
                continue
            rows.append(
                {
                    "id": entry_id,
                    "surface": surface,
                    "vector": {
                        gram: round(weight, _WEIGHT_PRECISION) for gram, weight in vector.items()
                    },
                }
            )
    return rows


@dataclass(frozen=True)
class NeighbourMatch:
    """The nearest Knowledge Base entry to a query, with its similarity score."""

    entry_id: str
    surface: str
    score: float


class EmbeddingIndex:
    """An in-memory embedding index over Knowledge Base entry surfaces."""

    def __init__(self, rows: list[dict], backend: EmbeddingBackend | None = None) -> None:
        self._rows: list[tuple[str, str, SparseVector]] = [
            (row["id"], row["surface"], row["vector"]) for row in rows
        ]
        self._backend = backend or get_backend(DEFAULT_BACKEND)

    @property
    def backend(self) -> EmbeddingBackend:
        return self._backend

    def nearest(self, text: str) -> NeighbourMatch | None:
        """Return the nearest entry surface to ``text`` (highest cosine), or None."""
        (query,) = self._backend.embed([text])
        if not query:
            return None
        best: NeighbourMatch | None = None
        for entry_id, surface, vector in self._rows:
            score = cosine_similarity(query, vector)
            # Strict '>' keeps the first (sorted-id, listed-surface) winner on ties,
            # so results are deterministic regardless of scan order.
            if best is None or score > best.score:
                best = NeighbourMatch(entry_id=entry_id, surface=surface, score=score)
        return best

    def __len__(self) -> int:
        return len(self._rows)


def load_index(path: str | Path, backend: EmbeddingBackend | None = None) -> EmbeddingIndex:
    """Load a committed embedding-index artifact once into an :class:`EmbeddingIndex`."""
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return EmbeddingIndex(rows, backend)


# The shipped index lives next to the package data; resolved relative to the repo
# root so it works regardless of the process working directory.
DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "kb_embedding_index.json"
_default_index_cache: EmbeddingIndex | None = None


def load_default_index() -> EmbeddingIndex | None:
    """Load and cache the shipped embedding index once, or None when it is absent."""
    global _default_index_cache
    if _default_index_cache is None and DEFAULT_INDEX_PATH.is_file():
        _default_index_cache = load_index(DEFAULT_INDEX_PATH)
    return _default_index_cache
