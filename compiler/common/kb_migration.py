"""Cross-version Knowledge Base entry migration (MASTER_SPEC §30.2, epic #36).

A pinned Knowledge Base may have been produced against an older entry-schema
version than the running code. To keep pinned datasets loadable as the format
evolves, entries are *adapted in memory at load time* — the on-disk (pinned)
files are never rewritten.

Compatibility policy
--------------------
- The current entry-schema version is :data:`CURRENT_ENTRY_SCHEMA_VERSION` (it
  matches ``schemas/json/knowledge_base_entry.schema.json``'s ``version``).
- A dataset declares its entry-schema version via the manifest's
  ``entry_schema_version`` field. A dataset with **no** manifest, or a manifest
  without that field, is assumed to already be at the current version — so the
  shipped reference Knowledge Base loads with no adaptation.
- Each supported older version has a forward adapter that upgrades a raw entry
  dict to the next version. Adapters are applied in sequence up to the current
  version, then the entry is validated and materialised as usual.
- Versions older than :data:`MIN_SUPPORTED_ENTRY_SCHEMA_VERSION` cannot be adapted
  and raise a clear error rather than loading a misinterpreted dataset.

Adapters must be pure and deterministic: the same pinned dataset always adapts to
the same in-memory entries.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

# Keep in sync with schemas/json/knowledge_base_entry.schema.json "version".
CURRENT_ENTRY_SCHEMA_VERSION = "1.1"
MIN_SUPPORTED_ENTRY_SCHEMA_VERSION = "1.0"


class UnsupportedKnowledgeBaseVersion(Exception):
    """Raised when a dataset's entry-schema version is too old to adapt."""


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _adapt_1_0_to_1_1(entry: dict[str, Any]) -> dict[str, Any]:
    """Entry schema 1.0 → 1.1.

    In 1.0 the explicit/general distinction was carried by a boolean ``nsfw``
    field; 1.1 replaced it with the ``rating`` enum (``general``/``explicit``).
    Translate the old field so a 1.0 dataset keeps its NSFW gating.
    """
    if "nsfw" in entry:
        entry.setdefault("rating", "explicit" if entry["nsfw"] else "general")
        del entry["nsfw"]
    return entry


# Forward adapters, keyed by the version they upgrade FROM. Each returns the
# entry at the next version. Extend this chain as the entry schema evolves.
_ADAPTERS: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "1.0": ("1.1", _adapt_1_0_to_1_1),
}


def adapt_entries(
    entries: list[Mapping[str, Any]], source_version: str | None
) -> list[dict[str, Any]]:
    """Adapt raw entry dicts from ``source_version`` to the current entry schema.

    Args:
        entries: The raw (parsed JSON) entries as loaded from disk.
        source_version: The dataset's entry-schema version, or ``None`` to assume
            the current version (no adaptation).

    Returns:
        New entry dicts at the current entry-schema version. Input dicts are not
        mutated.

    Raises:
        UnsupportedKnowledgeBaseVersion: If ``source_version`` is older than the
            minimum supported version, or references an unknown version with no
            adapter path to the current one.
    """
    version = source_version or CURRENT_ENTRY_SCHEMA_VERSION
    adapted = [dict(entry) for entry in entries]
    if version == CURRENT_ENTRY_SCHEMA_VERSION:
        return adapted

    if _version_tuple(version) < _version_tuple(MIN_SUPPORTED_ENTRY_SCHEMA_VERSION):
        raise UnsupportedKnowledgeBaseVersion(
            f"Knowledge Base entry-schema version '{version}' is older than the "
            f"minimum supported '{MIN_SUPPORTED_ENTRY_SCHEMA_VERSION}' and cannot be adapted."
        )

    # Walk the adapter chain forward to the current version.
    while version != CURRENT_ENTRY_SCHEMA_VERSION:
        step = _ADAPTERS.get(version)
        if step is None:
            raise UnsupportedKnowledgeBaseVersion(
                f"No migration path from Knowledge Base entry-schema version '{version}' "
                f"to '{CURRENT_ENTRY_SCHEMA_VERSION}'."
            )
        next_version, adapter = step
        adapted = [adapter(entry) for entry in adapted]
        version = next_version
    return adapted
