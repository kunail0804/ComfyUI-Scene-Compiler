"""Tests for the Knowledge Base embedding index (issue #115, epic #34)."""

from __future__ import annotations

from pathlib import Path

from compiler.common.embedding_index import EmbeddingIndex, build_index_rows, load_index
from compiler.common.knowledge_base import KnowledgeBase, KnowledgeBaseEntry, load_knowledge_base

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "knowledge_base"
INDEX_FILE = REPO_ROOT / "data" / "kb_embedding_index.json"


def _entry(id_, tags, aliases=()):
    return KnowledgeBaseEntry(id=id_, tags=tuple(tags), category="clothing", aliases=tuple(aliases))


# --- committed reference index ---------------------------------------------


def test_committed_index_maps_known_concept_to_expected_entry() -> None:
    index = load_index(INDEX_FILE)
    match = index.nearest("stockings")
    assert match.entry_id == "thighhighs"  # via the ingested alias surface
    assert match.score > 0.99  # near-exact (weights are rounded in the snapshot)


def test_index_only_references_real_kb_entries() -> None:
    kb = load_knowledge_base(KB_DIR)
    index = load_index(INDEX_FILE)
    # Every row id is a real entry: a fallback can never invent a tag.
    match = index.nearest("blue eyes")
    assert kb.get(match.entry_id) is not None


# --- build determinism ------------------------------------------------------


def test_build_is_deterministic() -> None:
    kb = KnowledgeBase(
        [
            _entry("thighhighs", ["thighhighs"], aliases=["thigh highs", "stockings"]),
            _entry("pantyhose", ["pantyhose"], aliases=["tights"]),
        ]
    )
    assert build_index_rows(kb) == build_index_rows(kb)


def test_nearest_returns_expected_surface() -> None:
    kb = KnowledgeBase(
        [
            _entry("thighhighs", ["thighhighs"], aliases=["stockings"]),
            _entry("dress", ["dress"]),
        ]
    )
    index = EmbeddingIndex(build_index_rows(kb))
    match = index.nearest("stockings")
    assert match.entry_id == "thighhighs"
    assert match.surface == "stockings"


def test_empty_query_has_no_neighbour() -> None:
    index = EmbeddingIndex(build_index_rows(KnowledgeBase([_entry("dress", ["dress"])])))
    assert index.nearest("") is None
