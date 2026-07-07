"""The Compiler Result wrapper and diagnostic messages (MASTER_SPEC §8.6, §21).

Every compiler stage returns a :class:`CompilerResult` exposing the same four
fields — ``data``, ``warnings``, ``errors``, ``metadata`` — so results can be
merged uniformly as data flows down the pipeline.

Diagnostics are :class:`Message` objects with a stable machine-readable ``code``
and ``severity``; no field requires string parsing to interpret. Results are
immutable: :meth:`CompilerResult.add_warning`, :meth:`CompilerResult.add_error`,
and :meth:`CompilerResult.merge` all return new instances.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

_EMPTY_CONTEXT: Mapping[str, Any] = MappingProxyType({})


class Severity(StrEnum):
    """The four diagnostic severity levels (§21.1).

    - INFORMATION — compiler activity; never requires user action.
    - WARNING — a recoverable problem; compilation continues.
    - ERROR — invalid intermediate data; the affected compilation stops.
    - FATAL — the compiler cannot start or continue at all.
    """

    INFORMATION = "information"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass(frozen=True)
class Message:
    """A single diagnostic message (§21.3).

    ``context`` is an optional machine-readable mapping (e.g. the offending
    field or stage); it is stored read-only so a produced message is immutable.
    """

    code: str
    severity: Severity
    title: str
    description: str
    context: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_CONTEXT)

    def __post_init__(self) -> None:
        # Normalize context to a read-only view without breaking frozen semantics.
        if not isinstance(self.context, MappingProxyType):
            frozen = MappingProxyType(dict(self.context)) if self.context else _EMPTY_CONTEXT
            object.__setattr__(self, "context", frozen)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Message:
        return cls(
            code=data["code"],
            severity=Severity(data["severity"]),
            title=data["title"],
            description=data["description"],
            context=data.get("context") or _EMPTY_CONTEXT,
        )

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
        }
        if self.context:
            result["context"] = dict(self.context)
        return result


@dataclass(frozen=True)
class CompilerResult:
    """The uniform wrapper returned by every compiler stage (§8.6).

    Attributes:
        data: The stage's payload (a model, a dict, or None). Not interpreted here.
        warnings: Recoverable diagnostics; compilation continues.
        errors: Error/Fatal diagnostics; the affected compilation has stopped.
        metadata: Free-form machine-readable stage metadata (read-only).
    """

    data: Any = None
    warnings: tuple[Message, ...] = ()
    errors: tuple[Message, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_CONTEXT)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            frozen = MappingProxyType(dict(self.metadata)) if self.metadata else _EMPTY_CONTEXT
            object.__setattr__(self, "metadata", frozen)

    @property
    def success(self) -> bool:
        """True when no Error or Fatal diagnostics have been recorded."""
        return not self.errors

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def add_warning(self, message: Message) -> CompilerResult:
        """Return a new result with ``message`` appended to the warnings."""
        return CompilerResult(
            data=self.data,
            warnings=(*self.warnings, message),
            errors=self.errors,
            metadata=self.metadata,
        )

    def add_error(self, message: Message) -> CompilerResult:
        """Return a new result with ``message`` appended to the errors."""
        return CompilerResult(
            data=self.data,
            warnings=self.warnings,
            errors=(*self.errors, message),
            metadata=self.metadata,
        )

    def merge(self, other: CompilerResult) -> CompilerResult:
        """Combine two results as data flows from this stage to the next.

        Warnings and errors are concatenated deterministically (this result's
        first, then ``other``'s). The merged result carries ``other``'s data
        (the downstream stage's output) and the union of both metadata mappings
        (``other`` wins on key conflicts).
        """
        return CompilerResult(
            data=other.data,
            warnings=(*self.warnings, *other.warnings),
            errors=(*self.errors, *other.errors),
            metadata={**self.metadata, **other.metadata},
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize to a machine-readable dict (data serialized when possible)."""
        return {
            "success": self.success,
            "data": _serialize_data(self.data),
            "warnings": [w.to_json() for w in self.warnings],
            "errors": [e.to_json() for e in self.errors],
            "metadata": dict(self.metadata),
        }


def _serialize_data(data: Any) -> Any:
    """Serialize stage data: use ``to_json`` when available, else pass through."""
    to_json = getattr(data, "to_json", None)
    if callable(to_json):
        return to_json()
    return data
