"""Reusable JSON Schema validation helper (MASTER_SPEC §11).

Validates a document against one of the named inter-stage schemas and returns a
list of structured :class:`ValidationIssue` objects (an empty list means the
document is valid). Every JSON exchanged between compiler stages MUST validate
against its schema before continuing through the pipeline (§11.0).

Schemas live as JSON files in ``schemas/json/`` and reference one another by
``$id`` (e.g. Scene references Character references Concept); they are loaded
into a shared :mod:`referencing` registry so cross-schema ``$ref`` resolves.

Unknown fields are rejected by default (``additionalProperties: false``). Passing
``allow_unknown=True`` relaxes that check per configuration, satisfying the
"(per config) unknown fields" acceptance criterion without duplicating schemas.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_DIR = Path(__file__).parent / "json"


@dataclass(frozen=True)
class ValidationIssue:
    """A single schema violation.

    Attributes:
        path: JSON pointer (slash-separated) to the offending location; empty
            string for a violation at the document root.
        message: Human-readable explanation of what failed.
        validator: The JSON Schema keyword that produced the error
            (e.g. ``"required"``, ``"type"``, ``"additionalProperties"``).
    """

    path: str
    message: str
    validator: str


def _relax_unknown_fields(schema: Any) -> Any:
    """Return a deep copy of ``schema`` with ``additionalProperties: false`` removed.

    Only the strict boolean form is relaxed; a schema-valued
    ``additionalProperties`` (e.g. the Category Map value constraint) is
    preserved so value shapes stay enforced.
    """
    if isinstance(schema, dict):
        return {
            key: _relax_unknown_fields(value)
            for key, value in schema.items()
            if not (key == "additionalProperties" and value is False)
        }
    if isinstance(schema, list):
        return [_relax_unknown_fields(item) for item in schema]
    return schema


@functools.cache
def _load_schemas() -> dict[str, dict]:
    """Load every ``*.schema.json`` file, keyed by its ``$id``."""
    schemas: dict[str, dict] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id")
        if not schema_id:
            raise ValueError(f"Schema file {path.name} is missing a required '$id'.")
        if schema_id in schemas:
            raise ValueError(f"Duplicate schema '$id' '{schema_id}' in {path.name}.")
        schemas[schema_id] = schema
    return schemas


@functools.cache
def _registry(allow_unknown: bool) -> Registry:
    """Build a referencing registry of all schemas, optionally unknown-field-relaxed."""
    resources = []
    for schema_id, schema in _load_schemas().items():
        contents = _relax_unknown_fields(schema) if allow_unknown else schema
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        resources.append((schema_id, resource))
    return Registry().with_resources(resources)


def list_schemas() -> list[str]:
    """Return the sorted names ($id) of all registered schemas."""
    return sorted(_load_schemas())


def validate_document(
    document: Any,
    schema_name: str,
    *,
    allow_unknown: bool = False,
) -> list[ValidationIssue]:
    """Validate ``document`` against the named schema.

    Args:
        document: The parsed JSON value to validate.
        schema_name: The ``$id`` of the target schema (see :func:`list_schemas`).
        allow_unknown: When True, unknown object fields are permitted.

    Returns:
        A list of :class:`ValidationIssue` objects, ordered deterministically.
        An empty list means the document is valid.

    Raises:
        KeyError: If ``schema_name`` is not a registered schema.
    """
    if schema_name not in _load_schemas():
        raise KeyError(f"Unknown schema '{schema_name}'. Available schemas: {list_schemas()}.")

    registry = _registry(allow_unknown)
    schema = registry.contents(schema_name)
    validator = Draft202012Validator(schema, registry=registry)

    issues = [
        ValidationIssue(
            path="/".join(str(part) for part in error.absolute_path),
            message=error.message,
            validator=str(error.validator),
        )
        for error in validator.iter_errors(document)
    ]
    issues.sort(key=lambda issue: (issue.path, issue.validator, issue.message))
    return issues
