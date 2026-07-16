"""Tests for the shared node Knowledge Base loading helper (was issue #25)."""

from __future__ import annotations

import json

from compiler.common.knowledge_base import KnowledgeBase
from nodes.kb_loading import load_cached_knowledge_base


def write_kb(directory, entries: list[dict]) -> str:
    (directory / "hair.json").write_text(json.dumps(entries), encoding="utf-8")
    return str(directory)


def test_loads_knowledge_base(tmp_path) -> None:
    path = write_kb(tmp_path, [{"id": "long_hair", "tags": ["long hair"], "category": "hair"}])
    kb, warnings, errors, *_ = load_cached_knowledge_base(path)
    assert isinstance(kb, KnowledgeBase)
    assert kb.get("long_hair") is not None
    assert (warnings, errors) == ("", "")


def test_invalid_knowledge_base_surfaces_sc0004(tmp_path) -> None:
    path = write_kb(tmp_path, [{"id": "x", "tags": ["x"], "category": "nope"}])
    kb, warnings, errors, *_ = load_cached_knowledge_base(path)
    assert kb is None
    assert "SC0004" in errors


def test_relative_path_resolves_against_package(monkeypatch, tmp_path) -> None:
    # Even with an unrelated working directory (as under ComfyUI), the default
    # relative path must load the shipped Knowledge Base, not an empty one.
    monkeypatch.chdir(tmp_path)
    kb, warnings, errors, raw = load_cached_knowledge_base("knowledge_base/")
    assert isinstance(kb, KnowledgeBase)
    assert len(kb) > 100
    assert (warnings, errors) == ("", "")
    assert "entries" in raw


def test_empty_knowledge_base_warns(tmp_path) -> None:
    kb, warnings, errors, raw = load_cached_knowledge_base(str(tmp_path))
    assert len(kb) == 0
    assert "empty" in warnings.lower()


def test_reload_input_is_accepted(tmp_path) -> None:
    path = write_kb(tmp_path, [{"id": "long_hair", "tags": ["long hair"], "category": "hair"}])
    kb, _, _, _ = load_cached_knowledge_base(path, reload=5)
    assert isinstance(kb, KnowledgeBase)
