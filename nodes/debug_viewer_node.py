"""ComfyUI Debug Viewer node (MASTER_SPEC §20).

A read-only inspector that renders connected state — Scene JSON, Warnings,
Errors — into a single report string. (Resolved tags are inspectable directly via
the Resolver's ``json`` output.) It never alters the data passing through and
contains no compiler logic.
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
                "scene": (
                    "SCENE",
                    {"tooltip": "Any scene data to inspect (from the Analyzer or Validator)."},
                ),
                "warnings": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": "A stage's warnings output to view.",
                    },
                ),
                "errors": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": "A stage's errors output to view.",
                    },
                ),
            }
        }

    def run(
        self,
        scene: Any = None,
        warnings: str = "",
        errors: str = "",
    ) -> tuple[str]:
        report = render_debug_report(scene=scene, warnings=warnings, errors=errors)
        return (report,)
