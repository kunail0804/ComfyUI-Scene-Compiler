"""ComfyUI node for the Illustrious Resolver (MASTER_SPEC §20).

A thin interface: it resolves the Scene against the Knowledge Base and translates
the resolved tags directly into a flat prompt string. No categories and no
separate Prompt Builder stage — the Resolver is the translator from Scene JSON to
prompt. It also surfaces warnings, errors, and the resolved-tags JSON so a
translation problem is inspectable. No compiler logic; it never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config
from compiler.common.embedding_index import load_default_index
from compiler.resolver.illustrious_resolver import resolve_scene, tags_to_prompt

from .adapters import format_messages, to_raw_json, upstream_failure_message


class ResolverNode:
    """Resolves a Scene into a flat prompt string using the loaded Knowledge Base."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "warnings", "errors", "json")

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
    ) -> tuple[str, str, str, str]:
        if scene is None or knowledge_base is None:
            return ("", "", upstream_failure_message("scene or knowledge base"), "")
        config = config or Config()
        # The (optional) semantic fallback reuses the shipped embedding index,
        # loaded once and cached; disabled configs never touch it.
        embedding_index = load_default_index() if config.semantic.enabled else None
        result = resolve_scene(scene, knowledge_base, config, embedding_index=embedding_index)
        separator = config.prompt_builder.separator
        prompt = "" if result.data is None else tags_to_prompt(result.data, separator)
        return (
            prompt,
            format_messages(result.warnings),
            format_messages(result.errors),
            to_raw_json(result.data),
        )
