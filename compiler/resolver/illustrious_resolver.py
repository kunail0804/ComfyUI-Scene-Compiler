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

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

from compiler.common.categories import is_valid_category
from compiler.common.config import Config
from compiler.common.embedding_index import EmbeddingIndex
from compiler.common.knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseEntry,
    normalize_concept,
)
from compiler.common.log import StructuredLogger
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult, Message
from schemas.models import ResolvedTag, Scene

# Re-exported for callers/tests that import it from the resolver (its historical
# home); the implementation now lives with the Knowledge Base it keys.
__all__ = ["normalize_concept", "resolve_scene", "tags_to_prompt"]

_CHARACTER_CONCEPT_FIELDS = (
    "identity",
    "appearance",
    "clothing",
    "accessories",
    "pose",
    "expression",
    "actions",
)

# Scenes with at least this many concepts resolve their concepts on a thread pool
# (#133). Small scenes stay sequential to avoid pool overhead; the default is high
# enough that ordinary scenes are unaffected. Each concept resolves independently
# against the read-only index, so results merge back in exact discovery order.
_DEFAULT_PARALLEL_THRESHOLD = 64


def resolve_scene(
    scene: Scene,
    knowledge_base: KnowledgeBase,
    config: Config,
    logger: StructuredLogger | None = None,
    embedding_index: EmbeddingIndex | None = None,
    parallel_threshold: int = _DEFAULT_PARALLEL_THRESHOLD,
) -> CompilerResult:
    """Resolve a validated Scene into an ordered tuple of Resolved Tags.

    When ``config.semantic.enabled`` and an ``embedding_index`` is supplied, a
    concept that misses deterministic lookup **and** the head-noun reduction may
    fall back to its nearest Knowledge Base entry (epic #34). Deterministic lookup
    always wins; with the feature disabled (or no index) behaviour is unchanged.

    Large scenes (at least ``parallel_threshold`` concepts, when it is positive)
    resolve their independent concepts on a thread pool and merge the results back
    in exact discovery order, so the output is identical to sequential resolution
    regardless of thread scheduling (#133). Pass ``0`` to force sequential.

    Returns:
        A CompilerResult whose ``data`` is the tuple of :class:`ResolvedTag` on
        success, or ``None`` with error messages when an error condition
        (circular expansion SC0003, invalid category SC0008) stops resolution.
    """
    include_nsfw = config.resolver.include_nsfw
    index = knowledge_base.normalized_index(include_nsfw)
    resolver = _ConceptResolver(knowledge_base, index, config, logger, embedding_index)

    tags: list[ResolvedTag] = []
    warnings: list[Message] = []
    errors: list[Message] = []

    concepts = list(_iter_scene_concepts(scene))
    if 0 < parallel_threshold <= len(concepts):
        # Concept resolution is a pure read over the immutable index (no shared
        # mutable state), and ``map`` preserves input order, so parallelizing is
        # deterministic.
        with ThreadPoolExecutor() as executor:
            resolutions = list(executor.map(resolver.resolve, concepts))
    else:
        resolutions = [resolver.resolve(concept_name) for concept_name in concepts]

    for resolved in resolutions:
        tags.extend(resolved.tags)
        warnings.extend(resolved.warnings)
        errors.extend(resolved.errors)

    if errors:
        result = CompilerResult()
        for error in errors:
            result = result.add_error(error)
        return result

    if config.prompt_builder.remove_duplicate_tags:
        tags, dedup_warnings = _deduplicate(tags)
        warnings.extend(dedup_warnings)

    result = CompilerResult(data=tuple(tags))
    for warning in warnings:
        result = result.add_warning(warning)
    if logger is not None:
        logger.basic("scene_resolved", tags=len(tags), warnings=len(warnings))
    return result


def tags_to_prompt(tags: tuple[ResolvedTag, ...], separator: str = ",") -> str:
    """Join Resolved Tags into a single flat prompt string, in resolution order.

    This is the whole "translator": the Resolver turns a Scene into ordered tags,
    and this renders them as one prompt. There are no categories — tags appear in
    resolution (discovery) order, which naturally leads with character/appearance
    concepts. Deduplication already happened in :func:`resolve_scene`.
    """
    return separator.join(resolved.tag for resolved in tags)


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
        embedding_index: EmbeddingIndex | None = None,
    ) -> None:
        self._kb = knowledge_base
        self._index = index
        self._allow_aliases = config.resolver.allow_aliases
        self._expansion_enabled = config.resolver.expansion_enabled
        self._max_depth = config.resolver.max_expansion_depth
        self._include_nsfw = config.resolver.include_nsfw
        self._logger = logger
        self._min_similarity = config.semantic.min_similarity
        self._embedding_index = embedding_index if config.semantic.enabled else None

    def resolve(self, concept_name: str) -> _Resolution:
        outcome = _Resolution()
        key = normalize_concept(concept_name)
        entry = self._lookup(key)
        if entry is not None:
            self._expand(entry, concept_name, depth=0, path=(), outcome=outcome)
            return outcome

        tokens = key.split()
        entry, reduced_key, start = self._reduce(tokens)
        if entry is None:
            if self._semantic_fallback(concept_name, outcome):
                return outcome
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

        outcome.warnings.append(
            message(
                "SC0019",
                (
                    f"Concept '{concept_name}' was reduced to its head noun "
                    f"'{reduced_key}' for resolution; leading modifiers were retried "
                    "as standalone concepts."
                ),
                concept=concept_name,
                reduced_to=reduced_key,
            )
        )

        self._expand(entry, concept_name, depth=0, path=(), outcome=outcome)
        self._recover_modifiers(tokens, start, concept_name, outcome)
        return outcome

    def _semantic_fallback(self, concept_name: str, outcome: _Resolution) -> bool:
        """Resolve an otherwise-dropped concept via nearest-neighbour (epic #34, #116).

        Runs only when the feature is enabled and an index is present, i.e. after
        deterministic lookup and the head-noun reduction both miss — deterministic
        resolution always wins. Accepts the neighbour only when its similarity is at
        least ``min_similarity`` and it survives NSFW gating; the matched entry is a
        real Knowledge Base entry, so nothing is invented. Returns True when the
        concept was resolved (emitting ``SC0020``), False to keep the drop/warn path.
        """
        if self._embedding_index is None:
            return False
        match = self._embedding_index.nearest(concept_name)
        if match is None or match.score < self._min_similarity:
            return False
        entry = self._kb.get(match.entry_id)
        if entry is None:
            return False
        if entry.rating == "explicit" and not self._include_nsfw:
            return False  # gated NSFW neighbour: keep the drop/warn path
        outcome.warnings.append(
            message(
                "SC0020",
                (
                    f"Concept '{concept_name}' resolved via semantic fallback to "
                    f"'{entry.id}' (similarity {match.score:.3f})."
                ),
                concept=concept_name,
                entry=entry.id,
                score=match.score,
            )
        )
        self._expand(entry, concept_name, depth=0, path=(), outcome=outcome)
        return True

    def _reduce(self, tokens: list[str]) -> tuple[KnowledgeBaseEntry | None, str | None, int]:
        """Fall back to the concept's head noun when the full key has no entry (§17.2).

        English noun phrases carry modifiers on the left ("white summer dress"),
        so progressively dropping leading tokens and looking up the longest
        remaining suffix recovers the head-noun Knowledge Base Entry ("dress")
        instead of discarding the whole concept. The lookup stays exact and
        deterministic; no tag or concept is invented. Returns the index of the
        first surviving token so the dropped leading modifiers can be recovered.
        """
        for start in range(1, len(tokens)):
            reduced_key = " ".join(tokens[start:])
            entry = self._lookup(reduced_key)
            if entry is not None:
                return entry, reduced_key, start
        return None, None, 0

    def _recover_modifiers(
        self,
        tokens: list[str],
        start: int,
        source_concept: str,
        outcome: _Resolution,
    ) -> None:
        """Retry each leading modifier the head-noun reduction dropped (§30.2, #111).

        A dropped modifier is often part of a valid compound tag ("open" in
        "open white shirt" → "open shirt"), so each dropped token is retried
        *combined with the phrase's head noun* through the direct resolution path
        (normalize → alias → canonical → expansion). Recovered tags are emitted in
        discovery (left-to-right) order.

        Only the ``<modifier> <head-noun>`` compound is tried — never the bare
        modifier on its own. Bare single words ("white", "hologram") are almost
        always generic tags whose recovery would flood the prompt with noise and
        silently change existing output; the compound form is a high-precision,
        deterministic recovery. Reduction is not re-applied, so no head noun is
        re-derived and the result stays KB-only.
        """
        head = tokens[-1]
        for index in range(start):
            candidate = f"{tokens[index]} {head}"
            entry = self._lookup(candidate)
            if entry is not None:
                self._expand(entry, source_concept, depth=0, path=(), outcome=outcome)

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
