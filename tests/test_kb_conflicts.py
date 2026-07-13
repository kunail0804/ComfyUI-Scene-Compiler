"""Tests for Knowledge Base conflict detection (issue #120, epic #35)."""

from __future__ import annotations

from pathlib import Path

from compiler.common.kb_conflicts import detect_conflicts
from scripts.detect_kb_conflicts import _load

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


def test_clean_reference_kb_has_no_conflicts() -> None:
    entries, curated_ids = _load(KB_DIR)
    report = detect_conflicts(entries, curated_ids)
    assert report.total == 0, report.to_json()


def test_fixture_reports_each_conflict_type_and_only_those() -> None:
    entries = [
        # duplicate id
        {"id": "dup", "tags": ["dup a"], "category": "objects"},
        {"id": "dup", "tags": ["dup b"], "category": "objects"},
        # duplicate alias across two entries
        {"id": "a1", "tags": ["a1"], "category": "objects", "aliases": ["shared_alias"]},
        {"id": "a2", "tags": ["a2"], "category": "objects", "aliases": ["shared_alias"]},
        # same tag owned by multiple NON-curated entries
        {"id": "g1", "tags": ["overlap tag"], "category": "objects"},
        {"id": "g2", "tags": ["overlap tag"], "category": "objects"},
        # contradictory (mutual) expansion
        {"id": "x", "tags": ["x"], "category": "objects", "expand": ["y"]},
        {"id": "y", "tags": ["y"], "category": "objects", "expand": ["x"]},
    ]
    report = detect_conflicts(entries, curated_ids=set())
    assert [d["id"] for d in report.duplicate_ids] == ["dup"]
    assert [d["alias"] for d in report.duplicate_aliases] == ["shared_alias"]
    assert [d["tag"] for d in report.tag_multiple_owners] == ["overlap tag"]
    assert report.contradictory_expansions == [{"pair": ["x", "y"]}]
    assert report.total == 4


def test_curated_owner_disambiguates_shared_tag() -> None:
    # A tag shared between a curated entry and a generated one is NOT a conflict
    # (curated wins). Same tag between two generated entries IS.
    entries = [
        {"id": "curated_one", "tags": ["t"], "category": "objects"},
        {"id": "generated_one", "tags": ["t"], "category": "objects"},
    ]
    assert detect_conflicts(entries, curated_ids={"curated_one"}).tag_multiple_owners == []
    assert detect_conflicts(entries, curated_ids=set()).tag_multiple_owners != []
