"""ComfyUI node for the Prompt Builder (MASTER_SPEC §20, §19).

A thin interface: it adapts the Category Map input to the Prompt Builder module
and exposes one string output per category plus the reserved ``negative`` and
``scene`` outputs (always empty in V1). No compiler logic; it never imports
ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.builder.prompt_builder import RESERVED_OUTPUTS, build_prompts
from compiler.common.categories import CANONICAL_CATEGORIES
from compiler.common.config import Config

# The stable set of node outputs: one per canonical category, then the reserved
# outputs. Matches the Prompt Outputs produced by build_prompts.
_OUTPUT_NAMES: tuple[str, ...] = (*CANONICAL_CATEGORIES, *RESERVED_OUTPUTS)


class PromptBuilderNode:
    """Formats a Category Map into one prompt string per category (+ reserved)."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",) * len(_OUTPUT_NAMES)
    RETURN_NAMES = _OUTPUT_NAMES

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {"category_map": ("CATEGORY_MAP",)},
            "optional": {"config": ("COMPILER_CONFIG",)},
        }

    def run(self, category_map: Any, config: Config | None = None) -> tuple[str, ...]:
        result = build_prompts(category_map, config or Config())
        by_name = {output.name: output.value for output in result.data}
        return tuple(by_name[name] for name in _OUTPUT_NAMES)
