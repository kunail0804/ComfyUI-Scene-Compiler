"""Regression: nodes must not crash when an upstream stage produced no output.

A failed upstream node passes ``None`` down its data output; downstream nodes must
surface an error instead of raising AttributeError (found in ComfyUI: a failed
Scene Analyzer crashed the Scene Validator on ``None.to_json()``).
"""

from __future__ import annotations

from nodes.category_splitter_node import CategorySplitterNode
from nodes.prompt_builder_node import PromptBuilderNode
from nodes.resolver_node import ResolverNode
from nodes.scene_validator_node import SceneValidatorNode


def test_validator_handles_none_scene() -> None:
    scene, warnings, errors = SceneValidatorNode().run(None)
    assert scene is None
    assert "no output" in errors.lower()


def test_resolver_handles_none_scene() -> None:
    resolved, _, errors = ResolverNode().run(None, knowledge_base=object())
    assert resolved is None
    assert errors


def test_resolver_handles_none_knowledge_base() -> None:
    resolved, _, errors = ResolverNode().run(scene=object(), knowledge_base=None)
    assert resolved is None
    assert errors


def test_category_splitter_handles_none_tags() -> None:
    category_map, _, errors = CategorySplitterNode().run(None)
    assert category_map is None
    assert errors


def test_prompt_builder_handles_none_category_map() -> None:
    outputs = PromptBuilderNode().run(None)
    assert len(outputs) == len(PromptBuilderNode.RETURN_NAMES)
    assert all(value == "" for value in outputs)
