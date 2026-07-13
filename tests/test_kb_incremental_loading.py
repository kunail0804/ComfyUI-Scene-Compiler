"""Tests for incremental (lazy) Knowledge Base loading (issue #132, epic #38)."""

from __future__ import annotations

import json
from pathlib import Path

from compiler.common.knowledge_base import KnowledgeBaseLoader

REPO_KB = Path(__file__).resolve().parent.parent / "knowledge_base"


def _make_kb(tmp_path):
    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]', encoding="utf-8"
    )
    (tmp_path / "clothing.json").write_text(
        '[{"id": "dress", "tags": ["dress"], "category": "clothing"}]', encoding="utf-8"
    )
    (tmp_path / "gen_clothing.json").write_text(
        '[{"id": "skirt", "tags": ["skirt"], "category": "clothing"}]', encoding="utf-8"
    )
    return tmp_path


def test_category_access_parses_only_that_categorys_files(tmp_path) -> None:
    loader = KnowledgeBaseLoader(_make_kb(tmp_path))
    hair = loader.category_entries("hair")
    assert [e["id"] for e in hair] == ["long_hair"]
    assert loader.files_read == {"hair.json"}  # clothing files not touched

    clothing = loader.category_entries("clothing")
    assert {e["id"] for e in clothing} == {"dress", "skirt"}  # curated + generated
    assert loader.files_read == {"hair.json", "clothing.json", "gen_clothing.json"}


def test_category_access_is_cached(tmp_path) -> None:
    loader = KnowledgeBaseLoader(_make_kb(tmp_path))
    loader.category_entries("hair")
    # Corrupt the file on disk; a cached second access must not re-read it.
    (tmp_path / "hair.json").write_text("BROKEN", encoding="utf-8")
    assert [e["id"] for e in loader.category_entries("hair")] == ["long_hair"]


def test_full_load_still_sees_complete_kb(tmp_path) -> None:
    loader = KnowledgeBaseLoader(_make_kb(tmp_path))
    loader.category_entries("hair")  # subset access first
    kb = loader.get()  # full resolution sees everything
    assert kb.get("long_hair") and kb.get("dress") and kb.get("skirt")


def test_reference_kb_category_access(tmp_path) -> None:
    loader = KnowledgeBaseLoader(REPO_KB)
    entries = loader.category_entries("clothing")
    assert any(e["id"] == "thighhighs" for e in entries)
    # Only clothing files were parsed, not the whole 16k-entry Knowledge Base.
    assert loader.files_read <= {"clothing.json", "gen_clothing.json"}
    assert len(json.dumps(entries)) > 0
