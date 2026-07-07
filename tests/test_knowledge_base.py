"""Tests for the Knowledge Base loader (issue #7, §15.11, §27.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compiler.common.knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseError,
    KnowledgeBaseLoader,
    load_knowledge_base,
)
from compiler.common.result import Severity


def write_kb(directory: Path, **files: list[dict]) -> Path:
    for name, entries in files.items():
        (directory / f"{name}.json").write_text(json.dumps(entries), encoding="utf-8")
    return directory


def valid_files() -> dict[str, list[dict]]:
    return {
        "hair": [
            {
                "id": "long_hair",
                "aliases": ["lengthy hair"],
                "tags": ["long hair"],
                "category": "hair",
            },
            {
                "id": "twin_braids",
                "aliases": ["double braids"],
                "tags": ["twin braids"],
                "category": "hair",
                "expand": ["long_hair"],
            },
        ],
        "eyes": [
            {
                "id": "blue_eyes",
                "aliases": ["azure eyes"],
                "tags": ["blue eyes"],
                "category": "eyes",
            },
        ],
    }


# --- successful load --------------------------------------------------------


def test_loads_all_files(tmp_path) -> None:
    kb = load_knowledge_base(write_kb(tmp_path, **valid_files()))
    assert isinstance(kb, KnowledgeBase)
    assert len(kb) == 3
    assert kb.get("long_hair").tags == ("long hair",)
    assert kb.get("blue_eyes").category == "eyes"


def test_id_and_alias_lookups(tmp_path) -> None:
    kb = load_knowledge_base(write_kb(tmp_path, **valid_files()))
    assert kb.resolve_alias("lengthy hair") == "long_hair"
    assert kb.lookup("lengthy hair").id == "long_hair"  # via alias
    assert kb.lookup("long_hair").id == "long_hair"  # via id
    assert kb.lookup("unknown") is None


def test_expand_and_deprecated_preserved(tmp_path) -> None:
    kb = load_knowledge_base(write_kb(tmp_path, **valid_files()))
    assert kb.get("twin_braids").expand == ("long_hair",)
    assert kb.get("long_hair").deprecated is False


def test_empty_directory_is_valid_empty_kb(tmp_path) -> None:
    kb = load_knowledge_base(tmp_path)
    assert len(kb) == 0
    assert kb.get("anything") is None


# --- invalid load -> SC0004 -------------------------------------------------


def test_invalid_kb_raises_sc0004(tmp_path) -> None:
    write_kb(tmp_path, bad=[{"id": "x", "tags": ["x"], "category": "nope"}])
    with pytest.raises(KnowledgeBaseError) as exc:
        load_knowledge_base(tmp_path)
    assert exc.value.message.code == "SC0004"
    assert exc.value.message.severity is Severity.FATAL
    assert exc.value.findings  # the underlying problems are attached


def test_duplicate_id_across_files_fails(tmp_path) -> None:
    write_kb(
        tmp_path,
        a=[{"id": "dup", "tags": ["a"], "category": "hair"}],
        b=[{"id": "dup", "tags": ["b"], "category": "hair"}],
    )
    with pytest.raises(KnowledgeBaseError):
        load_knowledge_base(tmp_path)


def test_invalid_json_file_fails(tmp_path) -> None:
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(KnowledgeBaseError) as exc:
        load_knowledge_base(tmp_path)
    assert exc.value.message.code == "SC0004"


# --- caching and reload -----------------------------------------------------


def test_loader_caches_after_first_get(tmp_path) -> None:
    loader = KnowledgeBaseLoader(write_kb(tmp_path, **valid_files()))
    first = loader.get()
    second = loader.get()
    assert first is second  # loaded once, reused


def test_explicit_reload_picks_up_changes(tmp_path) -> None:
    loader = KnowledgeBaseLoader(write_kb(tmp_path, **valid_files()))
    assert loader.get().get("blue_eyes") is not None
    # Replace the KB on disk.
    for existing in tmp_path.glob("*.json"):
        existing.unlink()
    write_kb(tmp_path, hair=[{"id": "short_hair", "tags": ["short hair"], "category": "hair"}])
    reloaded = loader.reload()
    assert reloaded.get("short_hair") is not None
    assert reloaded.get("blue_eyes") is None


def test_reload_failure_is_side_effect_free(tmp_path) -> None:
    loader = KnowledgeBaseLoader(write_kb(tmp_path, **valid_files()))
    good = loader.get()
    # Corrupt the KB on disk, then reload.
    write_kb(tmp_path, bad=[{"id": "x", "tags": ["x"], "category": "nope"}])
    with pytest.raises(KnowledgeBaseError):
        loader.reload()
    # The previously loaded KB is still intact and returned.
    assert loader.get() is good
    assert loader.get().get("long_hair") is not None


# --- immutability -----------------------------------------------------------


def test_knowledge_base_is_read_only(tmp_path) -> None:
    kb = load_knowledge_base(write_kb(tmp_path, **valid_files()))
    with pytest.raises(TypeError):
        kb.by_id["x"] = None  # type: ignore[index]
