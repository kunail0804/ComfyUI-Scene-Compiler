"""Tests for Analyzer response parsing and validation (issue #17, §12.2, §12.8)."""

from __future__ import annotations

import json

from compiler.analyzer.response_parser import parse_scene_response
from schemas.models import Scene


def scene_response(**overrides) -> str:
    scene = {
        "characters": [
            {
                "id": 0,
                "identity": ["female"],
                "appearance": ["blonde hair"],
                "clothing": [],
                "accessories": [],
                "pose": [],
                "expression": [],
                "actions": ["walking"],
            }
        ],
        "interactions": [],
        "objects": [],
        "environment": ["rain"],
        "camera": [],
        "lighting": [],
        "metadata": {},
    }
    scene.update(overrides)
    return json.dumps(scene)


def codes(messages) -> list[str]:
    return [m.code for m in messages]


# --- valid responses -------------------------------------------------------


def test_valid_response_parses_to_scene() -> None:
    result = parse_scene_response(scene_response())
    assert result.success
    assert isinstance(result.data, Scene)
    assert result.data.characters[0].identity[0].name == "female"
    assert result.data.environment[0].name == "rain"


def test_empty_metadata_is_stamped_with_schema_version() -> None:
    # §12.2 shows the Analyzer emitting `"metadata": {}`; the parser stamps the
    # compiler-owned schema_version so the document validates.
    result = parse_scene_response(scene_response())
    assert result.success
    assert result.data.metadata.schema_version


def test_object_and_string_concept_forms() -> None:
    scene = json.loads(scene_response())
    scene["characters"][0]["appearance"] = [
        "blonde hair",
        {"name": "blue eyes", "metadata": {"confidence": 0.9}},
    ]
    result = parse_scene_response(json.dumps(scene))
    assert result.success
    appearance = result.data.characters[0].appearance
    assert appearance[0].name == "blonde hair"
    assert appearance[1].name == "blue eyes"
    assert appearance[1].metadata["confidence"]  # confidence stays metadata-only


# --- invalid responses -> SC0011 -------------------------------------------


def test_malformed_json_is_rejected() -> None:
    result = parse_scene_response("{ not valid json")
    assert not result.success
    assert result.data is None
    assert "SC0011" in codes(result.errors)


def test_non_object_json_is_rejected() -> None:
    result = parse_scene_response("[1, 2, 3]")
    assert not result.success
    assert "SC0011" in codes(result.errors)


def test_missing_required_field_is_rejected() -> None:
    scene = json.loads(scene_response())
    del scene["characters"]
    result = parse_scene_response(json.dumps(scene))
    assert not result.success
    assert "SC0011" in codes(result.errors)


def test_wrong_type_is_rejected() -> None:
    scene = json.loads(scene_response())
    scene["characters"] = "not a list"
    result = parse_scene_response(json.dumps(scene))
    assert not result.success
    assert "SC0011" in codes(result.errors)


def test_json_fenced_response_is_unwrapped() -> None:
    # Most local models wrap JSON in a ```json fence; unwrapping is not repair.
    result = parse_scene_response("```json\n" + scene_response() + "\n```")
    assert result.success
    assert isinstance(result.data, Scene)


def test_plain_fenced_response_is_unwrapped() -> None:
    result = parse_scene_response("```\n" + scene_response() + "\n```")
    assert result.success


def test_fenced_but_malformed_json_still_fails() -> None:
    # Unwrapping only removes the fence; malformed JSON inside is still rejected.
    result = parse_scene_response("```json\n{ not valid json\n```")
    assert not result.success
    assert "SC0011" in codes(result.errors)
