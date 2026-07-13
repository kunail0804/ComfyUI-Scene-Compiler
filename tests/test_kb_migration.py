"""Tests for cross-version Knowledge Base loading (issue #129, epic #36)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compiler.common.kb_manifest import (
    MANIFEST_FILENAME,
    compute_content_hash,
    load_manifest,
)
from compiler.common.kb_migration import (
    CURRENT_ENTRY_SCHEMA_VERSION,
    UnsupportedKnowledgeBaseVersion,
    adapt_entries,
)
from compiler.common.knowledge_base import KnowledgeBaseError, load_knowledge_base

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "knowledge_base"


def _write_manifest(directory: Path, entry_schema_version: str) -> None:
    (directory / MANIFEST_FILENAME).write_text(
        json.dumps(
            {
                "manifest_schema_version": "1.0",
                "version": "1.0.0",
                "content_hash": compute_content_hash(directory),
                "entry_schema_version": entry_schema_version,
            }
        ),
        encoding="utf-8",
    )


# --- adapter unit level -----------------------------------------------------


def test_no_source_version_is_treated_as_current() -> None:
    entries = [{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]
    assert adapt_entries(entries, None) == entries


def test_adapter_1_0_translates_nsfw_to_rating() -> None:
    entries = [
        {"id": "a", "tags": ["a"], "category": "body", "nsfw": True},
        {"id": "b", "tags": ["b"], "category": "body", "nsfw": False},
    ]
    adapted = adapt_entries(entries, "1.0")
    assert adapted[0]["rating"] == "explicit" and "nsfw" not in adapted[0]
    assert adapted[1]["rating"] == "general" and "nsfw" not in adapted[1]
    assert entries[0]["nsfw"] is True  # inputs not mutated


def test_too_old_version_raises() -> None:
    with pytest.raises(UnsupportedKnowledgeBaseVersion):
        adapt_entries([], "0.9")


# --- loader level -----------------------------------------------------------


def test_current_reference_kb_loads_without_adaptation() -> None:
    assert load_manifest(KB_DIR).entry_schema_version is None
    kb = load_knowledge_base(KB_DIR)  # loads clean, no migration applied
    assert len(kb) > 100


def test_older_dataset_adapts_and_resolves(tmp_path) -> None:
    (tmp_path / "body.json").write_text(
        json.dumps(
            [{"id": "bare_shoulders", "tags": ["bare shoulders"], "category": "body", "nsfw": True}]
        ),
        encoding="utf-8",
    )
    _write_manifest(tmp_path, "1.0")
    kb = load_knowledge_base(tmp_path)
    entry = kb.get("bare_shoulders")
    assert entry is not None
    assert entry.rating == "explicit"  # adapted from nsfw=true


def test_unsupported_old_dataset_errors_clearly(tmp_path) -> None:
    (tmp_path / "hair.json").write_text(
        json.dumps([{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]),
        encoding="utf-8",
    )
    _write_manifest(tmp_path, "0.9")
    with pytest.raises(KnowledgeBaseError) as exc:
        load_knowledge_base(tmp_path)
    assert exc.value.message.code == "SC0004"
    assert "0.9" in exc.value.message.description


def test_current_version_string_matches_entry_schema_file() -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas" / "json" / "knowledge_base_entry.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["version"] == CURRENT_ENTRY_SCHEMA_VERSION
