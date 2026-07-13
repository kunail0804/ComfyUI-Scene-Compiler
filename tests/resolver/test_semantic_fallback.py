"""Tests for the semantic nearest-neighbour fallback (issue #116, epic #34)."""

from __future__ import annotations

from compiler.common.config import Config
from compiler.common.embedding_index import EmbeddingIndex, build_index_rows
from compiler.common.knowledge_base import KnowledgeBase, KnowledgeBaseEntry
from compiler.resolver.illustrious_resolver import resolve_scene
from schemas.models import Scene


def entry(id_, tags, category="clothing", aliases=(), rating="general"):
    return KnowledgeBaseEntry(
        id=id_, tags=tuple(tags), category=category, aliases=tuple(aliases), rating=rating
    )


def kb() -> KnowledgeBase:
    return KnowledgeBase(
        [
            entry("thighhighs", ["thighhighs"], aliases=["stockings"]),
            entry("dress", ["dress"]),
            entry("pussy", ["pussy"], category="body", rating="explicit"),
        ]
    )


def index(knowledge: KnowledgeBase) -> EmbeddingIndex:
    return EmbeddingIndex(build_index_rows(knowledge))


def scene_with(concept: str) -> Scene:
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": [concept],
                    "appearance": [],
                    "clothing": [],
                    "accessories": [],
                    "pose": [],
                    "expression": [],
                    "actions": [],
                }
            ],
            "interactions": [],
            "objects": [],
            "environment": [],
            "camera": [],
            "lighting": [],
            "metadata": {"schema_version": "1.0"},
        }
    )


def semantic_config(min_similarity: float = 0.5, include_nsfw: bool = False) -> Config:
    return Config.from_json(
        {
            "semantic": {"enabled": True, "min_similarity": min_similarity},
            "resolver": {"include_nsfw": include_nsfw},
        }
    )


def tags(result):
    return [t.tag for t in result.data]


def codes(messages):
    return [m.code for m in messages]


def test_near_concept_resolves_via_fallback_and_emits_sc0020() -> None:
    knowledge = kb()
    result = resolve_scene(
        scene_with("thighighs"), knowledge, semantic_config(), embedding_index=index(knowledge)
    )
    assert tags(result) == ["thighhighs"]
    assert "SC0020" in codes(result.warnings)


def test_far_concept_still_drops() -> None:
    knowledge = kb()
    result = resolve_scene(
        scene_with("quantum flux inverter"),
        knowledge,
        semantic_config(min_similarity=0.6),
        embedding_index=index(knowledge),
    )
    assert tags(result) == []
    assert "SC0001" in codes(result.warnings)
    assert "SC0020" not in codes(result.warnings)


def test_disabled_feature_is_byte_identical() -> None:
    knowledge = kb()
    disabled = resolve_scene(scene_with("thighighs"), knowledge, Config())
    with_index_but_disabled = resolve_scene(
        scene_with("thighighs"), knowledge, Config(), embedding_index=index(knowledge)
    )
    assert tags(disabled) == tags(with_index_but_disabled) == []
    assert "SC0020" not in codes(with_index_but_disabled.warnings)


def test_deterministic_lookup_always_wins() -> None:
    knowledge = kb()
    result = resolve_scene(
        scene_with("dress"), knowledge, semantic_config(), embedding_index=index(knowledge)
    )
    assert tags(result) == ["dress"]
    assert "SC0020" not in codes(result.warnings)  # exact hit, fallback not used


def test_gated_nsfw_neighbour_is_not_used() -> None:
    knowledge = kb()
    # "pusy" is closest to the explicit "pussy" entry, but NSFW is gated off.
    result = resolve_scene(
        scene_with("pusy"),
        knowledge,
        semantic_config(include_nsfw=False),
        embedding_index=index(knowledge),
    )
    assert "SC0020" not in codes(result.warnings)
    assert "SC0001" in codes(result.warnings)
