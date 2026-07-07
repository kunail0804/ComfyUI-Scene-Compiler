"""Tests for the Scene Validator (issue #11, MASTER_SPEC §14)."""

from __future__ import annotations

from compiler.common.config import Config
from compiler.common.result import Severity
from compiler.validator.scene_validator import validate_scene
from schemas.models import Scene


def valid_scene() -> dict:
    return {
        "characters": [
            {
                "id": 0,
                "identity": ["female"],
                "appearance": [],
                "clothing": ["dress"],
                "accessories": [],
                "pose": ["standing"],
                "expression": ["smile"],
                "actions": [],
            }
        ],
        "interactions": [],
        "objects": [],
        "environment": ["classroom"],
        "camera": [],
        "lighting": ["sunset"],
        "metadata": {"schema_version": "1.0"},
    }


def default_config() -> Config:
    return Config()


def codes(messages) -> list[str]:
    return [m.code for m in messages]


# --- valid input -----------------------------------------------------------


def test_valid_scene_succeeds() -> None:
    result = validate_scene(valid_scene(), default_config())
    assert result.success
    assert isinstance(result.data, Scene)
    assert result.warnings == ()
    assert result.data.characters[0].identity[0].name == "female"


# --- hard errors stop compilation ------------------------------------------


def test_missing_required_field_is_sc0009_and_stops() -> None:
    scene = valid_scene()
    del scene["metadata"]
    result = validate_scene(scene, default_config())
    assert not result.success
    assert result.data is None
    assert "SC0009" in codes(result.errors)


def test_wrong_type_is_sc0002_and_stops() -> None:
    scene = valid_scene()
    scene["characters"] = "not a list"
    result = validate_scene(scene, default_config())
    assert not result.success
    assert result.data is None
    assert "SC0002" in codes(result.errors)


# --- recoverable warnings continue -----------------------------------------


def test_unexpected_top_level_field_warns_and_continues() -> None:
    scene = valid_scene()
    scene["bogus"] = 1
    result = validate_scene(scene, default_config())
    assert result.success
    assert "SC0015" in codes(result.warnings)
    assert isinstance(result.data, Scene)  # field removed, scene still built


def test_unexpected_character_field_warns() -> None:
    scene = valid_scene()
    scene["characters"][0]["nickname"] = "Ann"
    result = validate_scene(scene, default_config())
    assert result.success
    assert "SC0015" in codes(result.warnings)


def test_allow_unknown_fields_suppresses_warning() -> None:
    scene = valid_scene()
    scene["bogus"] = 1
    config = Config.from_json({"validator": {"allow_unknown_fields": True}})
    result = validate_scene(scene, config)
    assert result.success
    assert "SC0015" not in codes(result.warnings)


def test_empty_concept_is_removed_with_warning() -> None:
    scene = valid_scene()
    scene["characters"][0]["identity"] = ["", "female"]
    result = validate_scene(scene, default_config())
    assert result.success
    assert "SC0016" in codes(result.warnings)
    assert [c.name for c in result.data.characters[0].identity] == ["female"]


def test_whitespace_concept_is_trimmed_and_empty_dropped() -> None:
    scene = valid_scene()
    scene["characters"][0]["identity"] = ["  female  ", "   "]
    result = validate_scene(scene, default_config())
    assert result.success
    assert [c.name for c in result.data.characters[0].identity] == ["female"]
    assert "SC0016" in codes(result.warnings)


def test_dangling_interaction_is_dropped_with_warning() -> None:
    scene = valid_scene()
    scene["interactions"] = [{"participants": [0, 5], "concept": "hug"}]
    result = validate_scene(scene, default_config())
    assert result.success
    assert "SC0017" in codes(result.warnings)
    assert result.data.interactions == ()


def test_valid_interaction_is_kept() -> None:
    scene = valid_scene()
    scene["characters"].append(
        {
            "id": 1,
            "identity": ["male"],
            "appearance": [],
            "clothing": [],
            "accessories": [],
            "pose": [],
            "expression": [],
            "actions": [],
        }
    )
    scene["interactions"] = [{"participants": [0, 1], "concept": "hug"}]
    result = validate_scene(scene, default_config())
    assert result.success
    assert len(result.data.interactions) == 1
    assert "SC0017" not in codes(result.warnings)


# --- guarantees ------------------------------------------------------------


def test_does_not_generate_tags_or_lookup_kb() -> None:
    # Concept names must be preserved verbatim (no tag substitution / KB lookup).
    scene = valid_scene()
    result = validate_scene(scene, default_config())
    assert result.data.characters[0].clothing[0].name == "dress"  # not "dress" -> tag


def test_output_is_deterministic() -> None:
    scene = valid_scene()
    scene["bogus"] = 1
    scene["characters"][0]["identity"] = ["", "female"]
    a = validate_scene(scene, default_config())
    b = validate_scene(scene, default_config())
    assert codes(a.warnings) == codes(b.warnings)


def test_warnings_have_warning_severity() -> None:
    scene = valid_scene()
    scene["bogus"] = 1
    result = validate_scene(scene, default_config())
    assert all(m.severity is Severity.WARNING for m in result.warnings)
