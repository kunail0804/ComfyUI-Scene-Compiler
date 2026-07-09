"""Tests for the Debug Viewer ComfyUI node (issue #24)."""

from __future__ import annotations

import json
from types import MappingProxyType

import nodes
from nodes.debug_viewer_node import DebugViewerNode
from schemas.models import CategoryMap, ResolvedTag, Scene


def sample_scene() -> Scene:
    return Scene.from_json(
        {
            "characters": [],
            "interactions": [],
            "objects": ["chair"],
            "environment": [],
            "camera": [],
            "lighting": [],
            "metadata": {"schema_version": "1.0"},
        }
    )


def rtag(name: str, category: str) -> ResolvedTag:
    return ResolvedTag(tag=name, category=category, source_concept=name, knowledge_base_entry=name)


def test_node_metadata() -> None:
    assert DebugViewerNode.RETURN_NAMES == ("report",)
    assert DebugViewerNode.OUTPUT_NODE is True
    optional = DebugViewerNode.INPUT_TYPES()["optional"]
    assert set(optional) == {"scene", "resolved_tags", "category_map", "warnings", "errors"}


def test_empty_report_when_nothing_connected() -> None:
    (report,) = DebugViewerNode().run()
    assert report == ""


def test_renders_each_state() -> None:
    scene = sample_scene()
    tags = (rtag("chair", "objects"),)
    category_map = CategoryMap(categories=MappingProxyType({"objects": tags}))
    (report,) = DebugViewerNode().run(
        scene=scene,
        resolved_tags=tags,
        category_map=category_map,
        warnings="SC0001: unknown",
        errors="",
    )
    assert "== Scene JSON ==" in report
    assert "== Resolved Tags ==" in report
    assert "== Categories ==" in report
    assert "== Warnings ==" in report
    assert "== Errors ==" not in report  # empty errors omitted
    assert "chair" in report


def test_report_is_valid_serialization() -> None:
    scene = sample_scene()
    (report,) = DebugViewerNode().run(scene=scene)
    payload = report.split("== Scene JSON ==\n", 1)[1]
    assert json.loads(payload)["objects"] == ["chair"]


def test_is_read_only() -> None:
    scene = sample_scene()
    before = scene.to_json()
    DebugViewerNode().run(scene=scene)
    assert scene.to_json() == before  # unchanged


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerDebugViewer"] is DebugViewerNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerDebugViewer"] == "Debug Viewer"
