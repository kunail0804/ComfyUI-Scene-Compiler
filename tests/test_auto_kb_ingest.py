"""Tests for Danbooru alias/implication ingestion (issue #118, epic #35)."""

from __future__ import annotations

from pathlib import Path

from compiler.common.knowledge_base import load_knowledge_base
from scripts import generate_kb_from_vocab as gen

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


# --- dataset level: the shipped, regenerated KB ----------------------------


def test_synonym_reaches_canonical_via_ingested_alias() -> None:
    kb = load_knowledge_base(KB_DIR)
    # The known V1 gap: "long black stockings" must reach "thighhighs".
    assert kb.lookup("stockings") is not None
    assert kb.lookup("stockings").id == "thighhighs"
    # An alias attached to a *generated* canonical (exercises ingestion on gen_*).
    assert kb.lookup("tights") is not None
    assert kb.lookup("tights").id == "pantyhose"


def test_implication_becomes_expand_relation() -> None:
    kb = load_knowledge_base(KB_DIR)
    assert "gloves" in kb.get("elbow_gloves").expand
    assert "weapon" in kb.get("katana").expand


# --- unit level: the ingestion function ------------------------------------


def test_ingestion_attaches_alias_and_skips_reserved(monkeypatch) -> None:
    monkeypatch.setattr(
        gen, "_load_aliases_by_canonical", lambda: {"pantyhose": ["tights", "curated_word"]}
    )
    monkeypatch.setattr(gen, "_load_implications", lambda: {})
    by_category = {"clothing": [{"id": "pantyhose", "tags": ["pantyhose"], "category": "clothing"}]}
    # "curated_word" is reserved by a curated entry, so curated wins → skipped.
    gen._ingest_aliases_and_implications(by_category, {"curated_word"}, curated_ids=set())
    assert by_category["clothing"][0]["aliases"] == ["tights"]


def test_ingestion_adds_expand_only_for_known_targets(monkeypatch) -> None:
    monkeypatch.setattr(gen, "_load_aliases_by_canonical", lambda: {})
    monkeypatch.setattr(
        gen, "_load_implications", lambda: {"elbow_gloves": ["gloves", "does_not_exist"]}
    )
    by_category = {
        "clothing": [{"id": "elbow_gloves", "tags": ["elbow gloves"], "category": "clothing"}]
    }
    gen._ingest_aliases_and_implications(by_category, set(), curated_ids={"gloves"})
    assert by_category["clothing"][0]["expand"] == ["gloves"]  # unknown target dropped
