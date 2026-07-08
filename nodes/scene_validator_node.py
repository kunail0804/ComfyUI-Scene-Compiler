"""ComfyUI node for the Scene Validator (MASTER_SPEC §20).

A thin interface: it adapts the Scene input to the Scene Validator module and
surfaces the CompilerResult's data, warnings, and errors. No compiler logic; it
never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config
from compiler.validator.scene_validator import validate_scene

from .adapters import format_messages


class SceneValidatorNode:
    """Validates and normalizes a Scene, passing warnings/errors through."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("SCENE", "STRING", "STRING")
    RETURN_NAMES = ("scene", "warnings", "errors")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {"scene": ("SCENE",)},
            "optional": {"config": ("COMPILER_CONFIG",)},
        }

    def run(self, scene: Any, config: Config | None = None) -> tuple[Any, str, str]:
        result = validate_scene(scene.to_json(), config or Config())
        return (result.data, format_messages(result.warnings), format_messages(result.errors))
