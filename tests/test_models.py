"""Tests for the typed data models (issue #3, MASTER_SPEC §9).

Covers construction, JSON serialization in both directions, lossless round-trips,
schema conformance of serialized output (cross-check with issue #2), and
immutability of produced models.
"""

from __future__ import annotations

import dataclasses

import pytest

from schemas.models import (
    Character,
    Concept,
    Interaction,
    Metadata,
    ResolvedTag,
    Scene,
    SceneObject,
)
from schemas.validation import validate_document

# --- Concept ---------------------------------------------------------------


def test_concept_from_bare_string() -> None:
    c = Concept.from_json("female")
    assert c.name == "female"
    assert c.category is None
    assert not c.metadata


def test_concept_from_object() -> None:
    c = Concept.from_json({"name": "long_hair", "category": "hair", "source": "sentence 1"})
    assert (c.name, c.category, c.source) == ("long_hair", "hair", "sentence 1")


def test_concept_confidence_lives_in_metadata() -> None:
    c = Concept.from_json({"name": "female", "metadata": {"confidence": 0.98}})
    assert c.metadata["confidence"] == pytest.approx(0.98)


def test_concept_bare_string_serializes_back_to_string() -> None:
    assert Concept.from_json("female").to_json() == "female"


def test_concept_with_extra_fields_serializes_to_object() -> None:
    c = Concept(name="female", category="identity")
    assert c.to_json() == {"name": "female", "category": "identity"}


def test_concept_roundtrip_lossless_string() -> None:
    c = Concept.from_json("female")
    assert Concept.from_json(c.to_json()) == c


def test_concept_roundtrip_lossless_object() -> None:
    data = {"name": "female", "category": "identity", "metadata": {"confidence": 0.5}}
    c = Concept.from_json(data)
    assert Concept.from_json(c.to_json()) == c


def test_concept_serialized_forms_validate_against_schema() -> None:
    for data in ["female", {"name": "female", "category": "identity"}]:
        assert validate_document(Concept.from_json(data).to_json(), "concept") == []


# --- Character -------------------------------------------------------------


def sample_character() -> Character:
    return Character.from_json(
        {
            "id": 0,
            "identity": ["female"],
            "appearance": [{"name": "long_hair", "category": "hair"}],
            "clothing": [],
            "accessories": [],
            "pose": ["standing"],
            "expression": ["smile"],
            "actions": [],
        }
    )


def test_character_construction_and_fields() -> None:
    ch = sample_character()
    assert ch.id == 0
    assert ch.identity[0].name == "female"
    assert ch.appearance[0].category == "hair"


def test_character_roundtrip_lossless() -> None:
    ch = sample_character()
    assert Character.from_json(ch.to_json()) == ch


def test_character_serialized_validates_against_schema() -> None:
    assert validate_document(sample_character().to_json(), "character") == []


# --- Interaction -----------------------------------------------------------


def test_interaction_roundtrip_and_schema() -> None:
    i = Interaction.from_json({"participants": [0, 1], "concept": "holding hands"})
    assert i.participants == (0, 1)
    assert Interaction.from_json(i.to_json()) == i
    assert validate_document(i.to_json(), "interaction") == []


# --- Metadata --------------------------------------------------------------


def test_metadata_roundtrip_minimal() -> None:
    m = Metadata.from_json({"schema_version": "1.0"})
    assert m.schema_version == "1.0"
    assert Metadata.from_json(m.to_json()) == m
    assert validate_document(m.to_json(), "metadata") == []


def test_metadata_roundtrip_full() -> None:
    data = {
        "schema_version": "1.0",
        "compiler_version": "0.1.0",
        "language": "en",
        "warnings": ["W001: something"],
    }
    m = Metadata.from_json(data)
    assert Metadata.from_json(m.to_json()) == m
    assert validate_document(m.to_json(), "metadata") == []


# --- ResolvedTag -----------------------------------------------------------


def test_resolved_tag_roundtrip_and_schema() -> None:
    data = {
        "tag": "blue eyes",
        "category": "eyes",
        "source_concept": "blue eyes",
        "knowledge_base_entry": "blue_eyes",
    }
    t = ResolvedTag.from_json(data)
    assert ResolvedTag.from_json(t.to_json()) == t
    assert validate_document(t.to_json(), "resolved_tag") == []


# --- SceneObject (V1 == Concept) -------------------------------------------


def test_scene_object_is_concept() -> None:
    assert SceneObject is Concept


# --- Scene -----------------------------------------------------------------


def sample_scene() -> Scene:
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": ["female"],
                    "appearance": [],
                    "clothing": [],
                    "accessories": [],
                    "pose": [],
                    "expression": [],
                    "actions": [],
                }
            ],
            "interactions": [{"participants": [0], "concept": "waving"}],
            "objects": ["chair"],
            "environment": ["classroom"],
            "camera": [],
            "lighting": ["sunset"],
            "metadata": {"schema_version": "1.0"},
        }
    )


def test_scene_construction() -> None:
    scene = sample_scene()
    assert scene.characters[0].identity[0].name == "female"
    assert scene.objects[0].name == "chair"
    assert scene.metadata.schema_version == "1.0"


def test_scene_roundtrip_lossless() -> None:
    scene = sample_scene()
    assert Scene.from_json(scene.to_json()) == scene


def test_empty_scene_roundtrip_and_schema() -> None:
    empty = {
        "characters": [],
        "interactions": [],
        "objects": [],
        "environment": [],
        "camera": [],
        "lighting": [],
        "metadata": {"schema_version": "1.0"},
    }
    scene = Scene.from_json(empty)
    assert Scene.from_json(scene.to_json()) == scene
    assert validate_document(scene.to_json(), "scene") == []


def test_scene_serialized_validates_against_schema() -> None:
    assert validate_document(sample_scene().to_json(), "scene") == []


# --- Immutability ----------------------------------------------------------


def test_models_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_character().id = 1  # type: ignore[misc]


def test_concept_metadata_is_read_only() -> None:
    c = Concept.from_json({"name": "female", "metadata": {"confidence": 0.9}})
    with pytest.raises(TypeError):
        c.metadata["confidence"] = 0.1  # type: ignore[index]


def test_scene_collections_are_immutable_tuples() -> None:
    scene = sample_scene()
    assert isinstance(scene.characters, tuple)
    assert isinstance(scene.environment, tuple)
