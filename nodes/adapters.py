"""Shared helpers for adapting compiler results to ComfyUI node outputs.

Nodes are thin interfaces; these helpers only format data for display and never
contain compiler logic.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from compiler.common.result import Message


def format_messages(messages: Iterable[Message]) -> str:
    """Render diagnostic messages as one ``CODE: description`` line each.

    Returns an empty string when there are no messages.
    """
    return "\n".join(f"{message.code}: {message.description}" for message in messages)


def to_raw_json(data: Any) -> str:
    """Serialize a stage's data output to a pretty JSON string for inspection.

    Handles models (via their ``to_json``), tuples/lists of models, plain values,
    and ``None`` (returns an empty string). Used for the debug ``raw`` outputs.
    """
    if data is None:
        return ""
    try:
        if hasattr(data, "to_json"):
            payload: Any = data.to_json()
        elif isinstance(data, list | tuple):
            payload = [item.to_json() if hasattr(item, "to_json") else item for item in data]
        else:
            payload = data
        return json.dumps(payload, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return repr(data)


def upstream_failure_message(what: str) -> str:
    """A stage's error string when a required input is missing (upstream failed)."""
    return (
        f"No {what} received: the previous node produced no output. "
        "Check the errors output of the upstream node."
    )


def render_debug_report(
    *,
    scene: Any = None,
    resolved_tags: Any = None,
    category_map: Any = None,
    warnings: str = "",
    errors: str = "",
) -> str:
    """Render whichever intermediate states are provided into one report string.

    Read-only: inputs are serialized via their ``to_json`` methods and never
    modified. Absent (None/empty) inputs are skipped.
    """
    sections: list[str] = []
    if scene is not None:
        sections.append("== Scene JSON ==\n" + json.dumps(scene.to_json(), indent=2))
    if resolved_tags is not None:
        payload = [tag.to_json() for tag in resolved_tags]
        sections.append("== Resolved Tags ==\n" + json.dumps(payload, indent=2))
    if category_map is not None:
        sections.append("== Categories ==\n" + json.dumps(category_map.to_json(), indent=2))
    if warnings:
        sections.append("== Warnings ==\n" + warnings)
    if errors:
        sections.append("== Errors ==\n" + errors)
    return "\n\n".join(sections)
