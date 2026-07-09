"""Tests for the Scene Validator ComfyUI node (issue #20)."""

from __future__ import annotations

import nodes
import nodes.scene_validator_node as node_module
from compiler.common.config import Config
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult
from nodes.scene_validator_node import SceneValidatorNode
from schemas.models import Scene


def sample_scene() -> Scene:
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": ["female"],
                    "appearance": [],
                    "clothing": ["dress"],
                    "accessories": [],
                    "pose": [],
                    "expression": ["smile"],
                    "actions": [],
                }
            ],
            "interactions": [],
            "objects": [],
            "environment": ["classroom"],
            "camera": [],
            "lighting": [],
            "metadata": {"schema_version": "1.0"},
        }
    )


def test_node_metadata() -> None:
    assert SceneValidatorNode.RETURN_TYPES == ("SCENE", "STRING", "STRING", "STRING")
    assert SceneValidatorNode.RETURN_NAMES == ("scene", "warnings", "errors", "raw")
    assert SceneValidatorNode.CATEGORY == "Scene Compiler"
    inputs = SceneValidatorNode.INPUT_TYPES()
    assert "scene" in inputs["required"]
    assert "config" in inputs["optional"]


def test_valid_scene_passes_through() -> None:
    scene, warnings, errors, *_ = SceneValidatorNode().run(sample_scene())
    assert isinstance(scene, Scene)
    assert (warnings, errors) == ("", "")


def test_raw_output_contains_scene_json() -> None:
    _, _, _, raw = SceneValidatorNode().run(sample_scene())
    assert '"characters"' in raw  # the debug raw output is the scene as JSON
    assert "female" in raw


def test_delegates_and_surfaces_messages(monkeypatch) -> None:
    captured = {}

    def fake_validate(scene_json, config):
        captured["allow_unknown"] = config.validator.allow_unknown_fields
        return (
            CompilerResult(data="VALIDATED")
            .add_warning(message("SC0015", "unexpected field removed"))
            .add_error(message("SC0002", "bad"))
        )

    monkeypatch.setattr(node_module, "validate_scene", fake_validate)
    config = Config.from_json({"validator": {"allow_unknown_fields": True}})
    scene, warnings, errors, *_ = SceneValidatorNode().run(sample_scene(), config)
    assert scene == "VALIDATED"
    assert captured["allow_unknown"] is True
    assert "SC0015: unexpected field removed" in warnings
    assert "SC0002: bad" in errors


def test_default_config_used_when_absent(monkeypatch) -> None:
    captured = {}

    def fake_validate(scene_json, config):
        captured["config"] = config
        return CompilerResult(data="V")

    monkeypatch.setattr(node_module, "validate_scene", fake_validate)
    SceneValidatorNode().run(sample_scene())
    assert isinstance(captured["config"], Config)


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerValidator"] is SceneValidatorNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerValidator"] == "Scene Validator"
