"""Knowledge Base loading and indexing (MASTER_SPEC §15.11, §27.3).

The compiler loads the complete Knowledge Base once during initialization and
reuses it across compilations. Loading is all-or-nothing: the whole Knowledge
Base is validated (delegated to :func:`compiler.common.kb_validation`) before any
index is built, so a failed load leaves no partial state and raises a Fatal
``SC0004`` :class:`KnowledgeBaseError`.

:class:`KnowledgeBaseLoader` caches the loaded Knowledge Base and exposes an
explicit :meth:`~KnowledgeBaseLoader.reload`; there is no automatic file
watching, and a failed reload is side-effect-free (the previous Knowledge Base is
kept).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from compiler.common.kb_validation import validate_knowledge_base
from compiler.common.log import StructuredLogger
from compiler.common.result import Message, Severity


class KnowledgeBaseError(Exception):
    """Raised when the Knowledge Base cannot be loaded or fails validation (SC0004)."""

    def __init__(self, message: Message, findings: list[Message]) -> None:
        super().__init__(message.description)
        self.message = message
        self.findings = findings


@dataclass(frozen=True)
class KnowledgeBaseEntry:
    """One canonical Knowledge Base concept (§15.4), immutable once produced."""

    id: str
    tags: tuple[str, ...]
    category: str
    aliases: tuple[str, ...] = ()
    expand: tuple[str, ...] = ()
    deprecated: bool = False
    notes: str | None = None

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> KnowledgeBaseEntry:
        return cls(
            id=data["id"],
            tags=tuple(data["tags"]),
            category=data["category"],
            aliases=tuple(data.get("aliases", ())),
            expand=tuple(data.get("expand", ())),
            deprecated=data.get("deprecated", False),
            notes=data.get("notes"),
        )


class KnowledgeBase:
    """An immutable, validated Knowledge Base with id and alias lookups."""

    def __init__(self, entries: list[KnowledgeBaseEntry]) -> None:
        by_id: dict[str, KnowledgeBaseEntry] = {}
        alias_to_id: dict[str, str] = {}
        for entry in entries:
            by_id[entry.id] = entry
            for alias in entry.aliases:
                alias_to_id[alias] = entry.id
        self._by_id: Mapping[str, KnowledgeBaseEntry] = MappingProxyType(by_id)
        self._alias_to_id: Mapping[str, str] = MappingProxyType(alias_to_id)

    @property
    def by_id(self) -> Mapping[str, KnowledgeBaseEntry]:
        return self._by_id

    def get(self, canonical_id: str) -> KnowledgeBaseEntry | None:
        """Return the entry for a canonical id, or None."""
        return self._by_id.get(canonical_id)

    def resolve_alias(self, alias: str) -> str | None:
        """Return the canonical id an alias resolves to, or None."""
        return self._alias_to_id.get(alias)

    def lookup(self, name: str) -> KnowledgeBaseEntry | None:
        """Return the entry named by a canonical id or an alias, or None."""
        entry = self._by_id.get(name)
        if entry is not None:
            return entry
        canonical = self._alias_to_id.get(name)
        return self._by_id.get(canonical) if canonical is not None else None

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, name: str) -> bool:
        return name in self._by_id or name in self._alias_to_id


def _read_entries(directory: Path) -> tuple[list[dict], list[Message]]:
    """Read all *.json files (arrays of entries); collect load-time SC0004 problems."""
    entries: list[dict] = []
    problems: list[Message] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(_load_problem(f"{path.name}: invalid JSON: {exc}", path.name))
            continue
        if isinstance(data, list):
            entries.extend(data)
        else:
            problems.append(
                _load_problem(f"{path.name}: expected a JSON array of entries.", path.name)
            )
    return entries, problems


def _load_problem(description: str, source: str) -> Message:
    return Message(
        code="SC0004",
        severity=Severity.FATAL,
        title="Knowledge Base Load Failure",
        description=description,
        context={"id": source},
    )


def load_knowledge_base(
    directory: str | Path,
    logger: StructuredLogger | None = None,
) -> KnowledgeBase:
    """Load and validate a Knowledge Base directory into an in-memory index.

    Raises:
        KnowledgeBaseError: If any file cannot be read or the Knowledge Base
            fails validation. Nothing is loaded in that case.
    """
    directory = Path(directory)
    raw_entries, problems = _read_entries(directory)
    findings = problems + validate_knowledge_base(raw_entries)
    if findings:
        raise KnowledgeBaseError(
            Message(
                code="SC0004",
                severity=Severity.FATAL,
                title="Knowledge Base Load Failure",
                description=(
                    f"Knowledge Base at '{directory}' failed validation "
                    f"({len(findings)} problem(s)); nothing was loaded."
                ),
                context={"id": str(directory), "problem_count": len(findings)},
            ),
            findings=findings,
        )

    entries = [KnowledgeBaseEntry.from_json(entry) for entry in raw_entries]
    kb = KnowledgeBase(entries)
    if logger is not None:
        logger.basic("knowledge_base_loaded", directory=str(directory), entries=len(kb))
    return kb


class KnowledgeBaseLoader:
    """Loads a Knowledge Base once and caches it; reload is explicit and safe."""

    def __init__(self, directory: str | Path, logger: StructuredLogger | None = None) -> None:
        self._directory = Path(directory)
        self._logger = logger
        self._cache: KnowledgeBase | None = None

    def get(self) -> KnowledgeBase:
        """Return the cached Knowledge Base, loading it on first use."""
        if self._cache is None:
            self._cache = load_knowledge_base(self._directory, self._logger)
        return self._cache

    def reload(self) -> KnowledgeBase:
        """Reload the Knowledge Base from disk.

        On failure the previously cached Knowledge Base is left untouched (the
        load raises before the cache is replaced).
        """
        kb = load_knowledge_base(self._directory, self._logger)
        self._cache = kb
        return kb
