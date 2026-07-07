"""Typed data models for the compiler's inter-stage documents (MASTER_SPEC §9).

Every model is a frozen dataclass and therefore immutable once produced. Concept
arrays are stored as tuples and free-form mappings as read-only views, so a
produced model cannot be mutated in place. Each model exposes:

- ``from_json(data)`` — build a model from parsed JSON (the schema form of §10–§11);
- ``to_json()`` — serialize back to a JSON-compatible value.

The model round-trip (model -> JSON -> model) is lossless for every documented
field, and each ``to_json()`` output validates against the matching schema from
:mod:`schemas.validation`.

Metadata such as a Concept's ``confidence`` is carried inside ``metadata`` and
MUST NOT influence deterministic compilation (§9.3, §12.7).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

# An immutable empty mapping reused as the default for optional metadata fields.
_EMPTY_METADATA: Mapping[str, Any] = MappingProxyType({})


def _freeze_mapping(data: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return a read-only shallow copy of ``data`` (empty view when falsy)."""
    if not data:
        return _EMPTY_METADATA
    return MappingProxyType(dict(data))


@dataclass(frozen=True)
class Concept:
    """The smallest semantic unit (§9.3).

    Serialized as a bare string when only ``name`` is set, otherwise as an object.
    A bare string on load is equivalent to ``{"name": <string>}``.
    """

    name: str
    category: str | None = None
    source: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_METADATA)

    @classmethod
    def from_json(cls, data: str | Mapping[str, Any]) -> Concept:
        if isinstance(data, str):
            return cls(name=data)
        if isinstance(data, Mapping):
            return cls(
                name=data["name"],
                category=data.get("category"),
                source=data.get("source"),
                metadata=_freeze_mapping(data.get("metadata")),
            )
        raise TypeError(f"Concept must be a string or object, got {type(data).__name__}.")

    def to_json(self) -> str | dict[str, Any]:
        if self.category is None and self.source is None and not self.metadata:
            return self.name
        obj: dict[str, Any] = {"name": self.name}
        if self.category is not None:
            obj["category"] = self.category
        if self.source is not None:
            obj["source"] = self.source
        if self.metadata:
            obj["metadata"] = dict(self.metadata)
        return obj


# In Version 1 an Object is serialized as a Concept (§10.4 grammar, scene schema).
# The richer Object model of §9.5 (optional owner/attributes) is not required in V1.
SceneObject = Concept


def _concepts_from_json(items: list[Any] | None) -> tuple[Concept, ...]:
    return tuple(Concept.from_json(item) for item in (items or ()))


def _concepts_to_json(concepts: tuple[Concept, ...]) -> list[Any]:
    return [concept.to_json() for concept in concepts]


@dataclass(frozen=True)
class Character:
    """One independent subject; every field holds semantic concepts (§9.2)."""

    id: int
    identity: tuple[Concept, ...] = ()
    appearance: tuple[Concept, ...] = ()
    clothing: tuple[Concept, ...] = ()
    accessories: tuple[Concept, ...] = ()
    pose: tuple[Concept, ...] = ()
    expression: tuple[Concept, ...] = ()
    actions: tuple[Concept, ...] = ()

    _CONCEPT_FIELDS = (
        "identity",
        "appearance",
        "clothing",
        "accessories",
        "pose",
        "expression",
        "actions",
    )

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Character:
        return cls(
            id=data["id"],
            **{name: _concepts_from_json(data.get(name)) for name in cls._CONCEPT_FIELDS},
        )

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {"id": self.id}
        for name in self._CONCEPT_FIELDS:
            result[name] = _concepts_to_json(getattr(self, name))
        return result


@dataclass(frozen=True)
class Interaction:
    """A relationship between two or more characters (§9.4)."""

    participants: tuple[int, ...]
    concept: str

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Interaction:
        return cls(participants=tuple(data["participants"]), concept=data["concept"])

    def to_json(self) -> dict[str, Any]:
        return {"participants": list(self.participants), "concept": self.concept}


@dataclass(frozen=True)
class Metadata:
    """Compiler metadata; MUST NOT affect compilation (§9.7)."""

    schema_version: str
    compiler_version: str | None = None
    language: str | None = None
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Metadata:
        return cls(
            schema_version=data["schema_version"],
            compiler_version=data.get("compiler_version"),
            language=data.get("language"),
            warnings=tuple(data.get("warnings", ())),
        )

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {"schema_version": self.schema_version}
        if self.compiler_version is not None:
            result["compiler_version"] = self.compiler_version
        if self.language is not None:
            result["language"] = self.language
        if self.warnings:
            result["warnings"] = list(self.warnings)
        return result


@dataclass(frozen=True)
class ResolvedTag:
    """A generated Illustrious tag with full traceability (§9.8)."""

    tag: str
    category: str
    source_concept: str
    knowledge_base_entry: str

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> ResolvedTag:
        return cls(
            tag=data["tag"],
            category=data["category"],
            source_concept=data["source_concept"],
            knowledge_base_entry=data["knowledge_base_entry"],
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "category": self.category,
            "source_concept": self.source_concept,
            "knowledge_base_entry": self.knowledge_base_entry,
        }


@dataclass(frozen=True)
class CategoryMap:
    """Maps each category name to an ordered tuple of Resolved Tags (§9.9)."""

    categories: Mapping[str, tuple[ResolvedTag, ...]] = field(
        default_factory=lambda: _EMPTY_METADATA
    )

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> CategoryMap:
        categories = {
            name: tuple(ResolvedTag.from_json(tag) for tag in tags) for name, tags in data.items()
        }
        return cls(categories=MappingProxyType(categories))

    def tags_for(self, category: str) -> tuple[ResolvedTag, ...]:
        """Return the Resolved Tags for ``category`` (empty tuple if absent)."""
        return self.categories.get(category, ())

    def to_json(self) -> dict[str, Any]:
        return {name: [tag.to_json() for tag in tags] for name, tags in self.categories.items()}


@dataclass(frozen=True)
class PromptOutput:
    """One final workflow output; ``value`` is always a string (§9.10)."""

    name: str
    value: str

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> PromptOutput:
        return cls(name=data["name"], value=data["value"])

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True)
class Scene:
    """The Scene JSON root; all sections required, collections MAY be empty (§9.1)."""

    characters: tuple[Character, ...] = ()
    interactions: tuple[Interaction, ...] = ()
    objects: tuple[Concept, ...] = ()
    environment: tuple[Concept, ...] = ()
    camera: tuple[Concept, ...] = ()
    lighting: tuple[Concept, ...] = ()
    metadata: Metadata = field(default_factory=lambda: Metadata(schema_version="1.0"))

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Scene:
        return cls(
            characters=tuple(Character.from_json(c) for c in data.get("characters", ())),
            interactions=tuple(Interaction.from_json(i) for i in data.get("interactions", ())),
            objects=_concepts_from_json(data.get("objects")),
            environment=_concepts_from_json(data.get("environment")),
            camera=_concepts_from_json(data.get("camera")),
            lighting=_concepts_from_json(data.get("lighting")),
            metadata=Metadata.from_json(data["metadata"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "characters": [c.to_json() for c in self.characters],
            "interactions": [i.to_json() for i in self.interactions],
            "objects": _concepts_to_json(self.objects),
            "environment": _concepts_to_json(self.environment),
            "camera": _concepts_to_json(self.camera),
            "lighting": _concepts_to_json(self.lighting),
            "metadata": self.metadata.to_json(),
        }
