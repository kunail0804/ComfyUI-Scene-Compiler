"""Knowledge Base duplicate & conflict detection (issue #120, epic #35).

As the Knowledge Base grows automatically, silent duplicates or conflicting
entries degrade resolution. This module scans a whole Knowledge Base and reports —
**detection only, it never edits** — four conflict classes:

- ``duplicate_ids``          — a canonical id defined by more than one entry.
- ``duplicate_aliases``      — an alias string claimed by more than one entry.
- ``tag_multiple_owners``    — a tag emitted by more than one entry with **no
  curated owner** to disambiguate it. The curated-wins additive-merge is respected:
  a tag shared between a curated entry and generated ones (or between two curated
  entries — an intentional cross-category synonym) is *not* a conflict, because the
  curated entry is authoritative.
- ``contradictory_expansions`` — a mutual expansion pair (``a`` expands to ``b`` and
  ``b`` expands to ``a``), which pulls each concept into the other.

The report is machine-readable (:meth:`ConflictReport.to_json`) with a human
summary count (:attr:`ConflictReport.total`), so it can drive a CI gate.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConflictReport:
    """The result of a Knowledge Base conflict scan."""

    duplicate_ids: list[dict[str, Any]] = field(default_factory=list)
    duplicate_aliases: list[dict[str, Any]] = field(default_factory=list)
    tag_multiple_owners: list[dict[str, Any]] = field(default_factory=list)
    contradictory_expansions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.duplicate_ids)
            + len(self.duplicate_aliases)
            + len(self.tag_multiple_owners)
            + len(self.contradictory_expansions)
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "duplicate_ids": self.duplicate_ids,
            "duplicate_aliases": self.duplicate_aliases,
            "tag_multiple_owners": self.tag_multiple_owners,
            "contradictory_expansions": self.contradictory_expansions,
        }


def detect_conflicts(
    entries: Iterable[Mapping[str, Any]],
    curated_ids: Collection[str] = (),
) -> ConflictReport:
    """Scan a Knowledge Base for duplicate/conflict classes.

    Args:
        entries: All Knowledge Base entries (parsed dicts) across every file.
        curated_ids: Ids owned by the hand-curated files; used so a tag with a
            curated owner is treated as authoritative (not a conflict).
    """
    entries = list(entries)
    curated = set(curated_ids)

    id_counts: dict[str, int] = defaultdict(int)
    alias_owners: dict[str, list[str]] = defaultdict(list)
    tag_owners: dict[str, list[str]] = defaultdict(list)
    expand: dict[str, set[str]] = {}

    for entry in entries:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str):
            continue
        id_counts[entry_id] += 1
        for alias in entry.get("aliases", ()):
            alias_owners[alias].append(entry_id)
        for tag in entry.get("tags", ()):
            tag_owners[tag].append(entry_id)
        expand[entry_id] = set(entry.get("expand", ()))

    duplicate_ids = [
        {"id": entry_id, "count": count}
        for entry_id, count in sorted(id_counts.items())
        if count > 1
    ]
    duplicate_aliases = [
        {"alias": alias, "owners": sorted(owners)}
        for alias, owners in sorted(alias_owners.items())
        if len(owners) > 1
    ]

    tag_multiple_owners = [
        {"tag": tag, "owners": sorted(owners)}
        for tag, owners in sorted(tag_owners.items())
        if len(owners) > 1 and not any(owner in curated for owner in owners)
    ]

    contradictory_expansions = [
        {"pair": [a, b]}
        for a in sorted(expand)
        for b in sorted(expand[a])
        if a < b and a in expand.get(b, set())
    ]

    return ConflictReport(
        duplicate_ids=duplicate_ids,
        duplicate_aliases=duplicate_aliases,
        tag_multiple_owners=tag_multiple_owners,
        contradictory_expansions=contradictory_expansions,
    )
