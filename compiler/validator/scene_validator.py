"""The Scene Validator (MASTER_SPEC §14).

Verifies and normalizes Scene JSON before resolution, guaranteeing that only
structurally valid, normalized Scene JSON reaches the Resolver.

- Hard errors (stop compilation): a missing required field (SC0009) or a wrong
  type / malformed structure (SC0002).
- Recoverable issues (warn and continue): an unexpected field is removed
  (SC0015), an empty/whitespace-only concept is removed after trimming (SC0016),
  and an interaction whose participants reference a non-existent character is
  dropped (SC0017).

The Validator never creates or guesses concepts, generates tags, or performs
Knowledge Base lookup. Validation order is stable: identical input yields
identical output.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from compiler.common.config import Config
from compiler.common.log import StructuredLogger
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult, Message
from schemas.models import Scene
from schemas.validation import validate_document

# The seven concept-bearing fields on a Character, plus the scene-level arrays.
_CHARACTER_CONCEPT_FIELDS = (
    "identity",
    "appearance",
    "clothing",
    "accessories",
    "pose",
    "expression",
    "actions",
)
_SCENE_CONCEPT_FIELDS = ("objects", "environment", "camera", "lighting")


def validate_scene(
    scene_json: dict[str, Any],
    config: Config,
    logger: StructuredLogger | None = None,
) -> CompilerResult:
    """Validate and normalize a Scene JSON document.

    Returns:
        A CompilerResult whose ``data`` is the validated :class:`Scene` on
        success, or ``None`` with error messages when a hard error stops the
        compilation.
    """
    errors, field_warnings = _classify_schema_issues(scene_json)
    if errors:
        result = CompilerResult()
        for error in errors:
            result = result.add_error(error)
        if logger is not None:
            logger.basic("scene_validation_failed", errors=len(errors))
        return result

    warnings: list[Message] = []
    if not config.validator.allow_unknown_fields:
        warnings.extend(field_warnings)

    cleaned, cleanup_warnings = _clean_scene(scene_json)
    warnings.extend(cleanup_warnings)

    scene = Scene.from_json(cleaned)
    result = CompilerResult(data=scene)
    for warning in warnings:
        result = result.add_warning(warning)
    if logger is not None:
        logger.basic("scene_validated", warnings=len(warnings))
    return result


def _classify_schema_issues(scene_json: Any) -> tuple[list[Message], list[Message]]:
    """Split strict schema issues into hard errors and unexpected-field warnings."""
    errors: list[Message] = []
    field_warnings: list[Message] = []
    for issue in validate_document(scene_json, "scene"):
        location = issue.path or "<root>"
        if issue.validator == "additionalProperties":
            field_warnings.append(
                message(
                    "SC0015",
                    f"Unexpected field at '{location}' was removed: {issue.message}",
                    path=issue.path,
                )
            )
        elif issue.validator == "required":
            errors.append(
                message(
                    "SC0009",
                    f"Missing required field at '{location}': {issue.message}",
                    path=issue.path,
                )
            )
        else:
            errors.append(
                message(
                    "SC0002",
                    f"Invalid Scene JSON at '{location}': {issue.message}",
                    path=issue.path,
                )
            )
    return errors, field_warnings


def _clean_scene(scene_json: dict[str, Any]) -> tuple[dict[str, Any], list[Message]]:
    """Trim/remove empty concepts and drop interactions with dangling participants."""
    warnings: list[Message] = []
    cleaned = dict(scene_json)

    character_ids: set[int] = set()
    cleaned_characters = []
    for character in scene_json.get("characters", []):
        character = dict(character)
        for field in _CHARACTER_CONCEPT_FIELDS:
            character[field] = _clean_concepts(
                character.get(field, []), f"characters/{character.get('id')}/{field}", warnings
            )
        cleaned_characters.append(character)
        if isinstance(character.get("id"), int):
            character_ids.add(character["id"])
    cleaned["characters"] = cleaned_characters

    for field in _SCENE_CONCEPT_FIELDS:
        cleaned[field] = _clean_concepts(scene_json.get(field, []), field, warnings)

    cleaned["interactions"] = _clean_interactions(
        scene_json.get("interactions", []), character_ids, warnings
    )
    return cleaned, warnings


def _clean_concepts(items: Sequence[Any], location: str, warnings: list[Message]) -> list[Any]:
    """Trim concept names and drop empty ones (SC0016), preserving order."""
    cleaned: list[Any] = []
    for item in items:
        if isinstance(item, str):
            trimmed = item.strip()
            if trimmed:
                cleaned.append(trimmed)
            else:
                warnings.append(
                    message("SC0016", f"Empty concept removed at '{location}'.", path=location)
                )
        elif isinstance(item, dict):
            entry = dict(item)
            name = entry.get("name", "")
            entry["name"] = name.strip() if isinstance(name, str) else name
            if entry["name"]:
                cleaned.append(entry)
            else:
                warnings.append(
                    message("SC0016", f"Empty concept removed at '{location}'.", path=location)
                )
        else:
            cleaned.append(item)
    return cleaned


def _clean_interactions(
    interactions: Sequence[Any], character_ids: set[int], warnings: list[Message]
) -> list[Any]:
    """Drop interactions whose participants reference a non-existent character (SC0017)."""
    cleaned: list[Any] = []
    for interaction in interactions:
        participants = interaction.get("participants", [])
        missing = [p for p in participants if p not in character_ids]
        if missing:
            warnings.append(
                message(
                    "SC0017",
                    (
                        f"Interaction '{interaction.get('concept')}' dropped: participant(s) "
                        f"{missing} reference no existing character."
                    ),
                    participants=participants,
                )
            )
        else:
            cleaned.append(interaction)
    return cleaned
