"""Tests for the official Analyzer system prompt (issue #16, MASTER_SPEC §13)."""

from __future__ import annotations

import pytest

from compiler.analyzer.system_prompt import (
    DEFAULT_SYSTEM_PROMPT_PATH,
    load_default_system_prompt,
    resolve_system_prompt,
)
from compiler.common.config import Config


def test_default_prompt_file_exists_and_loads() -> None:
    assert DEFAULT_SYSTEM_PROMPT_PATH.is_file()
    assert load_default_system_prompt().strip()


# Drift guard: required normative directives from §13 must remain present.
REQUIRED_PHRASES = [
    "Scene Analyzer",  # §13.1 core identity
    "deterministic semantic parser",  # §13.1
    "Extract explicit concepts",  # §13.2 primary objective
    "Never generate Illustrious or Danbooru tags",  # §13.3 forbidden
    "Extract only explicitly described information",  # §13.4
    "implicit information MUST be ignored",  # §13.5
    "Ignore subjective adjectives",  # §13.6
    "masterpiece",  # §13.6 artistic language example
    "camera",  # §13.7
    "lighting",  # §13.7
    "environment",  # §13.8
    "independent Character object",  # §13.9
    "Interactions belong to the scene",  # §13.9
    "preserve the original wording",  # §13.10
    "no markdown",  # §13.11 JSON only
    "valid JSON",  # §13.11
]


@pytest.mark.parametrize("phrase", REQUIRED_PHRASES)
def test_prompt_contains_required_directive(phrase: str) -> None:
    assert phrase in load_default_system_prompt(), f"missing directive: {phrase!r}"


def test_prompt_includes_output_shape_keys() -> None:
    prompt = load_default_system_prompt()
    for key in ("characters", "interactions", "objects", "environment", "camera", "lighting"):
        assert key in prompt


def test_resolve_uses_default_when_unset() -> None:
    assert resolve_system_prompt(Config()) == load_default_system_prompt()


def test_resolve_uses_config_override() -> None:
    config = Config.from_json({"analyzer": {"system_prompt": "CUSTOM PROMPT"}})
    assert resolve_system_prompt(config) == "CUSTOM PROMPT"


def test_config_roundtrips_system_prompt() -> None:
    config = Config.from_json({"analyzer": {"system_prompt": "X"}})
    assert config.to_json()["analyzer"]["system_prompt"] == "X"
