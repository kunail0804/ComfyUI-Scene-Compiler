"""Tests for the structured logger (issue #6, MASTER_SPEC §22, §25.7)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from compiler.common.config import Config
from compiler.common.log import DebugLevel, LogRecord, StructuredLogger

# --- DebugLevel ------------------------------------------------------------


def test_four_debug_levels_ordered() -> None:
    assert DebugLevel.NONE < DebugLevel.BASIC < DebugLevel.VERBOSE < DebugLevel.DEVELOPER


def test_debug_level_from_config_disabled_is_none() -> None:
    assert DebugLevel.from_config(enabled=False, level="basic") is DebugLevel.NONE


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        ("basic", DebugLevel.BASIC),
        ("verbose", DebugLevel.VERBOSE),
        ("developer", DebugLevel.DEVELOPER),
        ("none", DebugLevel.NONE),
    ],
)
def test_debug_level_from_config_enabled(level: str, expected: DebugLevel) -> None:
    assert DebugLevel.from_config(enabled=True, level=level) is expected


def test_unknown_level_raises() -> None:
    with pytest.raises(ValueError):
        DebugLevel.from_config(enabled=True, level="bogus")


# --- filtering -------------------------------------------------------------


def make_logger(level: DebugLevel) -> tuple[StructuredLogger, list[LogRecord]]:
    sink: list[LogRecord] = []
    return StructuredLogger(level=level, sink=sink.append), sink


def test_basic_logger_emits_basic_only() -> None:
    logger, sink = make_logger(DebugLevel.BASIC)
    assert logger.basic("stage_started", stage="resolver") is not None
    assert logger.verbose("detail") is None
    assert logger.developer("trace") is None
    assert [r.event for r in sink] == ["stage_started"]


def test_developer_logger_emits_all() -> None:
    logger, sink = make_logger(DebugLevel.DEVELOPER)
    logger.basic("a")
    logger.verbose("b")
    logger.developer("c")
    assert [r.event for r in sink] == ["a", "b", "c"]


def test_none_logger_emits_nothing() -> None:
    logger, sink = make_logger(DebugLevel.NONE)
    logger.basic("a")
    logger.verbose("b")
    logger.developer("c")
    assert sink == []


def test_verbose_logger_emits_basic_and_verbose() -> None:
    logger, sink = make_logger(DebugLevel.VERBOSE)
    logger.basic("a")
    logger.verbose("b")
    logger.developer("c")
    assert [r.event for r in sink] == ["a", "b"]


# --- structured records ----------------------------------------------------


def test_record_is_structured_not_a_string() -> None:
    logger, sink = make_logger(DebugLevel.BASIC)
    logger.basic("stage_started", stage="resolver", count=3)
    record = sink[0]
    assert record.event == "stage_started"
    assert record.fields == {"stage": "resolver", "count": 3}
    assert record.level is DebugLevel.BASIC


def test_record_to_json_machine_readable() -> None:
    record = LogRecord(level=DebugLevel.VERBOSE, event="e", fields={"k": "v"})
    assert record.to_json() == {"level": "verbose", "event": "e", "fields": {"k": "v"}}


def test_record_is_immutable() -> None:
    record = LogRecord(level=DebugLevel.BASIC, event="e", fields={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.event = "x"  # type: ignore[misc]


# --- config integration ----------------------------------------------------


def test_from_config_uses_debug_section() -> None:
    config = Config.from_json({"debug": {"enabled": True, "level": "verbose"}})
    logger, sink = make_logger(DebugLevel.NONE)
    logger = StructuredLogger.from_config(config, sink=sink.append)
    assert logger.level is DebugLevel.VERBOSE
    logger.verbose("ok")
    assert [r.event for r in sink] == ["ok"]


def test_default_logger_is_silent_and_needs_no_sink() -> None:
    # A logger without a sink must not raise when emitting.
    logger = StructuredLogger(level=DebugLevel.DEVELOPER)
    assert logger.basic("a") is not None  # returns record, emits nowhere


# --- no print() in the compiler --------------------------------------------


def test_no_print_in_compiler_package() -> None:
    compiler_dir = Path(__file__).resolve().parent.parent / "compiler"
    offenders = [
        py.relative_to(compiler_dir).as_posix()
        for py in compiler_dir.rglob("*.py")
        if "print(" in py.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"print() found in compiler package: {offenders}"
