"""The Category Splitter (MASTER_SPEC §18).

Organizes Resolved Tags into the 19 canonical categories, preserving order and
without modifying, generating, or removing any tag. Each tag is placed in the
category recorded on it by the Resolver (which is the category of its Knowledge
Base Entry).

Category ordering is deterministic (the shared canonical order); tags within a
category keep Resolver order; empty categories are omitted from the Category Map
(§18.4).
"""

from __future__ import annotations

from types import MappingProxyType

from compiler.common.categories import CANONICAL_CATEGORIES, is_valid_category
from compiler.common.log import StructuredLogger
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult
from schemas.models import CategoryMap, ResolvedTag


def split_into_categories(
    tags: tuple[ResolvedTag, ...],
    logger: StructuredLogger | None = None,
) -> CompilerResult:
    """Group Resolved Tags into a Category Map.

    Returns:
        A CompilerResult whose ``data`` is the :class:`CategoryMap` on success,
        or ``None`` with an SC0008 error if any tag carries a category outside
        the 19 canonical categories.
    """
    buckets: dict[str, list[ResolvedTag]] = {}
    for resolved in tags:
        if not is_valid_category(resolved.category):
            return CompilerResult().add_error(
                message(
                    "SC0008",
                    f"Tag '{resolved.tag}' has invalid category '{resolved.category}'.",
                    tag=resolved.tag,
                    category=resolved.category,
                )
            )
        buckets.setdefault(resolved.category, []).append(resolved)

    # Deterministic category order; empty categories omitted. Original ResolvedTag
    # objects are kept verbatim (tags are never modified).
    ordered = {
        category: tuple(buckets[category])
        for category in CANONICAL_CATEGORIES
        if category in buckets
    }
    category_map = CategoryMap(categories=MappingProxyType(ordered))
    if logger is not None:
        logger.basic("categories_split", categories=len(ordered), tags=len(tags))
    return CompilerResult(data=category_map)
