"""Tests for the Knowledge Base dataset manifest (issue #127, epic #36)."""

from __future__ import annotations

import json
from pathlib import Path

from compiler.common.kb_manifest import (
    IMPLICIT_VERSION,
    MANIFEST_FILENAME,
    compute_content_hash,
    load_manifest,
    write_manifest,
)
from compiler.common.knowledge_base import load_knowledge_base
from schemas.validation import validate_document

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "knowledge_base"


# --- shipped reference manifest --------------------------------------------


def test_reference_manifest_exists_and_validates() -> None:
    data = json.loads((KB_DIR / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert validate_document(data, "knowledge_base_manifest") == []
    assert data["version"] == "1.0.0"


def test_loader_reads_manifest_version() -> None:
    kb = load_knowledge_base(KB_DIR)
    assert kb.version == "1.0.0"


def test_manifest_content_hash_matches_current_entries() -> None:
    # The committed manifest is a faithful, deterministic stamp of the dataset.
    manifest = load_manifest(KB_DIR)
    assert manifest.content_hash == compute_content_hash(KB_DIR)


# --- backward compatibility -------------------------------------------------


def test_missing_manifest_defaults_to_implicit_v1(tmp_path) -> None:
    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]',
        encoding="utf-8",
    )
    assert load_manifest(tmp_path).version == IMPLICIT_VERSION
    assert load_knowledge_base(tmp_path).version == IMPLICIT_VERSION


# --- determinism ------------------------------------------------------------


def test_write_manifest_is_deterministic(tmp_path) -> None:
    vocab = tmp_path / "vocab.txt"
    vocab.write_text("clothing\tshirt\n", encoding="utf-8")
    (tmp_path / "clothing.json").write_text(
        '[{"id": "shirt", "tags": ["shirt"], "category": "clothing"}]',
        encoding="utf-8",
    )
    first = write_manifest(tmp_path, "2.0.0", vocab)
    first_bytes = (tmp_path / MANIFEST_FILENAME).read_bytes()
    second = write_manifest(tmp_path, "2.0.0", vocab)
    second_bytes = (tmp_path / MANIFEST_FILENAME).read_bytes()
    assert first == second
    assert first_bytes == second_bytes  # byte-identical regeneration


def test_requesting_available_version_loads(tmp_path) -> None:
    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]',
        encoding="utf-8",
    )
    write_manifest(tmp_path, "3.1.0", tmp_path / "missing_vocab.txt")
    kb = load_knowledge_base(tmp_path, requested_version="3.1.0")
    assert kb.version == "3.1.0"
    assert kb.get("long_hair") is not None


def test_requesting_unavailable_version_errors_clearly(tmp_path) -> None:
    from compiler.common.knowledge_base import KnowledgeBaseError

    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]',
        encoding="utf-8",
    )
    write_manifest(tmp_path, "3.1.0", tmp_path / "missing_vocab.txt")
    try:
        load_knowledge_base(tmp_path, requested_version="9.9.9")
    except KnowledgeBaseError as error:
        assert error.message.code == "SC0004"
        assert "9.9.9" in error.message.description
        assert error.message.context["available_version"] == "3.1.0"
    else:
        raise AssertionError("expected KnowledgeBaseError for unavailable version")


def test_manifest_is_not_read_as_an_entry_file(tmp_path) -> None:
    # A manifest.json in the KB dir must not break loading (it is not an entry array).
    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]',
        encoding="utf-8",
    )
    write_manifest(tmp_path, "1.0.0", tmp_path / "missing_vocab.txt")
    kb = load_knowledge_base(tmp_path)
    assert len(kb) == 1  # the manifest was skipped, only the one entry loaded
