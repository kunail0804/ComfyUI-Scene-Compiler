"""Tests for the Knowledge Base Editor backend (issues #123, #125, #126)."""

from __future__ import annotations

import json

import pytest

from compiler.common.knowledge_base import load_knowledge_base
from nodes.kb_editor import handlers, service
from schemas.validation import validate_document

CURATED = """[
  { "id": "dress", "tags": ["dress"], "category": "clothing" },
  { "id": "thighhighs", "tags": ["thighhighs"], "category": "clothing" },
  { "id": "jacket", "tags": ["jacket"], "category": "clothing" }
]
"""


@pytest.fixture
def kb_dir(tmp_path):
    (tmp_path / "clothing.json").write_text(CURATED, encoding="utf-8")
    # A generated file to prove collisions are checked against the whole KB state.
    (tmp_path / "gen_objects.json").write_text(
        '[{"id": "gen_sword", "tags": ["sword"], "category": "objects"}]', encoding="utf-8"
    )
    return tmp_path


# --- CRUD read paths --------------------------------------------------------


def test_list_and_get_curated_entries(kb_dir) -> None:
    ids = [e["id"] for e in service.list_entries(kb_dir)]
    assert ids == ["dress", "jacket", "thighhighs"]  # sorted, generated file excluded
    assert service.get_entry(kb_dir, "dress")["tags"] == ["dress"]
    assert service.get_entry(kb_dir, "missing") is None


def test_list_handler_shape(kb_dir) -> None:
    status, payload = handlers.api_list(kb_dir)
    assert status == 200
    assert {e["id"] for e in payload["entries"]} == {"dress", "jacket", "thighhighs"}


# --- create / update / delete -----------------------------------------------


def test_create_valid_entry_persists_and_loads(kb_dir) -> None:
    status, payload = handlers.api_create(
        kb_dir, {"entry": {"id": "skirt", "tags": ["skirt"], "category": "clothing"}}
    )
    assert status == 200 and payload["saved"]
    kb = load_knowledge_base(kb_dir)  # whole KB still valid
    assert kb.get("skirt") is not None
    # File still validates entry-by-entry against the schema.
    for entry in json.loads((kb_dir / "clothing.json").read_text(encoding="utf-8")):
        assert validate_document(entry, "knowledge_base_entry") == []


def test_update_changes_only_edited_entry(kb_dir) -> None:
    before = (kb_dir / "clothing.json").read_text(encoding="utf-8").splitlines()
    service.save_entry(
        kb_dir, {"id": "jacket", "tags": ["jacket", "coat"], "category": "clothing"}, "jacket"
    )
    after = (kb_dir / "clothing.json").read_text(encoding="utf-8").splitlines()
    # Only the "jacket" line changed; dress and thighhighs lines are byte-identical.
    assert before[1] == after[1]  # dress
    assert before[2] == after[2]  # thighhighs
    assert before[3] != after[3]  # jacket edited
    assert load_knowledge_base(kb_dir).get("jacket").tags == ("jacket", "coat")


def test_delete_removes_entry(kb_dir) -> None:
    status, payload = handlers.api_delete(kb_dir, "dress")
    assert status == 200 and payload["deleted"]
    assert service.get_entry(kb_dir, "dress") is None
    assert load_knowledge_base(kb_dir).get("dress") is None
    assert handlers.api_delete(kb_dir, "dress")[0] == 404  # already gone


# --- validation (single source of truth) ------------------------------------


def _validate(kb_dir, entry, original_id=None):
    return service.validate(kb_dir, entry, original_id)


def test_duplicate_id_rejected(kb_dir) -> None:
    errors = _validate(kb_dir, {"id": "dress", "tags": ["x"], "category": "clothing"})
    assert any(e["code"] == "SC0005" and e["field"] == "id" for e in errors)


def test_alias_collision_rejected(kb_dir) -> None:
    errors = _validate(
        kb_dir, {"id": "leggings", "tags": ["x"], "category": "clothing", "aliases": ["dress"]}
    )
    assert any(e["field"] == "aliases" for e in errors)


def test_unknown_category_rejected(kb_dir) -> None:
    errors = _validate(kb_dir, {"id": "x", "tags": ["x"], "category": "nope"})
    assert any(e["code"] == "SC0008" and e["field"] == "category" for e in errors)


def test_cyclic_expansion_rejected(kb_dir) -> None:
    errors = _validate(
        kb_dir, {"id": "dress", "tags": ["dress"], "category": "clothing", "expand": ["dress"]}
    )
    assert any(e["field"] == "expand" for e in errors)


def test_valid_entry_passes_validation(kb_dir) -> None:
    assert _validate(kb_dir, {"id": "boots", "tags": ["boots"], "category": "clothing"}) == []


def test_create_invalid_entry_is_blocked_with_400(kb_dir) -> None:
    status, payload = handlers.api_create(
        kb_dir, {"entry": {"id": "dress", "tags": ["x"], "category": "clothing"}}
    )
    assert status == 400 and payload["saved"] is False and payload["errors"]
    # The invalid entry was NOT written.
    assert len(service.list_entries(kb_dir)) == 3


# --- atomic, format-safe saves (#126) ---------------------------------------


def test_save_is_atomic_on_failure(kb_dir, monkeypatch) -> None:
    original = (kb_dir / "clothing.json").read_text(encoding="utf-8")

    def boom(*_a, **_k):
        raise OSError("simulated crash during rename")

    monkeypatch.setattr(service.os, "replace", boom)
    with pytest.raises(OSError):
        service.save_entry(kb_dir, {"id": "skirt", "tags": ["skirt"], "category": "clothing"})
    # The original file is untouched and no temp file was left behind.
    assert (kb_dir / "clothing.json").read_text(encoding="utf-8") == original
    assert not list(kb_dir.glob("*.tmp"))


def test_saved_entry_uses_canonical_key_order(kb_dir) -> None:
    service.save_entry(
        kb_dir,
        {"category": "clothing", "tags": ["socks"], "id": "socks", "aliases": ["sock"]},
    )
    line = next(
        ln
        for ln in (kb_dir / "clothing.json").read_text(encoding="utf-8").splitlines()
        if '"socks"' in ln
    )
    # Canonical order: id, aliases, tags, category.
    assert (
        line.index('"id"')
        < line.index('"aliases"')
        < line.index('"tags"')
        < line.index('"category"')
    )


# --- import safety ----------------------------------------------------------


def test_register_routes_is_noop_without_comfyui() -> None:
    from nodes.kb_editor.routes import register_routes

    assert register_routes() is False  # no PromptServer available in tests
