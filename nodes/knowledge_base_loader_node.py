"""ComfyUI node for the Knowledge Base Loader (MASTER_SPEC §20).

A thin interface: it loads a Knowledge Base directory via the loader module and
exposes it for the Resolver node. No compiler logic; it never imports ComfyUI.

A relative ``path`` is resolved against this package (where the shipped
``knowledge_base/`` lives), not ComfyUI's working directory, so the default works
regardless of where ComfyUI is launched from. Reloading is explicit: bumping the
``reload`` input re-executes the node (there is no automatic file watching).
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

# Process-wide Knowledge Base cache so the (large) KB loads once per (path, version)
# and is reused across node executions instead of being re-read on every run (#130).
# Keyed by the resolved path and pinned version; the ``reload`` widget forces a
# fresh load when bumped.
_LOADERS: dict[tuple[str, str], KnowledgeBaseLoader] = {}
_LAST_RELOAD: dict[tuple[str, str], int] = {}


def _resolve_path(path: str) -> Path:
    """Resolve a relative Knowledge Base path against the package root."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else _PACKAGE_ROOT / candidate


class KnowledgeBaseLoaderNode:
    """Loads the Knowledge Base and exposes it for the Resolver."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("KNOWLEDGE_BASE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("knowledge_base", "warnings", "errors", "raw")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {"path": ("STRING", {"default": "knowledge_base/"})},
            # New widgets are appended at the END so saved workflows keep their
            # positional widget values (ComfyUI stores widgets positionally).
            "optional": {
                "reload": ("INT", {"default": 0, "min": 0}),
                "version": ("STRING", {"default": ""}),
            },
        }

    def run(self, path: str, reload: int = 0, version: str = "") -> tuple[Any, str, str, str]:
        resolved = _resolve_path(path)
        requested_version = version or None
        key = (str(resolved), version)
        loader = _LOADERS.get(key)
        if loader is None:
            loader = KnowledgeBaseLoader(resolved, requested_version=requested_version)
            _LOADERS[key] = loader
            _LAST_RELOAD[key] = reload
        try:
            # Bumping the ``reload`` widget forces a fresh read; otherwise the cached
            # Knowledge Base is reused across runs.
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
