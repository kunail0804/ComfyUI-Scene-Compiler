"""ComfyUI node for the Illustrious Resolver (MASTER_SPEC §20).

A thin interface: it adapts the Scene and Knowledge Base inputs to the Resolver
module and surfaces the CompilerResult's data, warnings, and errors. No compiler
logic; it never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config
from compiler.resolver.illustrious_resolver import resolve_scene

from .adapters import format_messages, upstream_failure_message


class ResolverNode:
    """Resolves a Scene into Resolved Tags using the loaded Knowledge Base."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("RESOLVED_TAGS", "STRING", "STRING")
    RETURN_NAMES = ("resolved_tags", "warnings", "errors")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "scene": ("SCENE",),
                "knowledge_base": ("KNOWLEDGE_BASE",),
            },
            "optional": {"config": ("COMPILER_CONFIG",)},
        }

    def run(
        self,
        scene: Any,
        knowledge_base: Any,
        config: Config | None = None,
    ) -> tuple[Any, str, str]:
        if scene is None or knowledge_base is None:
            return (None, "", upstream_failure_message("scene or knowledge base"))
        result = resolve_scene(scene, knowledge_base, config or Config())
        return (result.data, format_messages(result.warnings), format_messages(result.errors))
