"""Tests for the Configuration ComfyUI node (issue #26)."""

from __future__ import annotations

import nodes
from compiler.common.config import Config
from compiler.common.knowledge_base import KnowledgeBase
from nodes.configuration_node import ConfigurationNode


def default_inputs() -> dict:
    return {
        "analyzer_model": "llama3",
        "analyzer_temperature": 0.0,
        "analyzer_max_retries": 3,
        "analyzer_timeout": 60,
        "resolver_strict_mode": True,
        "resolver_allow_aliases": True,
        "resolver_expansion_enabled": True,
        "resolver_max_expansion_depth": 8,
        "resolver_include_nsfw": False,
        "validator_allow_unknown_fields": False,
        "prompt_remove_duplicate_tags": True,
        "debug_enabled": False,
        "debug_level": "basic",
        "semantic_enabled": False,
        "semantic_min_similarity": 0.5,
        "semantic_backend": "char_ngram",
    }


def test_node_metadata() -> None:
    assert ConfigurationNode.RETURN_TYPES == (
        "COMPILER_CONFIG",
        "KNOWLEDGE_BASE",
        "STRING",
        "STRING",
    )
    assert ConfigurationNode.RETURN_NAMES == ("config", "knowledge_base", "warnings", "errors")
    required = ConfigurationNode.INPUT_TYPES()["required"]
    assert "analyzer_model" in required
    assert "debug_level" in required
    # Removed, leaner inputs: no user-facing KB path, prompt target/separator, or
    # analyzer system-prompt override.
    optional = ConfigurationNode.INPUT_TYPES()["optional"]
    assert "knowledge_base" not in required
    assert "prompt_target" not in required
    assert "prompt_separator" not in required
    assert "analyzer_system_prompt" not in optional
    assert "knowledge_base_reload" in optional


def test_default_inputs_produce_default_config_and_load_the_kb() -> None:
    config, kb, warnings, errors = ConfigurationNode().run(**default_inputs())
    assert isinstance(config, Config)
    assert config == Config()
    # The node loads the shipped reference Knowledge Base from its fixed path.
    assert isinstance(kb, KnowledgeBase)
    assert len(kb) > 100
    assert (warnings, errors) == ("", "")


def test_inputs_flow_into_config() -> None:
    inputs = default_inputs()
    inputs["analyzer_model"] = "mistral"
    inputs["resolver_max_expansion_depth"] = 4
    inputs["resolver_include_nsfw"] = True
    inputs["validator_allow_unknown_fields"] = True
    inputs["prompt_remove_duplicate_tags"] = False
    inputs["debug_enabled"] = True
    inputs["debug_level"] = "verbose"
    config, _kb, _warnings, _errors = ConfigurationNode().run(**inputs)
    assert config.analyzer.model == "mistral"
    assert config.resolver.max_expansion_depth == 4
    assert config.resolver.include_nsfw is True
    assert config.validator.allow_unknown_fields is True
    assert config.prompt_builder.remove_duplicate_tags is False
    assert config.debug.enabled is True
    assert config.debug.level == "verbose"


def test_prompt_target_and_separator_keep_their_defaults() -> None:
    # These are no longer user-facing; the compiler defaults still apply.
    config, *_ = ConfigurationNode().run(**default_inputs())
    assert config.prompt_builder.target == "easy_illustrious"
    assert config.prompt_builder.separator == ","


def test_debug_level_options_match_config_schema() -> None:
    options = ConfigurationNode.INPUT_TYPES()["required"]["debug_level"][0]
    for level in options:
        inputs = default_inputs()
        inputs["debug_level"] = level
        config, _kb, _warnings, errors = ConfigurationNode().run(**inputs)
        assert isinstance(config, Config)
        assert errors == ""


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerConfiguration"] is ConfigurationNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerConfiguration"] == "Configuration"
