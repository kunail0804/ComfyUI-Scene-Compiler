"""Tests for the Scene Analyzer ComfyUI node (issue #19). No live Ollama."""

from __future__ import annotations

import nodes
import nodes.scene_analyzer_node as node_module
from compiler.common.config import Config
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult
from nodes.scene_analyzer_node import SceneAnalyzerNode


def test_input_types_structure() -> None:
    inputs = SceneAnalyzerNode.INPUT_TYPES()
    # Analyzer settings live on the Configuration node; only the per-run text and
    # the optional config connection remain.
    assert set(inputs["required"]) == {"natural_language"}
    assert set(inputs["optional"]) == {"config"}


def test_node_metadata() -> None:
    assert SceneAnalyzerNode.RETURN_TYPES == ("SCENE", "STRING", "STRING", "STRING")
    assert SceneAnalyzerNode.RETURN_NAMES == ("scene", "warnings", "errors", "raw")
    assert SceneAnalyzerNode.FUNCTION == "run"
    assert SceneAnalyzerNode.CATEGORY == "Scene Compiler"


def test_run_uses_model_from_config(monkeypatch) -> None:
    captured = {}

    def fake_analyze(description, backend, config):
        captured["description"] = description
        captured["model"] = config.analyzer.model
        return (
            CompilerResult(data="SCENE_MODEL")
            .add_warning(message("SC0001", "unknown concept 'x'"))
            .add_error(message("SC0011", "bad response"))
        )

    monkeypatch.setattr(node_module, "analyze", fake_analyze)

    config = Config.from_json({"analyzer": {"model": "mistral"}})
    scene, warnings, errors, *_ = SceneAnalyzerNode().run(
        natural_language="A girl.",
        config=config,
    )
    assert scene == "SCENE_MODEL"
    assert captured["description"] == "A girl."
    assert captured["model"] == "mistral"
    assert "SC0001: unknown concept 'x'" in warnings
    assert "SC0011: bad response" in errors


def test_defaults_apply_without_a_configuration_node(monkeypatch) -> None:
    captured = {}

    def fake_analyze(description, backend, config):
        captured["model"] = config.analyzer.model
        captured["timeout"] = config.analyzer.timeout
        return CompilerResult(data="S")

    monkeypatch.setattr(node_module, "analyze", fake_analyze)
    SceneAnalyzerNode().run("A girl.")
    # Falls back to the built-in model with a cold-load-friendly timeout.
    assert captured["model"] == "llama3"
    assert captured["timeout"] == 300


def test_no_messages_yield_empty_strings(monkeypatch) -> None:
    monkeypatch.setattr(node_module, "analyze", lambda d, b, c: CompilerResult(data="S"))
    scene, warnings, errors, *_ = SceneAnalyzerNode().run("x")
    assert (warnings, errors) == ("", "")


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerAnalyzer"] is SceneAnalyzerNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerAnalyzer"] == "Scene Analyzer"
