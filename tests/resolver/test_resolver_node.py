"""Tests for the Resolver ComfyUI node (issue #21). No Ollama."""

from __future__ import annotations

import nodes
import nodes.resolver_node as node_module
from compiler.common.config import Config
from compiler.common.knowledge_base import KnowledgeBase, KnowledgeBaseEntry
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult
from nodes.resolver_node import ResolverNode
from schemas.models import Scene


def kb() -> KnowledgeBase:
    return KnowledgeBase(
        [
            KnowledgeBaseEntry(
                id="female", tags=("1girl",), category="character", aliases=("girl",)
            ),
            KnowledgeBaseEntry(id="long_hair", tags=("long hair",), category="hair"),
        ]
    )


def scene() -> Scene:
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": ["girl"],
                    "appearance": ["long hair"],
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


def test_node_metadata() -> None:
    assert ResolverNode.RETURN_TYPES == ("RESOLVED_TAGS", "STRING", "STRING", "STRING")
    assert ResolverNode.RETURN_NAMES == ("resolved_tags", "warnings", "errors", "raw")
    inputs = ResolverNode.INPUT_TYPES()
    assert set(inputs["required"]) == {"scene", "knowledge_base"}
    assert "config" in inputs["optional"]


def test_resolves_tags_with_real_resolver() -> None:
    resolved, warnings, errors, *_ = ResolverNode().run(scene(), kb())
    assert [t.tag for t in resolved] == ["1girl", "long hair"]
    assert errors == ""


def test_delegates_and_surfaces_messages(monkeypatch) -> None:
    def fake_resolve(scene_arg, knowledge_base, config):
        return CompilerResult(data=()).add_warning(message("SC0001", "unknown 'x'"))

    monkeypatch.setattr(node_module, "resolve_scene", fake_resolve)
    resolved, warnings, errors, *_ = ResolverNode().run(scene(), kb())
    assert resolved == ()
    assert "SC0001: unknown 'x'" in warnings


def test_default_config_used_when_absent(monkeypatch) -> None:
    captured = {}

    def fake_resolve(scene_arg, knowledge_base, config):
        captured["config"] = config
        return CompilerResult(data=())

    monkeypatch.setattr(node_module, "resolve_scene", fake_resolve)
    ResolverNode().run(scene(), kb())
    assert isinstance(captured["config"], Config)


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerResolver"] is ResolverNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerResolver"] == "Resolver"
