"""ComfyUI node for the Scene Analyzer (MASTER_SPEC §20).

A thin interface: it adapts ComfyUI inputs to the Analyzer module and surfaces the
CompilerResult's data, warnings, and errors. It contains no compiler logic and
never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.analyzer.backend import OllamaBackend
from compiler.analyzer.scene_analyzer import analyze
from compiler.common.config import Config

from .adapters import format_messages


class SceneAnalyzerNode:
    """Runs the Scene Analyzer and emits Scene plus warnings/errors."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("SCENE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("scene", "warnings", "errors", "raw")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "natural_language": ("STRING", {"multiline": True, "default": ""}),
                "model_name": ("STRING", {"default": "llama3"}),
                "temperature": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "timeout": ("INT", {"default": 60, "min": 1, "max": 3600}),
            },
            "optional": {
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    def run(
        self,
        natural_language: str,
        model_name: str,
        temperature: float,
        timeout: int,
        system_prompt: str = "",
    ) -> tuple[Any, str, str]:
        analyzer: dict[str, Any] = {
            "model": model_name,
            "temperature": temperature,
            "timeout": timeout,
        }
        if system_prompt:
            analyzer["system_prompt"] = system_prompt

        config = Config.from_json({"analyzer": analyzer})
        backend = OllamaBackend.from_config(config)
        result = analyze(natural_language, backend, config)
        return (
            result.data,
            format_messages(result.warnings),
            format_messages(result.errors),
            # The actual raw model text (empty on a terminal backend failure), so
            # the ``raw`` output reflects what the model returned rather than a
            # re-serialization of the parsed Scene.
            result.metadata.get("raw_response", ""),
        )
