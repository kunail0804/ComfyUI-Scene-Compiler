"""Determinism & no-invention guarantees for the semantic fallback (issue #117)."""

from __future__ import annotations

from compiler.common.config import Config
from compiler.common.embedding_index import EmbeddingIndex, build_index_rows
from compiler.common.knowledge_base import KnowledgeBase, KnowledgeBaseEntry
from compiler.common.message_codes import CODES
from compiler.common.result import Severity
from compiler.resolver.illustrious_resolver import resolve_scene
from schemas.models import Scene


def entry(id_, tags, aliases=()):
    return KnowledgeBaseEntry(id=id_, tags=tuple(tags), category="clothing", aliases=tuple(aliases))


def kb() -> KnowledgeBase:
    return KnowledgeBase(
        [
            entry("thighhighs", ["thighhighs"], aliases=["stockings"]),
            entry("dress", ["dress"]),
            entry("jacket", ["jacket"]),
        ]
    )


def scene_with(*concepts: str) -> Scene:
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": list(concepts),
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


def enabled_config() -> Config:
    return Config.from_json({"semantic": {"enabled": True, "min_similarity": 0.3}})


class _ExplodingIndex(EmbeddingIndex):
    """An index that fails if queried — proves the fallback was never reached."""

    def nearest(self, text: str):  # type: ignore[override]
        raise AssertionError(f"embedding fallback must not run for '{text}'")


def test_sc0020_is_registered() -> None:
    assert "SC0020" in CODES
    assert CODES["SC0020"].severity is Severity.WARNING


def test_exact_hit_never_routes_through_fallback() -> None:
    knowledge = kb()
    # Every concept is an exact id/alias hit, so nearest() must never be called
    # even with the feature enabled — deterministic resolution always wins.
    result = resolve_scene(
        scene_with("dress", "jacket", "stockings"),
        knowledge,
        enabled_config(),
        embedding_index=_ExplodingIndex(build_index_rows(knowledge)),
    )
    assert [t.tag for t in result.data] == ["dress", "jacket", "thighhighs"]


def test_fallback_only_emits_existing_kb_tags() -> None:
    knowledge = kb()
    index = EmbeddingIndex(build_index_rows(knowledge))
    kb_tags = {tag for e in knowledge.by_id.values() for tag in e.tags}
    # A spread of misspellings/near-misses; whatever resolves must be a real tag.
    for query in ["thighighs", "jackt", "dres", "stockngs", "zzzz"]:
        result = resolve_scene(
            scene_with(query), knowledge, enabled_config(), embedding_index=index
        )
        for resolved in result.data:
            assert resolved.tag in kb_tags  # no invention


def test_same_scene_twice_is_identical() -> None:
    knowledge = kb()
    index = EmbeddingIndex(build_index_rows(knowledge))
    scene = scene_with("thighighs", "dres", "jacket")
    first = resolve_scene(scene, knowledge, enabled_config(), embedding_index=index)
    second = resolve_scene(scene, knowledge, enabled_config(), embedding_index=index)
    assert [t.tag for t in first.data] == [t.tag for t in second.data]
    assert [m.code for m in first.warnings] == [m.code for m in second.warnings]
