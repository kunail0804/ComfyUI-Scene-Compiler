"""Tests for the configuration system (issue #5, MASTER_SPEC §23)."""

from __future__ import annotations

import dataclasses
import json

import pytest

from compiler.common.config import Config, ConfigError, load_config
from compiler.common.result import Severity

# The canonical example from MASTER_SPEC §23.2.
EXAMPLE_CONFIG = {
    "schema": "1.0",
    "analyzer": {
        "backend": "ollama",
        "model": "llama3",
        "temperature": 0.0,
        "max_retries": 3,
        "timeout": 60,
    },
    "resolver": {
        "knowledge_base": "knowledge_base/",
        "strict_mode": True,
        "allow_aliases": True,
        "expansion_enabled": True,
        "max_expansion_depth": 8,
        "include_nsfw": False,
    },
    "validator": {"allow_unknown_fields": False},
    "prompt_builder": {
        "target": "easy_illustrious",
        "separator": ",",
        "trim_empty_outputs": True,
        "remove_duplicate_tags": True,
    },
    "debug": {"enabled": False, "level": "basic"},
}


# --- defaults --------------------------------------------------------------


def test_defaults_match_section_23_2() -> None:
    c = Config()
    assert c.schema == "1.0"
    assert c.analyzer.backend == "ollama"
    assert c.analyzer.temperature == pytest.approx(0.0)
    assert c.analyzer.max_retries == 3
    assert c.analyzer.timeout == 60
    assert c.resolver.knowledge_base == "knowledge_base/"
    assert c.resolver.max_expansion_depth == 8
    assert c.resolver.strict_mode is True
    assert c.validator.allow_unknown_fields is False
    assert c.prompt_builder.separator == ","
    assert c.prompt_builder.target == "easy_illustrious"
    assert c.debug.enabled is False
    assert c.debug.level == "basic"


def test_defaults_equal_full_example() -> None:
    assert Config() == Config.from_json(EXAMPLE_CONFIG)


# --- load ------------------------------------------------------------------


def test_full_example_loads_and_roundtrips() -> None:
    c = Config.from_json(EXAMPLE_CONFIG)
    assert c.to_json() == EXAMPLE_CONFIG


def test_empty_config_uses_all_defaults() -> None:
    assert Config.from_json({}) == Config()


def test_partial_config_fills_defaults() -> None:
    c = Config.from_json({"analyzer": {"model": "mistral"}})
    assert c.analyzer.model == "mistral"
    assert c.analyzer.temperature == pytest.approx(0.0)  # default preserved
    assert c.resolver.max_expansion_depth == 8


def test_load_config_reads_file(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(EXAMPLE_CONFIG), encoding="utf-8")
    assert load_config(path) == Config.from_json(EXAMPLE_CONFIG)


# --- invalid config -> SC0014 ----------------------------------------------


def test_wrong_type_rejected_with_sc0014() -> None:
    with pytest.raises(ConfigError) as exc:
        Config.from_json({"analyzer": {"temperature": "hot"}})
    assert exc.value.message.code == "SC0014"
    assert exc.value.message.severity is Severity.FATAL


def test_unknown_field_rejected() -> None:
    with pytest.raises(ConfigError):
        Config.from_json({"analyzer": {"unknown_option": 1}})


def test_random_seed_option_is_forbidden() -> None:
    with pytest.raises(ConfigError) as exc:
        Config.from_json({"analyzer": {"seed": 42}})
    assert exc.value.message.code == "SC0014"


def test_negative_temperature_rejected() -> None:
    with pytest.raises(ConfigError):
        Config.from_json({"analyzer": {"temperature": -1.0}})


# --- immutability ----------------------------------------------------------


def test_config_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        Config().analyzer.temperature = 1.0  # type: ignore[misc]


# --- shipped default file --------------------------------------------------


def test_shipped_default_config_file_matches_defaults() -> None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    default_file = repo_root / "config" / "default_config.json"
    data = json.loads(default_file.read_text(encoding="utf-8"))
    assert Config.from_json(data) == Config()
