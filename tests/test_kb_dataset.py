"""Tests for the shipped Illustrious Knowledge Base dataset (issue #10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from compiler.common.knowledge_base import load_knowledge_base

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


@pytest.fixture(scope="module")
def kb():
    # Loading succeeds only if the whole dataset validates cleanly (delegated to #9).
    return load_knowledge_base(KB_DIR)


def test_dataset_loads_and_validates_cleanly(kb) -> None:
    assert len(kb) > 100  # a substantive starter set


# Core concepts spanning every reference scenario (single/two characters,
# interactions, indoor/outdoor, fantasy, modern).
CORE_CONCEPTS = [
    "female",
    "male",
    "multiple_girls",
    "long_hair",
    "blue_eyes",
    "dress",
    "school_uniform",
    "smile",
    "standing",
    "walking",
    "hug",
    "holding_hands",
    "chair",
    "sword",
    "classroom",
    "forest",
    "castle",
    "city",
    "beach",
    "close_up",
    "sunset",
    "armor",
    "cat_ears",
]


@pytest.mark.parametrize("concept", CORE_CONCEPTS)
def test_core_concept_is_known(kb, concept: str) -> None:
    assert kb.get(concept) is not None, f"core concept '{concept}' missing from the dataset"


# Frequent synonyms must resolve to their canonical id.
ALIASES = {
    "girl": "female",
    "woman": "female",
    "lady": "female",
    "boy": "male",
    "man": "male",
}


@pytest.mark.parametrize(("alias", "canonical"), list(ALIASES.items()))
def test_alias_resolves(kb, alias: str, canonical: str) -> None:
    assert kb.resolve_alias(alias) == canonical


def test_deterministic_expansions_present(kb) -> None:
    assert set(kb.get("school_uniform").expand) == {"blazer", "pleated_skirt"}
    assert kb.get("twin_braids").expand == ("braid",)
    # Expansion targets exist (the loader would have failed otherwise).
    for target in kb.get("school_uniform").expand:
        assert kb.get(target) is not None


def test_no_subjective_concepts(kb) -> None:
    banned = {"beautiful", "cute", "pretty", "sexy", "gorgeous", "handsome", "hot", "ugly"}
    names = set(kb.by_id) | {alias for entry in kb.by_id.values() for alias in entry.aliases}
    assert banned.isdisjoint(names)


def test_every_entry_has_exactly_one_valid_category(kb) -> None:
    from compiler.common.categories import is_valid_category

    for entry in kb.by_id.values():
        assert isinstance(entry.category, str)
        assert is_valid_category(entry.category)
