"""Regression: nodes must not crash when an upstream stage produced no output.

A failed upstream node passes ``None`` down its data output; downstream nodes must
surface an error instead of raising AttributeError (found in ComfyUI: a failed
Scene Analyzer crashed the Scene Validator on ``None.to_json()``).
"""

from __future__ import annotations

from nodes.resolver_node import ResolverNode
from nodes.scene_validator_node import SceneValidatorNode


def test_validator_handles_none_scene() -> None:
    scene, warnings, errors, *_ = SceneValidatorNode().run(None)
    assert scene is None
    assert "no output" in errors.lower()


def test_resolver_handles_none_scene() -> None:
    prompt, _, errors, *_ = ResolverNode().run(None, knowledge_base=object())
    assert prompt == ""
    assert errors


def test_resolver_handles_none_knowledge_base() -> None:
    prompt, _, errors, *_ = ResolverNode().run(scene=object(), knowledge_base=None)
    assert prompt == ""
    assert errors
