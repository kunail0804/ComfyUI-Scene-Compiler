"""Central registry of compiler message codes (MASTER_SPEC §21.2, Appendix B).

Every diagnostic :class:`Message` uses a stable code from here, giving one source
of truth for a code's canonical severity and title. Codes SC0001-SC0014 come from
Appendix B; SC0015+ are extensions added as the compiler is implemented and are
intended to be folded back into Appendix B and the wiki.

Use :func:`message` to build a message so the severity and title always match the
code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from compiler.common.result import Message, Severity


@dataclass(frozen=True)
class CodeSpec:
    """The canonical severity and title for a message code."""

    severity: Severity
    title: str


# Appendix B (SC0001-SC0014).
_APPENDIX_B: dict[str, CodeSpec] = {
    "SC0001": CodeSpec(Severity.WARNING, "Unknown Concept"),
    "SC0002": CodeSpec(Severity.ERROR, "Invalid Scene JSON"),
    "SC0003": CodeSpec(Severity.ERROR, "Circular Expansion"),
    "SC0004": CodeSpec(Severity.FATAL, "Knowledge Base Load Failure"),
    "SC0005": CodeSpec(Severity.ERROR, "Duplicate Canonical ID"),
    "SC0006": CodeSpec(Severity.WARNING, "Deprecated Concept"),
    "SC0007": CodeSpec(Severity.WARNING, "Duplicate Tag Removed"),
    "SC0008": CodeSpec(Severity.ERROR, "Invalid Category"),
    "SC0009": CodeSpec(Severity.ERROR, "Missing Required Field"),
    "SC0010": CodeSpec(Severity.ERROR, "Schema Version Mismatch"),
    "SC0011": CodeSpec(Severity.ERROR, "Analyzer Schema Validation Failure"),
    "SC0012": CodeSpec(Severity.FATAL, "Analyzer Unavailable"),
    "SC0013": CodeSpec(Severity.ERROR, "Analyzer Timeout"),
    "SC0014": CodeSpec(Severity.FATAL, "Invalid Configuration"),
}

# Extensions beyond Appendix B (to be documented in the spec/wiki).
_EXTENSIONS: dict[str, CodeSpec] = {
    "SC0015": CodeSpec(Severity.WARNING, "Unexpected Field Removed"),
    "SC0016": CodeSpec(Severity.WARNING, "Empty Concept Removed"),
    "SC0017": CodeSpec(Severity.WARNING, "Interaction Dropped"),
    "SC0018": CodeSpec(Severity.ERROR, "Analyzer Unexpected Response"),
    "SC0019": CodeSpec(Severity.WARNING, "Concept Reduced"),
    "SC0021": CodeSpec(Severity.WARNING, "List Under-Transcription"),
}

CODES: dict[str, CodeSpec] = {**_APPENDIX_B, **_EXTENSIONS}


def message(code: str, description: str, **context: Any) -> Message:
    """Build a :class:`Message` for a registered code.

    The severity and title are taken from the registry so they always match the
    code; only the description and optional context vary per call.

    Raises:
        KeyError: If ``code`` is not registered.
    """
    spec = CODES[code]
    return Message(
        code=code,
        severity=spec.severity,
        title=spec.title,
        description=description,
        context=context,
    )
