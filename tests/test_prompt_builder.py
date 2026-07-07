"""Tests for the Prompt Builder (issue #14, MASTER_SPEC §19)."""

from __future__ import annotations

from types import MappingProxyType

from compiler.builder.prompt_builder import RESERVED_OUTPUTS, build_prompts
from compiler.common.categories import CANONICAL_CATEGORIES
from compiler.common.config import Config
from schemas.models import CategoryMap, ResolvedTag


def rtag(name: str, category: str) -> ResolvedTag:
    return ResolvedTag(tag=name, category=category, source_concept=name, knowledge_base_entry=name)


def category_map(**by_category: list[ResolvedTag]) -> CategoryMap:
    return CategoryMap(categories=MappingProxyType({k: tuple(v) for k, v in by_category.items()}))


def outputs_by_name(result) -> dict[str, str]:
    return {o.name: o.value for o in result.data}


def default_config() -> Config:
    return Config()


def test_emits_one_output_per_category_plus_reserved() -> None:
    result = build_prompts(category_map(), default_config())
    names = [o.name for o in result.data]
    assert names == [*CANONICAL_CATEGORIES, *RESERVED_OUTPUTS]
    assert len(result.data) == 19 + 2


def test_tags_joined_with_default_comma_separator() -> None:
    cm = category_map(hair=[rtag("blonde hair", "hair"), rtag("long hair", "hair")])
    result = build_prompts(cm, default_config())
    assert outputs_by_name(result)["hair"] == "blonde hair,long hair"


def test_order_is_preserved() -> None:
    cm = category_map(hair=[rtag("c", "hair"), rtag("a", "hair"), rtag("b", "hair")])
    result = build_prompts(cm, default_config())
    assert outputs_by_name(result)["hair"] == "c,a,b"


def test_empty_category_is_empty_string() -> None:
    result = build_prompts(category_map(), default_config())
    values = outputs_by_name(result)
    assert values["hair"] == ""
    assert all(isinstance(o.value, str) for o in result.data)


def test_reserved_outputs_present_and_empty() -> None:
    result = build_prompts(category_map(character=[rtag("1girl", "character")]), default_config())
    values = outputs_by_name(result)
    assert values["negative"] == ""
    assert values["scene"] == ""


def test_custom_separator() -> None:
    cm = category_map(hair=[rtag("a", "hair"), rtag("b", "hair")])
    config = Config.from_json({"prompt_builder": {"separator": " | "}})
    result = build_prompts(cm, config)
    assert outputs_by_name(result)["hair"] == "a | b"


def test_no_trailing_separator_or_whitespace() -> None:
    cm = category_map(hair=[rtag("only", "hair")])
    result = build_prompts(cm, default_config())
    value = outputs_by_name(result)["hair"]
    assert value == "only"
    assert not value.endswith(",")
    assert value == value.strip()


def test_no_escaping_tags_emitted_verbatim() -> None:
    cm = category_map(objects=[rtag("cat (animal)", "objects")])
    result = build_prompts(cm, default_config())
    assert outputs_by_name(result)["objects"] == "cat (animal)"


def test_output_is_deterministic() -> None:
    cm = category_map(hair=[rtag("a", "hair"), rtag("b", "hair")])
    a = [(o.name, o.value) for o in build_prompts(cm, default_config()).data]
    b = [(o.name, o.value) for o in build_prompts(cm, default_config()).data]
    assert a == b
