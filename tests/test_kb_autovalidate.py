"""Tests for the automatic candidate validator (issue #119, epic #35)."""

from __future__ import annotations

import pytest

from compiler.common.kb_autovalidate import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    compute_confidence,
    validate_candidate,
)

VOCAB = {"pantyhose", "elbow_gloves", "gloves", "katana"}


def decide(entry, **overrides):
    kwargs = dict(
        curated_ids={"glasses", "thighhighs"},
        curated_aliases={"spectacles", "thigh highs"},
        known_ids={"pantyhose", "elbow_gloves", "gloves", "katana", "weapon"},
        source_vocab=VOCAB,
    )
    kwargs.update(overrides)
    return validate_candidate(entry, **kwargs)


def codes(decision):
    return [m.code for m in decision.reasons]


def test_well_formed_candidate_is_accepted() -> None:
    decision = decide({"id": "pantyhose", "tags": ["pantyhose"], "category": "clothing"})
    assert decision.accepted
    assert decision.confidence == pytest.approx(1.0)
    assert decision.reasons == []


def test_id_collision_with_curated_is_rejected() -> None:
    decision = decide({"id": "thighhighs", "tags": ["thighhighs"], "category": "clothing"})
    assert not decision.accepted
    assert "SC0005" in codes(decision)


def test_alias_collision_with_curated_is_rejected() -> None:
    decision = decide(
        {
            "id": "pantyhose",
            "tags": ["pantyhose"],
            "category": "clothing",
            "aliases": ["spectacles"],
        }
    )
    assert not decision.accepted
    assert "SC0004" in codes(decision)


def test_unknown_category_is_rejected() -> None:
    decision = decide({"id": "pantyhose", "tags": ["pantyhose"], "category": "not_a_category"})
    assert not decision.accepted
    assert "SC0008" in codes(decision)


def test_self_cycle_expansion_is_rejected() -> None:
    decision = decide(
        {"id": "katana", "tags": ["katana"], "category": "objects", "expand": ["katana"]}
    )
    assert not decision.accepted
    assert "SC0003" in codes(decision)


def test_unknown_expand_target_is_rejected() -> None:
    decision = decide(
        {"id": "katana", "tags": ["katana"], "category": "objects", "expand": ["nonexistent"]}
    )
    assert not decision.accepted
    assert "SC0004" in codes(decision)


def test_below_confidence_threshold_is_rejected() -> None:
    # A tag not in the source vocab scores below threshold (no invention).
    decision = decide({"id": "invented_tag", "tags": ["invented tag"], "category": "clothing"})
    assert not decision.accepted
    assert "SC0022" in codes(decision)
    assert decision.confidence < DEFAULT_CONFIDENCE_THRESHOLD


def test_confidence_scoring() -> None:
    assert compute_confidence({"id": "katana", "category": "objects"}, VOCAB) == pytest.approx(1.0)
    assert compute_confidence({"id": "katana", "category": "bogus"}, VOCAB) == pytest.approx(0.7)
    assert compute_confidence({"id": "unknown", "category": "objects"}, VOCAB) == pytest.approx(0.3)
