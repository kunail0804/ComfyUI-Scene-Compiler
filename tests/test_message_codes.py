"""Tests for the message-code registry (issue #11)."""

from __future__ import annotations

import pytest

from compiler.common.message_codes import CODES, message
from compiler.common.result import Severity


def test_appendix_b_and_extensions_registered() -> None:
    assert "SC0001" in CODES
    assert "SC0014" in CODES
    assert {"SC0015", "SC0016", "SC0017"}.issubset(CODES)


def test_message_uses_registry_severity_and_title() -> None:
    m = message("SC0009", "missing")
    assert m.severity is Severity.ERROR
    assert m.title == "Missing Required Field"
    assert m.code == "SC0009"


def test_message_carries_context() -> None:
    m = message("SC0015", "removed", path="characters/0")
    assert m.context["path"] == "characters/0"


def test_unknown_code_raises() -> None:
    with pytest.raises(KeyError):
        message("SC9999", "nope")
