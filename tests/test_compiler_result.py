"""Tests for the Compiler Result wrapper (issue #4, MASTER_SPEC §8.6, §21)."""

from __future__ import annotations

import dataclasses

import pytest

from compiler.common.result import CompilerResult, Message, Severity

# --- Severity --------------------------------------------------------------


def test_all_four_severity_levels_exist() -> None:
    assert {s.value for s in Severity} == {"information", "warning", "error", "fatal"}


# --- Message ---------------------------------------------------------------


def sample_message(code: str = "SC0001", severity: Severity = Severity.WARNING) -> Message:
    return Message(
        code=code,
        severity=severity,
        title="Unknown concept",
        description="Concept 'foo' is not in the Knowledge Base.",
    )


def test_message_construction() -> None:
    m = sample_message()
    assert m.code == "SC0001"
    assert m.severity is Severity.WARNING
    assert m.context == {}


def test_message_with_context() -> None:
    m = Message(
        code="SC0002",
        severity=Severity.ERROR,
        title="Missing field",
        description="Field 'metadata' is required.",
        context={"field": "metadata", "stage": "validator"},
    )
    assert m.context["field"] == "metadata"


def test_message_roundtrip_machine_readable() -> None:
    m = sample_message()
    data = m.to_json()
    assert data["severity"] == "warning"
    assert Message.from_json(data) == m


def test_message_context_roundtrip() -> None:
    m = Message(
        code="SC0002",
        severity=Severity.ERROR,
        title="t",
        description="d",
        context={"stage": "resolver"},
    )
    assert Message.from_json(m.to_json()) == m


def test_message_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_message().code = "X"  # type: ignore[misc]


def test_message_context_is_read_only() -> None:
    m = Message(
        code="SC0002",
        severity=Severity.ERROR,
        title="t",
        description="d",
        context={"stage": "resolver"},
    )
    with pytest.raises(TypeError):
        m.context["stage"] = "other"  # type: ignore[index]


# --- CompilerResult construction -------------------------------------------


def test_empty_result_defaults() -> None:
    r = CompilerResult()
    assert r.data is None
    assert r.warnings == ()
    assert r.errors == ()
    assert r.success is True
    assert r.has_warnings is False


def test_result_carries_data() -> None:
    r = CompilerResult(data={"scene": True})
    assert r.data == {"scene": True}


# --- add_warning / add_error (functional, immutable) -----------------------


def test_add_warning_returns_new_result() -> None:
    original = CompilerResult(data="x")
    warned = original.add_warning(sample_message())
    assert original.warnings == ()  # unchanged
    assert len(warned.warnings) == 1
    assert warned.data == "x"
    assert warned.success is True
    assert warned.has_warnings is True


def test_add_error_marks_failure() -> None:
    r = CompilerResult().add_error(sample_message("SC0100", Severity.ERROR))
    assert r.success is False
    assert len(r.errors) == 1


def test_fatal_is_stored_as_error_and_fails() -> None:
    r = CompilerResult().add_error(sample_message("SC0900", Severity.FATAL))
    assert r.success is False
    assert r.errors[0].severity is Severity.FATAL


# --- merge -----------------------------------------------------------------


def test_merge_concatenates_deterministically() -> None:
    a = (
        CompilerResult(data="a")
        .add_warning(sample_message("SC0001"))
        .add_error(sample_message("SC0101", Severity.ERROR))
    )
    b = (
        CompilerResult(data="b")
        .add_warning(sample_message("SC0002"))
        .add_error(sample_message("SC0102", Severity.ERROR))
    )
    merged = a.merge(b)
    assert [w.code for w in merged.warnings] == ["SC0001", "SC0002"]
    assert [e.code for e in merged.errors] == ["SC0101", "SC0102"]
    assert merged.success is False


def test_merge_takes_downstream_data() -> None:
    a = CompilerResult(data="a")
    b = CompilerResult(data="b")
    assert a.merge(b).data == "b"


def test_merge_combines_metadata() -> None:
    a = CompilerResult(metadata={"stage": "validator", "count": 1})
    b = CompilerResult(metadata={"stage": "resolver", "extra": 2})
    merged = a.merge(b)
    assert merged.metadata == {"stage": "resolver", "count": 1, "extra": 2}


def test_merge_does_not_mutate_operands() -> None:
    a = CompilerResult().add_warning(sample_message("SC0001"))
    b = CompilerResult().add_warning(sample_message("SC0002"))
    a.merge(b)
    assert [w.code for w in a.warnings] == ["SC0001"]
    assert [w.code for w in b.warnings] == ["SC0002"]


# --- serialization ---------------------------------------------------------


def test_result_to_json_is_machine_readable() -> None:
    r = CompilerResult(data="x").add_warning(sample_message())
    data = r.to_json()
    assert data["warnings"][0]["code"] == "SC0001"
    assert data["errors"] == []
    assert data["success"] is True


def test_result_to_json_serializes_model_data() -> None:
    class FakeModel:
        def to_json(self) -> dict:
            return {"kind": "scene"}

    r = CompilerResult(data=FakeModel())
    assert r.to_json()["data"] == {"kind": "scene"}
