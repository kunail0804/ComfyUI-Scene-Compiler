"""Tests for the Knowledge Base file format and entry schema (issue #8, §15, §18.2)."""

from __future__ import annotations

import json
from pathlib import Path

from compiler.common.categories import CANONICAL_CATEGORIES, is_valid_category
from schemas.validation import validate_document

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = REPO_ROOT / "examples" / "knowledge_base.example.json"
ENTRY_SCHEMA_FILE = REPO_ROOT / "schemas" / "json" / "knowledge_base_entry.schema.json"


# --- categories (single source of truth) -----------------------------------


def test_there_are_nineteen_categories() -> None:
    assert len(CANONICAL_CATEGORIES) == 19
    assert len(set(CANONICAL_CATEGORIES)) == 19  # all unique


def test_expected_categories_present() -> None:
    for name in ("character", "hair", "eyes", "clothing", "miscellaneous"):
        assert name in CANONICAL_CATEGORIES
        assert is_valid_category(name)


def test_unknown_category_is_invalid() -> None:
    assert not is_valid_category("not_a_category")


def test_schema_category_enum_matches_constant() -> None:
    schema = json.loads(ENTRY_SCHEMA_FILE.read_text(encoding="utf-8"))
    assert set(schema["properties"]["category"]["enum"]) == set(CANONICAL_CATEGORIES)


# --- entry schema ----------------------------------------------------------


def valid_entry() -> dict:
    return {"id": "long_hair", "tags": ["long hair"], "category": "hair"}


def test_valid_entry_passes() -> None:
    assert validate_document(valid_entry(), "knowledge_base_entry") == []


def test_entry_category_must_be_one_of_the_19() -> None:
    entry = valid_entry()
    entry["category"] = "hairstyle"
    assert validate_document(entry, "knowledge_base_entry") != []


def test_entry_requires_at_least_one_tag() -> None:
    entry = valid_entry()
    entry["tags"] = []
    assert validate_document(entry, "knowledge_base_entry") != []


def test_entry_id_must_be_snake_case() -> None:
    entry = valid_entry()
    entry["id"] = "Long Hair"
    assert validate_document(entry, "knowledge_base_entry") != []


def test_entry_expand_must_reference_snake_case_ids() -> None:
    entry = valid_entry()
    entry["expand"] = ["Not Snake"]
    assert validate_document(entry, "knowledge_base_entry") != []


def test_entry_unknown_field_rejected() -> None:
    entry = valid_entry()
    entry["colour"] = "brown"
    assert validate_document(entry, "knowledge_base_entry") != []


def test_full_entry_with_aliases_and_expand_valid() -> None:
    entry = {
        "id": "twin_braids",
        "aliases": ["twintail braids", "double braids"],
        "tags": ["twin braids"],
        "category": "hair",
        "expand": ["long_hair"],
        "deprecated": False,
        "notes": "Composite hairstyle.",
    }
    assert validate_document(entry, "knowledge_base_entry") == []


# --- worked example file ---------------------------------------------------


def load_example_entries() -> list[dict]:
    return json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))


def test_example_file_is_an_array_of_entries() -> None:
    entries = load_example_entries()
    assert isinstance(entries, list)
    assert len(entries) >= 2


def test_every_example_entry_validates() -> None:
    for entry in load_example_entries():
        assert validate_document(entry, "knowledge_base_entry") == []


def test_example_demonstrates_alias_and_expansion() -> None:
    entries = load_example_entries()
    assert any(entry.get("aliases") for entry in entries), "no entry demonstrates an alias"
    assert any(entry.get("expand") for entry in entries), "no entry demonstrates an expansion"


def test_example_expand_targets_exist_in_file() -> None:
    entries = load_example_entries()
    ids = {entry["id"] for entry in entries}
    for entry in entries:
        for target in entry.get("expand", []):
            assert target in ids, f"expand target '{target}' missing from example"
