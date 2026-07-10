"""Tests for the Configuration ComfyUI node (issue #26)."""

from __future__ import annotations

import nodes
from compiler.common.config import Config
from nodes.configuration_node import ConfigurationNode


def default_inputs() -> dict:
    return {
        "analyzer_model": "llama3",
        "analyzer_temperature": 0.0,
        "analyzer_max_retries": 3,
        "analyzer_timeout": 60,
        "knowledge_base": "knowledge_base/",
        "resolver_strict_mode": True,
        "resolver_allow_aliases": True,
        "resolver_expansion_enabled": True,
        "resolver_max_expansion_depth": 8,
        "resolver_include_nsfw": False,
        "validator_allow_unknown_fields": False,
        "prompt_target": "easy_illustrious",
        "prompt_separator": ",",
        "prompt_trim_empty_outputs": True,
        "prompt_remove_duplicate_tags": True,
        "debug_enabled": False,
        "debug_level": "basic",
    }


def test_node_metadata() -> None:
    assert ConfigurationNode.RETURN_TYPES == ("COMPILER_CONFIG", "STRING")
    assert ConfigurationNode.RETURN_NAMES == ("config", "errors")
    required = ConfigurationNode.INPUT_TYPES()["required"]
    assert "analyzer_model" in required
    assert "debug_level" in required
    assert "analyzer_system_prompt" in ConfigurationNode.INPUT_TYPES()["optional"]


def test_default_inputs_produce_default_config() -> None:
    config, errors = ConfigurationNode().run(**default_inputs())
    assert isinstance(config, Config)
    assert config == Config()
    assert errors == ""


def test_inputs_flow_into_config() -> None:
    inputs = default_inputs()
    inputs["analyzer_model"] = "mistral"
    inputs["resolver_max_expansion_depth"] = 4
    inputs["resolver_include_nsfw"] = True
    inputs["validator_allow_unknown_fields"] = True
    inputs["prompt_separator"] = " | "
    inputs["debug_enabled"] = True
    inputs["debug_level"] = "verbose"
    config, _ = ConfigurationNode().run(**inputs)
    assert config.analyzer.model == "mistral"
    assert config.resolver.max_expansion_depth == 4
    assert config.resolver.include_nsfw is True
    assert config.validator.allow_unknown_fields is True
    assert config.prompt_builder.separator == " | "
    assert config.debug.enabled is True
    assert config.debug.level == "verbose"


def test_system_prompt_override_is_applied() -> None:
    config, _ = ConfigurationNode().run(**default_inputs(), analyzer_system_prompt="CUSTOM")
    assert config.analyzer.system_prompt == "CUSTOM"


def test_empty_system_prompt_is_omitted() -> None:
    config, _ = ConfigurationNode().run(**default_inputs(), analyzer_system_prompt="")
    assert config.analyzer.system_prompt is None


def test_debug_level_options_match_config_schema() -> None:
    options = ConfigurationNode.INPUT_TYPES()["required"]["debug_level"][0]
    for level in options:
        inputs = default_inputs()
        inputs["debug_level"] = level
        config, errors = ConfigurationNode().run(**inputs)
        assert isinstance(config, Config)
        assert errors == ""


def test_registered_for_comfyui() -> None:
    assert nodes.NODE_CLASS_MAPPINGS["SceneCompilerConfiguration"] is ConfigurationNode
    assert nodes.NODE_DISPLAY_NAME_MAPPINGS["SceneCompilerConfiguration"] == "Configuration"
