"""Tests for the automated KB build pipeline (issue #122, epic #35)."""

from __future__ import annotations

from pathlib import Path

from scripts import build_knowledge_base as pipe
from scripts import generate_kb_from_vocab as gen


def test_dry_run_pipeline_succeeds(monkeypatch) -> None:
    # Mirror CI: no external vocab source, so the committed snapshot is used.
    monkeypatch.setattr(pipe.build_vocab, "_SOURCE", Path("/nonexistent/source.txt"))
    assert pipe.run_pipeline(write=False) == 0  # clean: no rejections, no conflicts


def test_candidate_generation_is_deterministic() -> None:
    assert gen.build_generated_entries() == gen.build_generated_entries()


def test_validation_rejects_bad_candidates() -> None:
    by_category = {
        "objects": [
            {"id": "real_tag", "tags": ["real tag"], "category": "objects"},
            {"id": "bad_category", "tags": ["bad"], "category": "not_a_category"},
        ]
    }
    rejections = pipe.validate_candidates(
        by_category,
        curated_ids=set(),
        curated_aliases=set(),
        source_vocab={"real_tag", "bad_category"},
    )
    ids = {r["id"] for r in rejections}
    assert ids == {"bad_category"}  # only the malformed candidate is rejected


def test_collision_with_curated_is_rejected() -> None:
    by_category = {"objects": [{"id": "sword", "tags": ["sword"], "category": "objects"}]}
    rejections = pipe.validate_candidates(
        by_category,
        curated_ids={"sword"},  # curated already owns "sword"
        curated_aliases=set(),
        source_vocab={"sword"},
    )
    assert [r["id"] for r in rejections] == ["sword"]
