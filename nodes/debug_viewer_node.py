"""ComfyUI Debug Viewer node (MASTER_SPEC §20).

A read-only inspector that renders any connected intermediate state — Scene JSON,
Resolved Tags, Categories, Warnings, Errors — into a single report string. It
never alters the data passing through and contains no compiler logic.
"""

from __future__ import annotations

from typing import Any

from .adapters import render_debug_report


class DebugViewerNode:
    """Renders connected intermediate states for inspection (read-only)."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("report",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "optional": {
                "scene": ("SCENE",),
                "resolved_tags": ("RESOLVED_TAGS",),
                "category_map": ("CATEGORY_MAP",),
                "warnings": ("STRING", {"default": "", "forceInput": True}),
                "errors": ("STRING", {"default": "", "forceInput": True}),
            }
        }

    def run(
        self,
        scene: Any = None,
        resolved_tags: Any = None,
        category_map: Any = None,
        warnings: str = "",
        errors: str = "",
    ) -> tuple[str]:
        report = render_debug_report(
            scene=scene,
            resolved_tags=resolved_tags,
            category_map=category_map,
            warnings=warnings,
            errors=errors,
        )
        return (report,)
