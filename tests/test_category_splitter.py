"""Tests for the Category Splitter (issue #13, MASTER_SPEC §18)."""

from __future__ import annotations

from compiler.common.categories import CANONICAL_CATEGORIES
from compiler.splitter.category_splitter import split_into_categories
from schemas.models import CategoryMap, ResolvedTag


def tag(name: str, category: str) -> ResolvedTag:
    return ResolvedTag(tag=name, category=category, source_concept=name, knowledge_base_entry=name)


def codes(messages) -> list[str]:
    return [m.code for m in messages]


def test_output_is_a_category_map() -> None:
    result = split_into_categories((tag("1girl", "character"),))
    assert result.success
    assert isinstance(result.data, CategoryMap)


def test_tags_land_in_their_entry_category() -> None:
    tags = (tag("1girl", "character"), tag("blue eyes", "eyes"), tag("long hair", "hair"))
    result = split_into_categories(tags)
    assert [t.tag for t in result.data.tags_for("character")] == ["1girl"]
    assert [t.tag for t in result.data.tags_for("eyes")] == ["blue eyes"]
    assert [t.tag for t in result.data.tags_for("hair")] == ["long hair"]


def test_order_within_category_preserves_resolver_order() -> None:
    tags = (tag("long hair", "hair"), tag("blonde hair", "hair"), tag("bangs", "hair"))
    result = split_into_categories(tags)
    assert [t.tag for t in result.data.tags_for("hair")] == ["long hair", "blonde hair", "bangs"]


def test_empty_categories_are_omitted() -> None:
    result = split_into_categories((tag("1girl", "character"),))
    present = list(result.data.categories.keys())
    assert present == ["character"]  # only the non-empty category


def test_category_ordering_is_canonical() -> None:
    # Provide tags out of canonical order; the map must follow CANONICAL_CATEGORIES.
    tags = (tag("sunset", "lighting"), tag("1girl", "character"), tag("long hair", "hair"))
    result = split_into_categories(tags)
    present = list(result.data.categories.keys())
    assert present == ["character", "hair", "lighting"]
    assert present == [c for c in CANONICAL_CATEGORIES if c in present]


def test_tags_are_not_modified() -> None:
    original = tag("1girl", "character")
    result = split_into_categories((original,))
    assert result.data.tags_for("character")[0] is original


def test_empty_input_produces_empty_map() -> None:
    result = split_into_categories(())
    assert result.success
    assert len(result.data.categories) == 0


def test_invalid_category_stops_with_sc0008() -> None:
    result = split_into_categories((tag("x", "not_a_category"),))
    assert not result.success
    assert result.data is None
    assert "SC0008" in codes(result.errors)
