"""Tests for the Category Splitter ComfyUI node (issue #22)."""

from __future__ import annotations

import nodes
import nodes.category_splitter_node as node_module
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult
from nodes.category_splitter_node import CategorySplitterNode
from schemas.models import CategoryMap, ResolvedTag


def rtag(name: str, category: str) -> ResolvedTag:
    return ResolvedTag(tag=name, category=category, source_concept=name, knowledge_base_entry=name)


def test_node_metadata() -> None:
    assert CategorySplitterNode.RETURN_TYPES == ("CATEGORY_MAP", "STRING", "STRING", "STRING")
    assert CategorySplitterNode.RETURN_NAMES == ("category_map", "warnings", "errors", "raw")
    assert "resolved_tags" in CategorySplitterNode.INPUT_TYPES()["required"]


def test_splits_with_real_module() -> None:
    tags = (rtag("1girl", "character"), rtag("long hair", "hair"))
    category_map, warnings, errors, *_ = CategorySplitterNode().run(tags)
    assert isinstance(category_map, CategoryMap)
    assert [t.tag for t in category_map.tags_for("character")] == ["1girl"]
    assert [t.tag for t in category_map.tags_for("hair")] == ["long hair"]
    assert (warnings, errors) == ("", "")


def test_delegates_and_surfaces_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        node_module,
        "split_into_categories",
        lambda tags: CompilerResult().add_error(message("SC0008", "bad category")),
    )
    category_map, warnings, errors, *_ = CategorySplitterNode().run(())
    assert category_map is None
    assert "SC0008: bad category" in errors


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerCategorySplitter"] is CategorySplitterNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerCategorySplitter"] == "Category Splitter"
