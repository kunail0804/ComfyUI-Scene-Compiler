"""The 19 canonical compiler categories (MASTER_SPEC §18.2, Appendix C.1).

Categories are defined by the compiler, not by the Knowledge Base (§15.5). This
module is their single source of truth: the Knowledge Base entry schema, the
Knowledge Base validation tooling, and the Category Splitter all draw the valid
category set from here so they cannot drift apart.

The §18.2 list is authoritative and uses Title-Case display names; we use the
lowercase identifier form here for machine use (Category Map keys and
``ResolvedTag.category``). The two forms correspond one-to-one, in order.
"""

from __future__ import annotations

# Ordered lowercase identifiers for the 19 categories of §18.2. Order is the
# authoritative spec order and is significant (e.g. category ordering downstream).
CANONICAL_CATEGORIES: tuple[str, ...] = (
    "character",
    "appearance",
    "hair",
    "face",
    "eyes",
    "expression",
    "body",
    "clothing",
    "accessories",
    "pose",
    "action",
    "interaction",
    "objects",
    "environment",
    "camera",
    "lighting",
    "style",
    "quality",
    "miscellaneous",
)

_CATEGORY_SET = frozenset(CANONICAL_CATEGORIES)


def is_valid_category(category: str) -> bool:
    """Return True when ``category`` is one of the 19 canonical categories."""
    return category in _CATEGORY_SET
