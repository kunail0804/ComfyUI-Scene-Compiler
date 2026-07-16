"""ComfyUI node for the Scene Analyzer (MASTER_SPEC §20).

A thin interface: it adapts ComfyUI inputs to the Analyzer module and surfaces the
CompilerResult's data, warnings, and errors. It contains no compiler logic and
never imports ComfyUI.

Analyzer settings (model, temperature, retries, timeout, system prompt) live on
the **Configuration** node and reach this node through the optional ``config``
input, so a setting like the model name is entered in exactly one place. Without a
Configuration node the built-in defaults apply (llama3, temperature 0), with a
generous 300 s timeout so a local Ollama model that cold-loads into VRAM on the
first call does not time out.
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
                        "tooltip": "The scene description to analyze, in plain language.",
                    },
                ),
            },
            "optional": {
                "config": (
                    "COMPILER_CONFIG",
                    {
                        "tooltip": (
                            "Optional Configuration node. Supplies the analyzer model, "
                            "temperature, retries and timeout. If left unconnected, the "
                            "defaults apply (llama3, temperature 0, 300 s timeout)."
                        )
                    },
                ),
                "system_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": (
                            "Advanced: override the analyzer system prompt. Leave empty to "
                            "use the built-in prompt (or the one from the Configuration node)."
                        ),
                    },
                ),
            },
        }

    def run(
        self,
        natural_language: str,
        config: Config | None = None,
        system_prompt: str = "",
    ) -> tuple[Any, str, str, str]:
        config = self._resolve_config(config, system_prompt)
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

    @staticmethod
    def _resolve_config(config: Config | None, system_prompt: str) -> Config:
        """Pick the effective config, applying the optional system-prompt override.

        No Configuration node: build a default config with a cold-load-friendly
        timeout. A non-empty ``system_prompt`` widget always wins over whatever the
        Configuration node carries.
        """
        if config is None:
            analyzer: dict[str, Any] = {"timeout": _DEFAULT_TIMEOUT}
            if system_prompt:
                analyzer["system_prompt"] = system_prompt
            return Config.from_json({"analyzer": analyzer})
        if system_prompt:
            document = config.to_json()
            document.setdefault("analyzer", {})["system_prompt"] = system_prompt
            return Config.from_json(document)
        return config
