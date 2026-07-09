"""ComfyUI node for the Category Splitter (MASTER_SPEC §20).

A thin interface: it adapts the Resolved Tags input to the Category Splitter
module and surfaces the CompilerResult's data, warnings, and errors. No compiler
logic; it never imports ComfyUI.

The node outputs the Category Map (per-category grouping, in order); the
per-category prompt strings are produced downstream by the Prompt Builder node
(§19).
"""

from __future__ import annotations

from typing import Any

from compiler.splitter.category_splitter import split_into_categories

from .adapters import format_messages, to_raw_json, upstream_failure_message


class CategorySplitterNode:
    """Groups Resolved Tags into a Category Map."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("CATEGORY_MAP", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("category_map", "warnings", "errors", "raw")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {"required": {"resolved_tags": ("RESOLVED_TAGS",)}}

    def run(self, resolved_tags: Any) -> tuple[Any, str, str, str]:
        if resolved_tags is None:
            return (None, "", upstream_failure_message("resolved tags"), "")
        result = split_into_categories(tuple(resolved_tags))
        return (
            result.data,
            format_messages(result.warnings),
            format_messages(result.errors),
            to_raw_json(result.data),
        )
