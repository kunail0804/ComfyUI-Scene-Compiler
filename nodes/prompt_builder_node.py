"""ComfyUI node for the Prompt Builder (MASTER_SPEC §20, §19).

A thin interface: it adapts the Category Map input to the Prompt Builder module
and exposes one string output per category plus the reserved ``negative`` and
``scene`` outputs (always empty in V1). No compiler logic; it never imports
ComfyUI.
"""

from __future__ import annotations

import json
from typing import Any

from compiler.builder.prompt_builder import RESERVED_OUTPUTS, build_prompts
from compiler.common.categories import CANONICAL_CATEGORIES
from compiler.common.config import Config

# One output per canonical category, then the reserved outputs (matching the
# Prompt Outputs produced by build_prompts), then a debug `raw` dump.
_OUTPUT_NAMES: tuple[str, ...] = (*CANONICAL_CATEGORIES, *RESERVED_OUTPUTS)
_RETURN_NAMES: tuple[str, ...] = (*_OUTPUT_NAMES, "raw")


class PromptBuilderNode:
    """Formats a Category Map into one prompt string per category (+ reserved)."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",) * len(_RETURN_NAMES)
    RETURN_NAMES = _RETURN_NAMES

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {"category_map": ("CATEGORY_MAP",)},
            "optional": {"config": ("COMPILER_CONFIG",)},
        }

    def run(self, category_map: Any, config: Config | None = None) -> tuple[str, ...]:
        if category_map is None:
            # Upstream produced no Category Map; emit empty strings rather than crash.
            return tuple("" for _ in _RETURN_NAMES)
        result = build_prompts(category_map, config or Config())
        by_name = {output.name: output.value for output in result.data}
        values = tuple(by_name[name] for name in _OUTPUT_NAMES)
        raw = json.dumps(by_name, indent=2, ensure_ascii=False)
        return (*values, raw)
