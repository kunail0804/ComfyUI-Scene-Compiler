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
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from compiler.common.kb_manifest import IMPLICIT_VERSION, MANIFEST_FILENAME, load_manifest
from compiler.common.kb_migration import UnsupportedKnowledgeBaseVersion, adapt_entries
from compiler.common.kb_validation import validate_knowledge_base
from compiler.common.log import StructuredLogger
from compiler.common.result import Message, Severity


def normalize_concept(name: str) -> str:
    """Normalize a concept for lookup (§17.3).

    Applies Unicode (NFKC) normalization and lowercasing, and unifies underscores
    with spaces before collapsing whitespace, so natural-language concepts
    ("holding hands"), snake_case ids ("holding_hands"), and spaced aliases all
    map to the same key.
    """
    text = unicodedata.normalize("NFKC", name).replace("_", " ").lower()
    return " ".join(text.split())


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
    rating: str = "general"
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
            rating=data.get("rating", "general"),
            deprecated=data.get("deprecated", False),
            notes=data.get("notes"),
        )


class KnowledgeBase:
    """An immutable, validated Knowledge Base with id and alias lookups."""

    def __init__(self, entries: list[KnowledgeBaseEntry], version: str = IMPLICIT_VERSION) -> None:
        by_id: dict[str, KnowledgeBaseEntry] = {}
        alias_to_id: dict[str, str] = {}
        for entry in entries:
            by_id[entry.id] = entry
            for alias in entry.aliases:
                alias_to_id[alias] = entry.id
        self._by_id: Mapping[str, KnowledgeBaseEntry] = MappingProxyType(by_id)
        self._alias_to_id: Mapping[str, str] = MappingProxyType(alias_to_id)
        self._version = version
        # Normalized id/alias -> entry lookup tables, compiled once per NSFW gating
        # and reused across resolutions (§30.2, #131). The Knowledge Base is
        # immutable, so the tables never go stale.
        self._normalized_index: dict[bool, Mapping[str, KnowledgeBaseEntry]] = {}

    @property
    def version(self) -> str:
        """The dataset version from the manifest (implicit ``v1`` when absent)."""
        return self._version

    def normalized_index(self, include_nsfw: bool) -> Mapping[str, KnowledgeBaseEntry]:
        """Return the compiled normalized-lookup table, building it once per gating.

        Maps every normalized canonical id and alias to its entry (aliases resolve
        directly). Explicit-rated entries are omitted unless ``include_nsfw`` is
        set, so a gated concept simply has no entry. The result is cached and reused
        across resolutions instead of being rebuilt on every ``resolve_scene``.
        """
        cached = self._normalized_index.get(include_nsfw)
        if cached is None:
            table: dict[str, KnowledgeBaseEntry] = {}
            for entry in self._by_id.values():
                if entry.rating == "explicit" and not include_nsfw:
                    continue
                table[normalize_concept(entry.id)] = entry
                for alias in entry.aliases:
                    table[normalize_concept(alias)] = entry
            cached = MappingProxyType(table)
            self._normalized_index[include_nsfw] = cached
        return cached

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
        if path.name == MANIFEST_FILENAME:
            continue  # the manifest is dataset metadata, not an entry array
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
    requested_version: str | None = None,
) -> KnowledgeBase:
    """Load and validate a Knowledge Base directory into an in-memory index.

    Args:
        directory: The Knowledge Base directory to load.
        logger: Optional structured logger.
        requested_version: If set, the dataset manifest ``version`` must match it
            exactly; otherwise a Fatal ``SC0004`` is raised (the requested version
            is unavailable at this path). ``None`` loads whatever is on the path.

    Raises:
        KnowledgeBaseError: If any file cannot be read, the Knowledge Base fails
            validation, or the requested version is unavailable. Nothing is loaded
            in that case.
    """
    directory = Path(directory)
    manifest = load_manifest(directory)
    if requested_version is not None and manifest.version != requested_version:
        raise KnowledgeBaseError(
            Message(
                code="SC0004",
                severity=Severity.FATAL,
                title="Knowledge Base Load Failure",
                description=(
                    f"Requested Knowledge Base version '{requested_version}' is not "
                    f"available at '{directory}' (found version '{manifest.version}')."
                ),
                context={
                    "id": str(directory),
                    "requested_version": requested_version,
                    "available_version": manifest.version,
                },
            ),
            findings=[],
        )
    raw_entries, problems = _read_entries(directory)
    try:
        raw_entries = adapt_entries(raw_entries, manifest.entry_schema_version)
    except UnsupportedKnowledgeBaseVersion as exc:
        raise KnowledgeBaseError(
            Message(
                code="SC0004",
                severity=Severity.FATAL,
                title="Knowledge Base Load Failure",
                description=str(exc),
                context={
                    "id": str(directory),
                    "entry_schema_version": manifest.entry_schema_version,
                },
            ),
            findings=[],
        ) from exc
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
    kb = KnowledgeBase(entries, version=manifest.version)
    if logger is not None:
        logger.basic(
            "knowledge_base_loaded",
            directory=str(directory),
            entries=len(kb),
            version=kb.version,
        )
    return kb


class KnowledgeBaseLoader:
    """Loads a Knowledge Base once and caches it; reload is explicit and safe."""

    def __init__(
        self,
        directory: str | Path,
        logger: StructuredLogger | None = None,
        requested_version: str | None = None,
    ) -> None:
        self._directory = Path(directory)
        self._logger = logger
        self._requested_version = requested_version
        self._cache: KnowledgeBase | None = None
        # Per-file lazy cache for category-scoped access (#132).
        self._file_cache: dict[str, list[dict]] = {}

    def get(self) -> KnowledgeBase:
        """Return the cached Knowledge Base, loading it on first use."""
        if self._cache is None:
            self._cache = load_knowledge_base(
                self._directory, self._logger, self._requested_version
            )
        return self._cache

    def reload(self) -> KnowledgeBase:
        """Reload the Knowledge Base from disk.

        On failure the previously cached Knowledge Base is left untouched (the
        load raises before the cache is replaced).
        """
        kb = load_knowledge_base(self._directory, self._logger, self._requested_version)
        self._cache = kb
        self._file_cache.clear()
        return kb

    @property
    def files_read(self) -> set[str]:
        """Names of the entry files parsed so far via :meth:`category_entries`."""
        return set(self._file_cache)

    def _read_file(self, path: Path) -> list[dict]:
        if path.name not in self._file_cache:
            self._file_cache[path.name] = json.loads(path.read_text(encoding="utf-8"))
        return self._file_cache[path.name]

    def category_entries(self, category: str) -> list[dict]:
        """Return the raw entries for one category, parsing only its file(s) (#132).

        Incremental/lazy: instead of eagerly parsing the whole Knowledge Base, this
        reads only ``<category>.json`` and ``gen_<category>.json`` (whichever exist)
        on first access and caches them. Full loading via :meth:`get` still sees the
        complete Knowledge Base. The curated file is listed first so curated entries
        win on any id collision, matching the additive-merge model.
        """
        entries: list[dict] = []
        for name in (f"{category}.json", f"gen_{category}.json"):
            path = self._directory / name
            if path.is_file():
                entries.extend(self._read_file(path))
        return entries
