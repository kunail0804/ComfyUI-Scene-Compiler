"""Shared helpers for adapting compiler results to ComfyUI node outputs.

Nodes are thin interfaces; these helpers only format data for display and never
contain compiler logic.
"""

from __future__ import annotations

from collections.abc import Iterable

from compiler.common.result import Message


def format_messages(messages: Iterable[Message]) -> str:
    """Render diagnostic messages as one ``CODE: description`` line each.

    Returns an empty string when there are no messages.
    """
    return "\n".join(f"{message.code}: {message.description}" for message in messages)
