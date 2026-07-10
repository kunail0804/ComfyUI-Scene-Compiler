"""Tests for the JSON Schema validation helper (issue #2, MASTER_SPEC §11).

Covers, per schema, at least one valid document and several invalid documents
(wrong types, missing required fields, unknown fields), plus the configurable
unknown-field behaviour.
"""

from __future__ import annotations

import pytest

from schemas.validation import ValidationIssue, list_schemas, validate_document

# --- helpers ---------------------------------------------------------------


def valid_metadata() -> dict:
    return {"schema_version": "1.0"}


def valid_scene() -> dict:
    return {
        "characters": [],
        "interactions": [],
        "objects": [],
        "environment": [],
        "camera": [],
        "lighting": [],
        "metadata": valid_metadata(),
    }


def valid_character() -> dict:
    return {
        "id": 0,
        "identity": ["female"],
        "appearance": [{"name": "long_hair", "category": "hair"}],
        "clothing": [],
        "accessories": [],
        "pose": [],
        "expression": ["smile"],
        "actions": [],
    }


# --- generic behaviour -----------------------------------------------------


def test_valid_scene_passes() -> None:
    assert validate_document(valid_scene(), "scene") == []


def test_returns_structured_issue_objects() -> None:
    issues = validate_document({"characters": []}, "scene")
    assert issues
    assert all(isinstance(i, ValidationIssue) for i in issues)
    assert all(i.message for i in issues)


def test_unknown_schema_name_raises() -> None:
    with pytest.raises(KeyError):
        validate_document({}, "does_not_exist")


def test_core_schemas_are_registered() -> None:
    expected = {
        "scene",
        "character",
        "concept",
        "interaction",
        "metadata",
        "knowledge_base_entry",
        "resolved_tag",
    }
    assert expected.issubset(set(list_schemas()))


# --- scene -----------------------------------------------------------------


def test_scene_missing_required_field_fails() -> None:
    doc = valid_scene()
    del doc["metadata"]
    issues = validate_document(doc, "scene")
    assert any("metadata" in i.message or "metadata" in i.path for i in issues)


def test_scene_unknown_field_rejected_by_default() -> None:
    doc = valid_scene()
    doc["extra"] = 1
    assert validate_document(doc, "scene") != []


def test_scene_unknown_field_allowed_when_configured() -> None:
    doc = valid_scene()
    doc["extra"] = 1
    assert validate_document(doc, "scene", allow_unknown=True) == []


def test_scene_with_populated_nested_documents_passes() -> None:
    doc = valid_scene()
    doc["characters"] = [valid_character()]
    doc["interactions"] = [{"participants": [0], "concept": "holding hands"}]
    doc["objects"] = ["chair"]
    doc["environment"] = ["classroom"]
    assert validate_document(doc, "scene") == []


# --- character -------------------------------------------------------------


def test_valid_character_passes() -> None:
    assert validate_document(valid_character(), "character") == []


def test_character_id_must_be_integer() -> None:
    doc = valid_character()
    doc["id"] = "0"
    assert validate_document(doc, "character") != []


def test_character_missing_field_fails() -> None:
    doc = valid_character()
    del doc["identity"]
    assert validate_document(doc, "character") != []


# --- concept ---------------------------------------------------------------


def test_concept_bare_string_valid() -> None:
    assert validate_document("blue_eyes", "concept") == []


def test_concept_object_valid() -> None:
    assert validate_document({"name": "blue_eyes", "category": "eyes"}, "concept") == []


def test_concept_object_without_name_fails() -> None:
    assert validate_document({"category": "eyes"}, "concept") != []


def test_concept_unknown_field_rejected_by_default() -> None:
    assert validate_document({"name": "x", "bogus": 1}, "concept") != []


def test_concept_unknown_field_allowed_when_configured() -> None:
    assert validate_document({"name": "x", "bogus": 1}, "concept", allow_unknown=True) == []


# --- interaction -----------------------------------------------------------


def test_valid_interaction_passes() -> None:
    assert validate_document({"participants": [0, 1], "concept": "hug"}, "interaction") == []


def test_interaction_participants_must_be_integers() -> None:
    assert validate_document({"participants": ["a"], "concept": "hug"}, "interaction") != []


def test_interaction_missing_concept_fails() -> None:
    assert validate_document({"participants": [0]}, "interaction") != []


# --- metadata --------------------------------------------------------------


def test_valid_metadata_passes() -> None:
    assert validate_document({"schema_version": "1.0", "warnings": []}, "metadata") == []


def test_metadata_missing_schema_version_fails() -> None:
    assert validate_document({"warnings": []}, "metadata") != []


def test_metadata_warnings_must_be_array() -> None:
    assert validate_document({"schema_version": "1.0", "warnings": "oops"}, "metadata") != []


# --- knowledge base entry --------------------------------------------------


def valid_kb_entry() -> dict:
    return {"id": "blonde_hair", "tags": ["blonde hair"], "category": "hair"}


def test_valid_kb_entry_passes() -> None:
    assert validate_document(valid_kb_entry(), "knowledge_base_entry") == []


def test_kb_entry_id_must_be_snake_case() -> None:
    doc = valid_kb_entry()
    doc["id"] = "Blonde Hair"
    assert validate_document(doc, "knowledge_base_entry") != []


def test_kb_entry_category_must_be_string() -> None:
    doc = valid_kb_entry()
    doc["category"] = 5
    assert validate_document(doc, "knowledge_base_entry") != []


# --- resolved tag ----------------------------------------------------------


def valid_resolved_tag() -> dict:
    return {
        "tag": "blue eyes",
        "category": "eyes",
        "source_concept": "blue eyes",
        "knowledge_base_entry": "blue_eyes",
    }


def test_valid_resolved_tag_passes() -> None:
    assert validate_document(valid_resolved_tag(), "resolved_tag") == []


def test_resolved_tag_missing_field_fails() -> None:
    doc = valid_resolved_tag()
    del doc["knowledge_base_entry"]
    assert validate_document(doc, "resolved_tag") != []
