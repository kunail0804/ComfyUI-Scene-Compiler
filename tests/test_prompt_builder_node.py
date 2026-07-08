"""Tests for the Prompt Builder ComfyUI node (issue #23)."""

from __future__ import annotations

from types import MappingProxyType

import nodes
from compiler.common.categories import CANONICAL_CATEGORIES
from compiler.common.config import Config
from nodes.prompt_builder_node import PromptBuilderNode
from schemas.models import CategoryMap, ResolvedTag


def rtag(name: str, category: str) -> ResolvedTag:
    return ResolvedTag(tag=name, category=category, source_concept=name, knowledge_base_entry=name)


def category_map(**by_category: list[ResolvedTag]) -> CategoryMap:
    return CategoryMap(categories=MappingProxyType({k: tuple(v) for k, v in by_category.items()}))


def outputs(result: tuple[str, ...]) -> dict[str, str]:
    return dict(zip(PromptBuilderNode.RETURN_NAMES, result, strict=True))


def test_emits_one_output_per_category_plus_reserved() -> None:
    assert PromptBuilderNode.RETURN_NAMES == (*CANONICAL_CATEGORIES, "negative", "scene")
    assert PromptBuilderNode.RETURN_TYPES == ("STRING",) * 21


def test_formats_and_orders_category_strings() -> None:
    cm = category_map(hair=[rtag("blonde hair", "hair"), rtag("long hair", "hair")])
    result = PromptBuilderNode().run(cm)
    by_name = outputs(result)
    assert by_name["hair"] == "blonde hair,long hair"
    assert by_name["character"] == ""  # empty category -> empty string


def test_reserved_outputs_are_empty() -> None:
    cm = category_map(character=[rtag("1girl", "character")])
    by_name = outputs(PromptBuilderNode().run(cm))
    assert by_name["negative"] == ""
    assert by_name["scene"] == ""


def test_custom_separator_from_config() -> None:
    cm = category_map(hair=[rtag("a", "hair"), rtag("b", "hair")])
    config = Config.from_json({"prompt_builder": {"separator": " | "}})
    by_name = outputs(PromptBuilderNode().run(cm, config))
    assert by_name["hair"] == "a | b"


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerPromptBuilder"] is PromptBuilderNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerPromptBuilder"] == "Prompt Builder"
