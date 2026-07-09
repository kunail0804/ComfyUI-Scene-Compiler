"""Tests for the Knowledge Base Loader ComfyUI node (issue #25)."""

from __future__ import annotations

import json

import nodes
from compiler.common.knowledge_base import KnowledgeBase
from nodes.knowledge_base_loader_node import KnowledgeBaseLoaderNode


def write_kb(directory, entries: list[dict]) -> str:
    (directory / "hair.json").write_text(json.dumps(entries), encoding="utf-8")
    return str(directory)


def test_node_metadata() -> None:
    assert KnowledgeBaseLoaderNode.RETURN_TYPES == ("KNOWLEDGE_BASE", "STRING", "STRING")
    assert KnowledgeBaseLoaderNode.RETURN_NAMES == ("knowledge_base", "warnings", "errors")
    inputs = KnowledgeBaseLoaderNode.INPUT_TYPES()
    assert "path" in inputs["required"]
    assert "reload" in inputs["optional"]


def test_loads_knowledge_base(tmp_path) -> None:
    path = write_kb(tmp_path, [{"id": "long_hair", "tags": ["long hair"], "category": "hair"}])
    kb, warnings, errors = KnowledgeBaseLoaderNode().run(path)
    assert isinstance(kb, KnowledgeBase)
    assert kb.get("long_hair") is not None
    assert (warnings, errors) == ("", "")


def test_invalid_knowledge_base_surfaces_sc0004(tmp_path) -> None:
    path = write_kb(tmp_path, [{"id": "x", "tags": ["x"], "category": "nope"}])
    kb, warnings, errors = KnowledgeBaseLoaderNode().run(path)
    assert kb is None
    assert "SC0004" in errors


def test_reload_input_is_accepted(tmp_path) -> None:
    path = write_kb(tmp_path, [{"id": "long_hair", "tags": ["long hair"], "category": "hair"}])
    kb, _, _ = KnowledgeBaseLoaderNode().run(path, reload=5)
    assert isinstance(kb, KnowledgeBase)


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerKnowledgeBaseLoader"] is KnowledgeBaseLoaderNode
    assert (
        nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerKnowledgeBaseLoader"]
        == "Knowledge Base Loader"
    )
