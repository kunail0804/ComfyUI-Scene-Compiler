"""Knowledge Base validation tooling (MASTER_SPEC §15.10, §26.4).

Validates a whole Knowledge Base — both per-entry structure and cross-entry
integrity — and returns every problem found (it does not stop at the first).
Each problem is a :class:`Message` carrying a code, the offending ``id`` in its
context, and a description.

This core is importable by the Knowledge Base loader (#7) and driven by the CLI
in ``scripts/validate_knowledge_base.py``.

Codes (Appendix B): duplicate canonical id → ``SC0005``; invalid category →
``SC0008``; circular expansion → ``SC0003``. The remaining Knowledge-Base
structural problems have no dedicated Appendix B code and are reported under the
umbrella ``SC0004`` (Knowledge Base Load Failure): duplicate alias, an alias
colliding with a canonical id (which would create a resolution chain), a missing
expansion target, and any per-entry schema nonconformance (including empty tags
and unknown fields).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from compiler.common.categories import is_valid_category
from compiler.common.result import Message, Severity
from schemas.validation import validate_document

_ENTRY_SCHEMA = "knowledge_base_entry"


def _sc0004(title: str, description: str, entry_id: str, **context: Any) -> Message:
    return Message(
        code="SC0004",
        severity=Severity.FATAL,
        title=title,
        description=description,
        context={"id": entry_id, **context},
    )


def _schema_messages(entry: Mapping[str, Any], entry_id: str) -> list[Message]:
    """Per-entry schema conformance, minus the category (checked explicitly)."""
    messages: list[Message] = []
    for issue in validate_document(entry, _ENTRY_SCHEMA):
        if issue.path == "category":
            continue  # reported as SC0008 by the explicit category check
        messages.append(
            _sc0004(
                title="Invalid Knowledge Base entry",
                description=f"Entry '{entry_id}' failed schema validation: {issue.message}",
                entry_id=entry_id,
                path=issue.path,
            )
        )
    return messages


def _category_messages(entry: Mapping[str, Any], entry_id: str) -> list[Message]:
    category = entry.get("category")
    if category is not None and not is_valid_category(category):
        return [
            Message(
                code="SC0008",
                severity=Severity.ERROR,
                title="Invalid Category",
                description=f"Entry '{entry_id}' references unknown category '{category}'.",
                context={"id": entry_id, "category": category},
            )
        ]
    return []


def _duplicate_id_messages(entries: Sequence[Mapping[str, Any]]) -> list[Message]:
    seen: set[str] = set()
    messages: list[Message] = []
    for entry in entries:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str):
            continue
        if entry_id in seen:
            messages.append(
                Message(
                    code="SC0005",
                    severity=Severity.ERROR,
                    title="Duplicate Canonical ID",
                    description=f"Canonical id '{entry_id}' is defined more than once.",
                    context={"id": entry_id},
                )
            )
        seen.add(entry_id)
    return messages


def _alias_messages(entries: Sequence[Mapping[str, Any]]) -> list[Message]:
    """Aliases must be globally unique and never collide with a canonical id."""
    ids = {e["id"] for e in entries if isinstance(e.get("id"), str)}
    messages: list[Message] = []
    seen_aliases: set[str] = set()
    for entry in entries:
        entry_id = entry.get("id", "<unknown>")
        for alias in entry.get("aliases", []):
            if alias in ids:
                messages.append(
                    _sc0004(
                        title="Alias collides with a canonical id",
                        description=(
                            f"Alias '{alias}' on entry '{entry_id}' equals a canonical id; "
                            "aliases must resolve directly (no chains)."
                        ),
                        entry_id=entry_id,
                        alias=alias,
                    )
                )
            if alias in seen_aliases:
                messages.append(
                    _sc0004(
                        title="Duplicate alias",
                        description=(
                            f"Alias '{alias}' (entry '{entry_id}') is defined more than once."
                        ),
                        entry_id=entry_id,
                        alias=alias,
                    )
                )
            seen_aliases.add(alias)
    return messages


def _expansion_messages(entries: Sequence[Mapping[str, Any]]) -> list[Message]:
    """Expansion targets must exist and must not form cycles."""
    ids = {e["id"] for e in entries if isinstance(e.get("id"), str)}
    graph = {
        e["id"]: [t for t in e.get("expand", [])] for e in entries if isinstance(e.get("id"), str)
    }
    messages: list[Message] = []

    # Missing targets.
    for entry in entries:
        entry_id = entry.get("id", "<unknown>")
        for target in entry.get("expand", []):
            if target not in ids:
                messages.append(
                    _sc0004(
                        title="Expansion target does not exist",
                        description=(
                            f"Entry '{entry_id}' expands to unknown canonical id '{target}'."
                        ),
                        entry_id=entry_id,
                        target=target,
                    )
                )

    # Cycles (only over targets that exist), reported once per distinct cycle.
    reported: set[frozenset[str]] = set()
    for cycle in _find_cycles(graph, ids):
        key = frozenset(cycle)
        if key in reported:
            continue
        reported.add(key)
        messages.append(
            Message(
                code="SC0003",
                severity=Severity.ERROR,
                title="Circular Expansion",
                description=f"Expansion cycle detected: {' -> '.join(cycle)}.",
                context={"id": cycle[0], "cycle": cycle},
            )
        )
    return messages


def _find_cycles(graph: Mapping[str, list[str]], ids: set[str]) -> list[list[str]]:
    """Return the ids of each expansion cycle, deterministically."""
    cycles: list[list[str]] = []
    on_stack: dict[str, int] = {}
    stack: list[str] = []
    visited: set[str] = set()

    def dfs(node: str) -> None:
        visited.add(node)
        on_stack[node] = len(stack)
        stack.append(node)
        for target in graph.get(node, []):
            if target not in ids:
                continue
            if target in on_stack:
                cycles.append(stack[on_stack[target] :])
            elif target not in visited:
                dfs(target)
        stack.pop()
        del on_stack[node]

    for node in graph:  # insertion order -> deterministic
        if node not in visited:
            dfs(node)
    return cycles


def validate_entry(entry: Mapping[str, Any]) -> list[Message]:
    """Validate a single entry's structure (schema + category), no cross-entry rules.

    Reuses the same schema/category checks as :func:`validate_knowledge_base` so
    per-entry tooling (e.g. the automatic candidate validator, #119) stays in sync
    with the authoritative rules instead of duplicating them.
    """
    entry_id = entry.get("id", "<unknown>")
    return _schema_messages(entry, entry_id) + _category_messages(entry, entry_id)


def validate_knowledge_base(entries: Iterable[Mapping[str, Any]]) -> list[Message]:
    """Validate a whole Knowledge Base and return every problem found.

    Args:
        entries: All Knowledge Base entries (parsed JSON), across every file.

    Returns:
        A deterministically-ordered list of :class:`Message`; empty when the
        Knowledge Base is valid.
    """
    entries = list(entries)
    messages: list[Message] = []

    for entry in entries:
        entry_id = entry.get("id", "<unknown>")
        messages.extend(_schema_messages(entry, entry_id))
        messages.extend(_category_messages(entry, entry_id))

    messages.extend(_duplicate_id_messages(entries))
    messages.extend(_alias_messages(entries))
    messages.extend(_expansion_messages(entries))
    return messages
