"""ComfyUI node for the Scene Analyzer (MASTER_SPEC §20).

A thin interface: it adapts ComfyUI inputs to the Analyzer module and surfaces the
CompilerResult's data, warnings, and errors. It contains no compiler logic and
never imports ComfyUI.

Analyzer settings (model, temperature, retries, timeout) live on the **Configuration**
node and reach this node through its optional ``config`` input, so they are entered in
one place. Without a Configuration node the built-in defaults apply (llama3,
temperature 0) with a generous 300 s timeout, because a local Ollama model cold-loads
into VRAM on the first call and a shorter timeout often fails on first use.
"""

from __future__ import annotations

from typing import Any

from compiler.analyzer.backend import OllamaBackend
from compiler.analyzer.scene_analyzer import analyze
from compiler.common.config import Config

from .adapters import format_messages

# Cold-load-friendly fallback timeout used only when no Configuration node is
# wired; a local model loading into VRAM on the first call can take minutes.
_DEFAULT_TIMEOUT = 300


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
                "natural_language": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Describe your scene in plain language.",
                    },
                ),
            },
            "optional": {
                "config": (
                    "COMPILER_CONFIG",
                    {
                        "tooltip": (
                            "Optional: connect a Configuration node to set the model and other "
                            "options. Without it, sensible defaults are used."
                        )
                    },
                ),
            },
        }

    def run(
        self,
        natural_language: str,
        config: Config | None = None,
    ) -> tuple[Any, str, str, str]:
        if config is None:
            # No Configuration node: use defaults with a cold-load-friendly timeout.
            config = Config.from_json({"analyzer": {"timeout": _DEFAULT_TIMEOUT}})
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
