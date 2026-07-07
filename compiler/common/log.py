"""Centralized structured logging for the compiler (MASTER_SPEC §22, §25.7).

Logs are structured :class:`LogRecord` objects — never free-form strings — so
they can be consumed programmatically without parsing. Emission is filtered by a
:class:`DebugLevel` threshold driven by configuration (``config.debug``), and the
compiler never calls ``print``.

Records carry no timestamp so that logging stays deterministic and testable. The
output destination is an injectable ``sink`` callable; the ComfyUI nodes (or a
test) supply one. :func:`json_lines_sink` provides a ready-made sink that writes
one JSON object per line to a stream.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import IntEnum
from types import MappingProxyType
from typing import IO, Any

_EMPTY_FIELDS: Mapping[str, Any] = MappingProxyType({})


class DebugLevel(IntEnum):
    """Debug verbosity levels (§22.1), ordered from least to most verbose."""

    NONE = 0
    BASIC = 1
    VERBOSE = 2
    DEVELOPER = 3

    @classmethod
    def from_config(cls, *, enabled: bool, level: str) -> DebugLevel:
        """Resolve the active level from a ``debug`` config section.

        When debugging is disabled the level is always :attr:`NONE`, regardless
        of the configured ``level``.

        Raises:
            ValueError: If ``level`` is not a known level name.
        """
        if not enabled:
            return cls.NONE
        try:
            return cls[level.upper()]
        except KeyError:
            raise ValueError(f"Unknown debug level '{level}'.") from None


@dataclass(frozen=True)
class LogRecord:
    """A single structured log record."""

    level: DebugLevel
    event: str
    fields: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_FIELDS)

    def __post_init__(self) -> None:
        if not isinstance(self.fields, MappingProxyType):
            frozen = MappingProxyType(dict(self.fields)) if self.fields else _EMPTY_FIELDS
            object.__setattr__(self, "fields", frozen)

    def to_json(self) -> dict[str, Any]:
        return {
            "level": self.level.name.lower(),
            "event": self.event,
            "fields": dict(self.fields),
        }


class StructuredLogger:
    """Emits structured log records filtered by a configured :class:`DebugLevel`.

    A record is emitted only when its level is not :attr:`DebugLevel.NONE` and is
    at or below the logger's threshold. Emission goes to the injected ``sink``;
    without a sink the logger is silent but still returns the (unemitted) record.
    """

    def __init__(
        self,
        level: DebugLevel = DebugLevel.NONE,
        sink: Callable[[LogRecord], None] | None = None,
    ) -> None:
        self.level = level
        self._sink = sink

    @classmethod
    def from_config(cls, config: Any, sink: Callable[[LogRecord], None] | None = None):
        """Build a logger from a Config's ``debug`` section."""
        level = DebugLevel.from_config(enabled=config.debug.enabled, level=config.debug.level)
        return cls(level=level, sink=sink)

    def log(self, level: DebugLevel, event: str, **fields: Any) -> LogRecord | None:
        """Emit a record at ``level``; return it, or None if filtered out."""
        if level == DebugLevel.NONE or level > self.level:
            return None
        record = LogRecord(level=level, event=event, fields=fields)
        if self._sink is not None:
            self._sink(record)
        return record

    def basic(self, event: str, **fields: Any) -> LogRecord | None:
        return self.log(DebugLevel.BASIC, event, **fields)

    def verbose(self, event: str, **fields: Any) -> LogRecord | None:
        return self.log(DebugLevel.VERBOSE, event, **fields)

    def developer(self, event: str, **fields: Any) -> LogRecord | None:
        return self.log(DebugLevel.DEVELOPER, event, **fields)


def json_lines_sink(stream: IO[str] | None = None) -> Callable[[LogRecord], None]:
    """Return a sink that writes each record as one JSON line to ``stream``.

    Defaults to ``sys.stderr``. Uses ``json.dumps`` (never ``print``).
    """
    target = stream if stream is not None else sys.stderr

    def _sink(record: LogRecord) -> None:
        target.write(json.dumps(record.to_json(), sort_keys=True) + "\n")

    return _sink
