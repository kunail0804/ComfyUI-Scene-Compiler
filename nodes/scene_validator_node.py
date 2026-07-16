"""ComfyUI node for the Scene Validator (MASTER_SPEC §20).

A thin interface: it adapts the Scene input to the Scene Validator module and
surfaces the CompilerResult's data, warnings, and errors. No compiler logic; it
never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config
from compiler.validator.scene_validator import validate_scene

from .adapters import format_messages, to_raw_json, upstream_failure_message


class SceneValidatorNode:
    """Validates and normalizes a Scene, passing warnings/errors through."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("SCENE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("scene", "warnings", "errors", "raw")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "scene": ("SCENE", {"tooltip": "Raw Scene JSON from the Scene Analyzer."}),
            },
            "optional": {
                "config": (
                    "COMPILER_CONFIG",
                    {"tooltip": "Optional Configuration node; supplies the unknown-field policy."},
                )
            },
        }

    def run(self, scene: Any, config: Config | None = None) -> tuple[Any, str, str, str]:
        if scene is None:
            return (None, "", upstream_failure_message("scene"), "")
        result = validate_scene(scene.to_json(), config or Config())
        return (
            result.data,
            format_messages(result.warnings),
            format_messages(result.errors),
            to_raw_json(result.data),
        )
