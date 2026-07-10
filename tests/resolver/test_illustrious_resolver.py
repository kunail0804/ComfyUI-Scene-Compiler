"""Tests for the Illustrious Resolver (issue #12, MASTER_SPEC §17). No Ollama."""

from __future__ import annotations

from compiler.common.config import Config
from compiler.common.knowledge_base import KnowledgeBase, KnowledgeBaseEntry
from compiler.resolver.illustrious_resolver import resolve_scene
from schemas.models import Scene


def kb(*entries: KnowledgeBaseEntry) -> KnowledgeBase:
    return KnowledgeBase(list(entries))


def entry(id_, tags, category="hair", aliases=(), expand=(), deprecated=False, rating="general"):
    return KnowledgeBaseEntry(
        id=id_,
        tags=tuple(tags),
        category=category,
        aliases=tuple(aliases),
        expand=tuple(expand),
        deprecated=deprecated,
        rating=rating,
    )


def scene_with(identity=(), **fields) -> Scene:
    character = {
        "id": 0,
        "identity": list(identity),
        "appearance": list(fields.get("appearance", [])),
        "clothing": list(fields.get("clothing", [])),
        "accessories": [],
        "pose": [],
        "expression": [],
        "actions": [],
    }
    return Scene.from_json(
        {
            "characters": [character],
            "interactions": [],
            "objects": list(fields.get("objects", [])),
            "environment": list(fields.get("environment", [])),
            "camera": [],
            "lighting": [],
            "metadata": {"schema_version": "1.0"},
        }
    )


def default_config() -> Config:
    return Config()


def tags(result) -> list[str]:
    return [t.tag for t in result.data]


def codes(messages) -> list[str]:
    return [m.code for m in messages]


# --- normalization ---------------------------------------------------------


def test_normalization_matches_snake_case_id() -> None:
    knowledge = kb(entry("long_hair", ["long hair"]))
    for written in ["long hair", "Long   Hair", "  LONG_HAIR ", "long_hair"]:
        result = resolve_scene(scene_with(identity=[written]), knowledge, default_config())
        assert tags(result) == ["long hair"], written


# --- alias resolution ------------------------------------------------------


def test_alias_resolves_directly() -> None:
    knowledge = kb(entry("female", ["1girl"], category="character", aliases=["girl", "woman"]))
    result = resolve_scene(scene_with(identity=["girl"]), knowledge, default_config())
    assert tags(result) == ["1girl"]
    assert result.data[0].knowledge_base_entry == "female"
    assert result.data[0].source_concept == "girl"


def test_alias_ignored_when_disabled() -> None:
    knowledge = kb(entry("female", ["1girl"], category="character", aliases=["girl"]))
    config = Config.from_json({"resolver": {"allow_aliases": False}})
    result = resolve_scene(scene_with(identity=["girl"]), knowledge, config)
    assert tags(result) == []
    assert "SC0001" in codes(result.warnings)


# --- expansion order -------------------------------------------------------


def test_expansion_order_is_normative() -> None:
    knowledge = kb(
        entry(
            "school_uniform", ["school uniform"], category="clothing", expand=["blazer", "skirt"]
        ),
        entry("blazer", ["blazer"], category="clothing"),
        entry("skirt", ["pleated skirt"], category="clothing"),
    )
    result = resolve_scene(scene_with(clothing=["school uniform"]), knowledge, default_config())
    assert tags(result) == ["school uniform", "blazer", "pleated skirt"]


def test_nested_expansion_is_depth_first() -> None:
    knowledge = kb(
        entry("a", ["ta"], expand=["b"]),
        entry("b", ["tb"], expand=["c"]),
        entry("c", ["tc"]),
    )
    result = resolve_scene(scene_with(identity=["a"]), knowledge, default_config())
    assert tags(result) == ["ta", "tb", "tc"]


def test_expansion_disabled_emits_only_own_tags() -> None:
    knowledge = kb(
        entry("a", ["ta"], expand=["b"]),
        entry("b", ["tb"]),
    )
    config = Config.from_json({"resolver": {"expansion_enabled": False}})
    result = resolve_scene(scene_with(identity=["a"]), knowledge, config)
    assert tags(result) == ["ta"]


def test_max_expansion_depth_caps_recursion() -> None:
    # depth 1 allows one expansion level (a -> b) but not the next (b -> c).
    knowledge = kb(
        entry("a", ["ta"], expand=["b"]),
        entry("b", ["tb"], expand=["c"]),
        entry("c", ["tc"]),
    )
    config = Config.from_json({"resolver": {"max_expansion_depth": 1}})
    result = resolve_scene(scene_with(identity=["a"]), knowledge, config)
    assert tags(result) == ["ta", "tb"]


def test_expanded_tag_traceability() -> None:
    knowledge = kb(
        entry("school_uniform", ["school uniform"], category="clothing", expand=["blazer"]),
        entry("blazer", ["blazer"], category="clothing"),
    )
    result = resolve_scene(scene_with(clothing=["school uniform"]), knowledge, default_config())
    blazer_tag = result.data[1]
    assert blazer_tag.tag == "blazer"
    assert blazer_tag.knowledge_base_entry == "blazer"
    assert blazer_tag.source_concept == "school uniform"  # originating scene concept


# --- deduplication ---------------------------------------------------------


def test_duplicate_tags_removed_keeping_first() -> None:
    knowledge = kb(
        entry("a", ["shared"]),
        entry("b", ["shared"]),
    )
    result = resolve_scene(scene_with(identity=["a", "b"]), knowledge, default_config())
    assert tags(result) == ["shared"]
    assert "SC0007" in codes(result.warnings)


# --- compound concept reduction (head-noun fallback) -----------------------


def test_compound_concept_reduces_to_head_noun() -> None:
    # "white summer dress" is not a KB key, but its head noun "dress" is; the
    # resolver recovers it instead of dropping the concept entirely.
    knowledge = kb(entry("dress", ["dress"], category="clothing"))
    result = resolve_scene(scene_with(clothing=["white summer dress"]), knowledge, default_config())
    assert tags(result) == ["dress"]
    assert "SC0019" in codes(result.warnings)
    assert result.data[0].source_concept == "white summer dress"  # traceability kept


def test_reduction_prefers_longest_matching_suffix() -> None:
    knowledge = kb(
        entry("pleated_skirt", ["pleated skirt"], category="clothing"),
        entry("skirt", ["skirt"], category="clothing"),
    )
    result = resolve_scene(
        scene_with(clothing=["black pleated skirt"]), knowledge, default_config()
    )
    assert tags(result) == ["pleated skirt"]  # longest suffix wins over bare "skirt"


def test_reduction_resolves_through_aliases() -> None:
    knowledge = kb(entry("suit", ["business suit"], category="clothing", aliases=["business suit"]))
    result = resolve_scene(
        scene_with(clothing=["black business suit"]), knowledge, default_config()
    )
    assert tags(result) == ["business suit"]


def test_reduction_disabled_when_aliases_only_match_and_aliases_off() -> None:
    # An exact-id concept is unaffected; reduction never invents an alias hit.
    knowledge = kb(entry("dress", ["dress"], category="clothing"))
    result = resolve_scene(scene_with(clothing=["dress"]), knowledge, default_config())
    assert tags(result) == ["dress"]
    assert "SC0019" not in codes(result.warnings)  # exact match, no reduction


def test_truly_unknown_compound_still_warns_sc0001() -> None:
    knowledge = kb(entry("female", ["1girl"], category="character"))
    result = resolve_scene(
        scene_with(clothing=["hologram flux capacitor"]), knowledge, default_config()
    )
    assert tags(result) == []
    assert "SC0001" in codes(result.warnings)


# --- NSFW rating gating ----------------------------------------------------


def test_explicit_entry_hidden_by_default() -> None:
    knowledge = kb(entry("bar", ["bar tag"], category="body", rating="explicit"))
    result = resolve_scene(scene_with(clothing=["bar"]), knowledge, default_config())
    assert tags(result) == []
    assert "SC0001" in codes(result.warnings)  # gated out -> treated as unknown


def test_explicit_entry_included_when_enabled() -> None:
    knowledge = kb(entry("bar", ["bar tag"], category="body", rating="explicit"))
    config = Config.from_json({"resolver": {"include_nsfw": True}})
    result = resolve_scene(scene_with(clothing=["bar"]), knowledge, config)
    assert tags(result) == ["bar tag"]


def test_explicit_expansion_target_gated_out_by_default() -> None:
    knowledge = kb(
        entry("coat", ["coat"], category="clothing", expand=["nude"]),
        entry("nude", ["nude"], category="body", rating="explicit"),
    )
    result = resolve_scene(scene_with(clothing=["coat"]), knowledge, default_config())
    assert tags(result) == ["coat"]  # explicit expansion target dropped


# --- unknown / deprecated --------------------------------------------------


def test_unknown_concept_warns_and_continues() -> None:
    knowledge = kb(entry("female", ["1girl"], category="character"))
    result = resolve_scene(scene_with(identity=["dragon", "female"]), knowledge, default_config())
    assert tags(result) == ["1girl"]
    assert "SC0001" in codes(result.warnings)


def test_deprecated_concept_warns_but_emits_tags() -> None:
    knowledge = kb(entry("old_style", ["old style"], deprecated=True))
    result = resolve_scene(scene_with(identity=["old_style"]), knowledge, default_config())
    assert tags(result) == ["old style"]
    assert "SC0006" in codes(result.warnings)


# --- error conditions stop -------------------------------------------------


def test_circular_expansion_stops_with_sc0003() -> None:
    knowledge = kb(
        entry("a", ["ta"], expand=["b"]),
        entry("b", ["tb"], expand=["a"]),
    )
    result = resolve_scene(scene_with(identity=["a"]), knowledge, default_config())
    assert not result.success
    assert result.data is None
    assert "SC0003" in codes(result.errors)


def test_invalid_category_stops_with_sc0008() -> None:
    knowledge = kb(entry("a", ["ta"], category="not_a_category"))
    result = resolve_scene(scene_with(identity=["a"]), knowledge, default_config())
    assert not result.success
    assert "SC0008" in codes(result.errors)


# --- category preservation & determinism -----------------------------------


def test_tag_keeps_entry_category() -> None:
    knowledge = kb(entry("blue_eyes", ["blue eyes"], category="eyes"))
    result = resolve_scene(scene_with(appearance=["blue_eyes"]), knowledge, default_config())
    assert result.data[0].category == "eyes"


def test_discovery_order_preserved_across_scene() -> None:
    knowledge = kb(
        entry("female", ["1girl"], category="character"),
        entry("forest", ["forest"], category="environment"),
    )
    scene = scene_with(identity=["female"], environment=["forest"])
    result = resolve_scene(scene, knowledge, default_config())
    assert tags(result) == ["1girl", "forest"]


def test_output_is_deterministic() -> None:
    knowledge = kb(
        entry("school_uniform", ["school uniform"], category="clothing", expand=["blazer"]),
        entry("blazer", ["blazer"], category="clothing"),
    )
    scene = scene_with(clothing=["school uniform", "school uniform"])
    a = resolve_scene(scene, knowledge, default_config())
    b = resolve_scene(scene, knowledge, default_config())
    assert tags(a) == tags(b)
    assert codes(a.warnings) == codes(b.warnings)
