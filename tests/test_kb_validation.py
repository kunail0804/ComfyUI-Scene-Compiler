"""Tests for the Knowledge Base validation tooling (issue #9, §15.10, §26.4)."""

from __future__ import annotations

from compiler.common.kb_validation import validate_knowledge_base
from compiler.common.result import Severity


def entry(id_: str, **overrides) -> dict:
    base = {"id": id_, "tags": [id_.replace("_", " ")], "category": "hair"}
    base.update(overrides)
    return base


def codes(messages) -> list[str]:
    return [m.code for m in messages]


# --- passing ---------------------------------------------------------------


def test_valid_knowledge_base_passes_cleanly() -> None:
    entries = [
        entry("long_hair", aliases=["lengthy hair"]),
        entry("twin_braids", aliases=["double braids"], expand=["long_hair"]),
    ]
    assert validate_knowledge_base(entries) == []


def test_empty_knowledge_base_passes() -> None:
    assert validate_knowledge_base([]) == []


# --- duplicate canonical id (SC0005) ---------------------------------------


def test_duplicate_id_reports_sc0005() -> None:
    messages = validate_knowledge_base([entry("long_hair"), entry("long_hair")])
    assert "SC0005" in codes(messages)
    dup = next(m for m in messages if m.code == "SC0005")
    assert dup.context["id"] == "long_hair"


# --- invalid category (SC0008) ---------------------------------------------


def test_invalid_category_reports_sc0008() -> None:
    messages = validate_knowledge_base([entry("x", category="hairstyle")])
    assert "SC0008" in codes(messages)


def test_valid_category_accepted() -> None:
    assert validate_knowledge_base([entry("x", category="eyes")]) == []


# --- circular expansion (SC0003) -------------------------------------------


def test_circular_expansion_reports_sc0003() -> None:
    entries = [entry("a", expand=["b"]), entry("b", expand=["a"])]
    messages = validate_knowledge_base(entries)
    assert "SC0003" in codes(messages)


def test_self_expansion_is_circular() -> None:
    messages = validate_knowledge_base([entry("a", expand=["a"])])
    assert "SC0003" in codes(messages)


# --- other KB-structural failures (SC0004) ---------------------------------


def test_duplicate_alias_reports_sc0004() -> None:
    entries = [entry("a", aliases=["shared"]), entry("b", aliases=["shared"])]
    assert "SC0004" in codes(validate_knowledge_base(entries))


def test_alias_colliding_with_id_reports_sc0004() -> None:
    # "long_hair" is a canonical id; using it as an alias would create a chain.
    entries = [entry("long_hair"), entry("b", aliases=["long_hair"])]
    assert "SC0004" in codes(validate_knowledge_base(entries))


def test_missing_expansion_target_reports_sc0004() -> None:
    messages = validate_knowledge_base([entry("a", expand=["does_not_exist"])])
    assert "SC0004" in codes(messages)


def test_empty_tags_reported() -> None:
    messages = validate_knowledge_base([entry("a", tags=[])])
    assert messages != []


def test_unknown_field_reported() -> None:
    messages = validate_knowledge_base([entry("a", colour="brown")])
    assert messages != []


# --- reporting behaviour ---------------------------------------------------


def test_reports_all_problems_not_just_first() -> None:
    entries = [
        entry("dup"),
        entry("dup"),  # duplicate id (SC0005)
        entry("bad", category="nope"),  # invalid category (SC0008)
    ]
    found = set(codes(validate_knowledge_base(entries)))
    assert {"SC0005", "SC0008"}.issubset(found)


def test_every_message_has_code_id_and_description() -> None:
    messages = validate_knowledge_base([entry("a", category="nope", expand=["missing"])])
    assert messages
    for m in messages:
        assert m.code
        assert m.description
        assert "id" in m.context


def test_findings_are_deterministic() -> None:
    entries = [entry("dup"), entry("dup"), entry("bad", category="nope")]
    assert codes(validate_knowledge_base(entries)) == codes(validate_knowledge_base(entries))


def test_findings_carry_error_or_fatal_severity() -> None:
    messages = validate_knowledge_base([entry("x", category="nope")])
    assert all(m.severity in (Severity.ERROR, Severity.FATAL) for m in messages)
