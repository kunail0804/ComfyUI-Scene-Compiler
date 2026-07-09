"""ComfyUI node for the Knowledge Base Loader (MASTER_SPEC §20).

A thin interface: it loads a Knowledge Base directory via the loader module and
exposes it for the Resolver node. No compiler logic; it never imports ComfyUI.

Reloading is explicit: bumping the ``reload`` input changes the node's inputs so
ComfyUI re-executes it (there is no automatic file watching).
"""

from __future__ import annotations

from typing import Any

from compiler.common.knowledge_base import KnowledgeBaseError, load_knowledge_base

from .adapters import format_messages


class KnowledgeBaseLoaderNode:
    """Loads the Knowledge Base and exposes it for the Resolver."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("KNOWLEDGE_BASE", "STRING", "STRING")
    RETURN_NAMES = ("knowledge_base", "warnings", "errors")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {"path": ("STRING", {"default": "knowledge_base/"})},
            "optional": {"reload": ("INT", {"default": 0, "min": 0})},
        }

    def run(self, path: str, reload: int = 0) -> tuple[Any, str, str]:
        try:
            knowledge_base = load_knowledge_base(path)
        except KnowledgeBaseError as error:
            return (None, "", format_messages([error.message, *error.findings]))
        return (knowledge_base, "", "")
