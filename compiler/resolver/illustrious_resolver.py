"""The Illustrious Resolver (MASTER_SPEC §17).

Deterministically converts the semantic concepts of a validated Scene into
Illustrious Resolved Tags using the Knowledge Base. No language model is involved
and no concept or tag is ever invented.

Per-concept pipeline (§17.2): normalize -> alias resolution (direct only) ->
canonical lookup -> expansion -> tag generation. Concepts are processed in scene
discovery order (§17.8) and every generated tag keeps the category of its
Knowledge Base Entry.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator

from compiler.common.categories import is_valid_category
from compiler.common.config import Config
from compiler.common.knowledge_base import KnowledgeBase, KnowledgeBaseEntry
from compiler.common.log import StructuredLogger
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult, Message
from schemas.models import ResolvedTag, Scene

_CHARACTER_CONCEPT_FIELDS = (
    "identity",
    "appearance",
    "clothing",
    "accessories",
    "pose",
    "expression",
    "actions",
)


def normalize_concept(name: str) -> str:
    """Normalize a concept for lookup (§17.3).

    Applies Unicode (NFKC) normalization and lowercasing, and unifies underscores
    with spaces before collapsing whitespace, so natural-language concepts
    ("holding hands"), snake_case ids ("holding_hands"), and spaced aliases all
    map to the same key.
    """
    text = unicodedata.normalize("NFKC", name).replace("_", " ").lower()
    return " ".join(text.split())


def resolve_scene(
    scene: Scene,
    knowledge_base: KnowledgeBase,
    config: Config,
    logger: StructuredLogger | None = None,
) -> CompilerResult:
    """Resolve a validated Scene into an ordered tuple of Resolved Tags.

    Returns:
        A CompilerResult whose ``data`` is the tuple of :class:`ResolvedTag` on
        success, or ``None`` with error messages when an error condition
        (circular expansion SC0003, invalid category SC0008) stops resolution.
    """
    include_nsfw = config.resolver.include_nsfw
    index = _build_normalized_index(knowledge_base, include_nsfw)
    resolver = _ConceptResolver(knowledge_base, index, config, logger)

    tags: list[ResolvedTag] = []
    warnings: list[Message] = []
    errors: list[Message] = []

    for concept_name in _iter_scene_concepts(scene):
        resolved = resolver.resolve(concept_name)
        tags.extend(resolved.tags)
        warnings.extend(resolved.warnings)
        errors.extend(resolved.errors)

    if errors:
        result = CompilerResult()
        for error in errors:
            result = result.add_error(error)
        return result

    deduped, dedup_warnings = _deduplicate(tags)
    warnings.extend(dedup_warnings)

    result = CompilerResult(data=tuple(deduped))
    for warning in warnings:
        result = result.add_warning(warning)
    if logger is not None:
        logger.basic("scene_resolved", tags=len(deduped), warnings=len(warnings))
    return result


def tags_to_prompt(tags: tuple[ResolvedTag, ...], separator: str = ",") -> str:
    """Join Resolved Tags into a single flat prompt string, in resolution order.

    This is the whole "translator": the Resolver turns a Scene into ordered tags,
    and this renders them as one prompt. There are no categories — tags appear in
    resolution (discovery) order, which naturally leads with character/appearance
    concepts. Deduplication already happened in :func:`resolve_scene`.
    """
    return separator.join(resolved.tag for resolved in tags)


def _build_normalized_index(
    knowledge_base: KnowledgeBase,
    include_nsfw: bool,
) -> dict[str, KnowledgeBaseEntry]:
    """Map every normalized canonical id and alias to its entry (aliases direct).

    Explicit-rated entries are omitted unless ``include_nsfw`` is set, so a gated
    concept simply has no entry and is reported as unknown (SC0001).
    """
    index: dict[str, KnowledgeBaseEntry] = {}
    for entry in knowledge_base.by_id.values():
        if entry.rating == "explicit" and not include_nsfw:
            continue
        index[normalize_concept(entry.id)] = entry
        for alias in entry.aliases:
            index[normalize_concept(alias)] = entry
    return index


def _iter_scene_concepts(scene: Scene) -> Iterator[str]:
    """Yield concept names in scene discovery order (§17.8)."""
    for character in scene.characters:
        for field in _CHARACTER_CONCEPT_FIELDS:
            for concept in getattr(character, field):
                yield concept.name
    for interaction in scene.interactions:
        yield interaction.concept
    for field in ("objects", "environment", "camera", "lighting"):
        for concept in getattr(scene, field):
            yield concept.name


class _Resolution:
    """The outcome of resolving one concept."""

    __slots__ = ("tags", "warnings", "errors")

    def __init__(self) -> None:
        self.tags: list[ResolvedTag] = []
        self.warnings: list[Message] = []
        self.errors: list[Message] = []


class _ConceptResolver:
    """Resolves a single concept (with expansion) against a normalized index."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        index: dict[str, KnowledgeBaseEntry],
        config: Config,
        logger: StructuredLogger | None,
    ) -> None:
        self._kb = knowledge_base
        self._index = index
        self._allow_aliases = config.resolver.allow_aliases
        self._expansion_enabled = config.resolver.expansion_enabled
        self._max_depth = config.resolver.max_expansion_depth
        self._include_nsfw = config.resolver.include_nsfw
        self._logger = logger

    def resolve(self, concept_name: str) -> _Resolution:
        outcome = _Resolution()
        key = normalize_concept(concept_name)
        entry = self._lookup(key)
        if entry is None:
            entry, reduced_key = self._reduce(key)
        else:
            reduced_key = None

        if entry is None:
            outcome.warnings.append(
                message(
                    "SC0001",
                    f"Unknown concept '{concept_name}' has no Knowledge Base entry; ignored.",
                    concept=concept_name,
                )
            )
            if self._logger is not None:
                self._logger.verbose("concept_unknown", concept=concept_name, normalized=key)
            return outcome

        if reduced_key is not None:
            outcome.warnings.append(
                message(
                    "SC0019",
                    (
                        f"Concept '{concept_name}' was reduced to its head noun "
                        f"'{reduced_key}' for resolution; leading modifiers were dropped."
                    ),
                    concept=concept_name,
                    reduced_to=reduced_key,
                )
            )

        self._expand(entry, concept_name, depth=0, path=(), outcome=outcome)
        return outcome

    def _reduce(self, key: str) -> tuple[KnowledgeBaseEntry | None, str | None]:
        """Fall back to the concept's head noun when the full key has no entry (§17.2).

        English noun phrases carry modifiers on the left ("white summer dress"),
        so progressively dropping leading tokens and looking up the longest
        remaining suffix recovers the head-noun Knowledge Base Entry ("dress")
        instead of discarding the whole concept. The lookup stays exact and
        deterministic; no tag or concept is invented.
        """
        tokens = key.split()
        for start in range(1, len(tokens)):
            reduced_key = " ".join(tokens[start:])
            entry = self._lookup(reduced_key)
            if entry is not None:
                return entry, reduced_key
        return None, None

    def _lookup(self, key: str) -> KnowledgeBaseEntry | None:
        entry = self._index.get(key)
        if entry is None:
            return None
        # A key that matches an alias but not the entry's own id is an alias hit.
        if not self._allow_aliases and key != normalize_concept(entry.id):
            return None
        return entry

    def _expand(
        self,
        entry: KnowledgeBaseEntry,
        source_concept: str,
        depth: int,
        path: tuple[str, ...],
        outcome: _Resolution,
    ) -> None:
        if entry.id in path:
            outcome.errors.append(
                message(
                    "SC0003",
                    f"Circular expansion detected at '{entry.id}' (path: {' -> '.join(path)}).",
                    entry=entry.id,
                )
            )
            return
        if not is_valid_category(entry.category):
            outcome.errors.append(
                message(
                    "SC0008",
                    f"Entry '{entry.id}' has invalid category '{entry.category}'.",
                    entry=entry.id,
                )
            )
            return
        if entry.deprecated:
            outcome.warnings.append(
                message(
                    "SC0006",
                    f"Concept '{entry.id}' is deprecated; migration is encouraged.",
                    entry=entry.id,
                )
            )

        for tag in entry.tags:
            outcome.tags.append(
                ResolvedTag(
                    tag=tag,
                    category=entry.category,
                    source_concept=source_concept,
                    knowledge_base_entry=entry.id,
                )
            )
        if self._logger is not None:
            self._logger.verbose(
                "concept_resolved",
                concept=source_concept,
                canonical=entry.id,
                tags=list(entry.tags),
            )

        if not self._expansion_enabled or depth >= self._max_depth:
            return
        for target_id in entry.expand:
            target = self._kb.get(target_id)
            if target is None:
                continue
            if target.rating == "explicit" and not self._include_nsfw:
                continue  # gated NSFW expansion target
            self._expand(target, source_concept, depth + 1, (*path, entry.id), outcome)


def _deduplicate(tags: list[ResolvedTag]) -> tuple[list[ResolvedTag], list[Message]]:
    """Remove duplicate tags after expansion, keeping the first occurrence (§17.7)."""
    seen: set[str] = set()
    kept: list[ResolvedTag] = []
    warnings: list[Message] = []
    for resolved in tags:
        if resolved.tag in seen:
            warnings.append(
                message(
                    "SC0007",
                    f"Duplicate tag '{resolved.tag}' removed after expansion.",
                    tag=resolved.tag,
                )
            )
            continue
        seen.add(resolved.tag)
        kept.append(resolved)
    return kept, warnings
