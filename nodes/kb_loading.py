"""Shared Knowledge Base loading for the Scene Compiler nodes.

Loads a Knowledge Base directory with a process-wide load-once cache keyed by
``(resolved_path, version)`` so the (large) Knowledge Base is read once and reused
across node executions (#130); bumping ``reload`` forces a fresh read. A relative
path is resolved against this package (where the shipped ``knowledge_base/`` lives),
not ComfyUI's working directory, so the default works regardless of where ComfyUI
is launched from.

The Configuration node uses this to emit the Knowledge Base for the Resolver; no
compiler logic lives here beyond delegating to the loader module, and it never
imports ComfyUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compiler.common.knowledge_base import (
    KnowledgeBaseError,
    KnowledgeBaseLoader,
)

from .adapters import format_messages

# Package root: the repository directory that ships knowledge_base/, prompts/, ...
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# Process-wide cache keyed by the resolved path and pinned version; the ``reload``
# counter forces a fresh load when bumped.
_LOADERS: dict[tuple[str, str], KnowledgeBaseLoader] = {}
_LAST_RELOAD: dict[tuple[str, str], int] = {}


def resolve_kb_path(path: str) -> Path:
    """Resolve a relative Knowledge Base path against the package root."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else _PACKAGE_ROOT / candidate


def load_cached_knowledge_base(
    path: str, version: str = "", reload: int = 0
) -> tuple[Any, str, str, str]:
    """Load (and cache) the Knowledge Base, returning ``(kb, warnings, errors, raw)``.

    ``kb`` is ``None`` on a load failure. The cache is reused across calls with the
    same ``(path, version)`` unless ``reload`` changes.
    """
    resolved = resolve_kb_path(path)
    requested_version = version or None
    key = (str(resolved), version)
    loader = _LOADERS.get(key)
    if loader is None:
        loader = KnowledgeBaseLoader(resolved, requested_version=requested_version)
        _LOADERS[key] = loader
        _LAST_RELOAD[key] = reload
    try:
        if reload != _LAST_RELOAD[key]:
            _LAST_RELOAD[key] = reload
            knowledge_base = loader.reload()
        else:
            knowledge_base = loader.get()
    except KnowledgeBaseError as error:
        errors = format_messages([error.message, *error.findings])
        return (None, "", errors, f"Failed to load Knowledge Base from: {resolved}")

    count = len(knowledge_base)
    warnings = ""
    if count == 0:
        warnings = (
            f"Knowledge Base at '{resolved}' is empty (0 entries); "
            "check the path. Every concept will be reported as unknown."
        )
    sample = ", ".join(sorted(knowledge_base.by_id)[:20])
    raw = f"Loaded {count} entries from {resolved}\nFirst entries: {sample}"
    return (knowledge_base, warnings, "", raw)
