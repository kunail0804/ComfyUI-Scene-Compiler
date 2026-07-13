"""ComfyUI node for the compiler Configuration (MASTER_SPEC §20, §23).

A thin interface: it collects the configuration options as node inputs and emits
a single COMPILER_CONFIG that the other nodes consume, so behaviour can change
without editing the workflow. No compiler logic; it never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config, ConfigError

from .adapters import format_messages

_DEBUG_LEVELS = ["none", "basic", "verbose", "developer"]


class ConfigurationNode:
    """Centralizes compiler configuration and emits it for the other nodes."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("COMPILER_CONFIG", "STRING")
    RETURN_NAMES = ("config", "errors")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "analyzer_model": ("STRING", {"default": "llama3"}),
                "analyzer_temperature": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.1},
                ),
                "analyzer_max_retries": ("INT", {"default": 3, "min": 0, "max": 10}),
                "analyzer_timeout": ("INT", {"default": 300, "min": 1, "max": 3600}),
                "knowledge_base": ("STRING", {"default": "knowledge_base/"}),
                "resolver_strict_mode": ("BOOLEAN", {"default": True}),
                "resolver_allow_aliases": ("BOOLEAN", {"default": True}),
                "resolver_expansion_enabled": ("BOOLEAN", {"default": True}),
                "resolver_max_expansion_depth": ("INT", {"default": 8, "min": 1, "max": 32}),
                "resolver_include_nsfw": ("BOOLEAN", {"default": False}),
                "validator_allow_unknown_fields": ("BOOLEAN", {"default": False}),
                "prompt_target": ("STRING", {"default": "easy_illustrious"}),
                "prompt_separator": ("STRING", {"default": ","}),
                "prompt_remove_duplicate_tags": ("BOOLEAN", {"default": True}),
                "debug_enabled": ("BOOLEAN", {"default": False}),
                "debug_level": (_DEBUG_LEVELS, {"default": "basic"}),
            },
            # Appended at the END so saved workflows keep their positional widget
            # values (ComfyUI stores widget values positionally).
            "optional": {
                "analyzer_system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "resolver_knowledge_base_version": ("STRING", {"default": ""}),
                "semantic_enabled": ("BOOLEAN", {"default": False}),
                "semantic_min_similarity": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05},
                ),
                "semantic_backend": ("STRING", {"default": "char_ngram"}),
            },
        }

    def run(
        self,
        analyzer_model: str,
        analyzer_temperature: float,
        analyzer_max_retries: int,
        analyzer_timeout: int,
        knowledge_base: str,
        resolver_strict_mode: bool,
        resolver_allow_aliases: bool,
        resolver_expansion_enabled: bool,
        resolver_max_expansion_depth: int,
        resolver_include_nsfw: bool,
        validator_allow_unknown_fields: bool,
        prompt_target: str,
        prompt_separator: str,
        prompt_remove_duplicate_tags: bool,
        debug_enabled: bool,
        debug_level: str,
        analyzer_system_prompt: str = "",
        resolver_knowledge_base_version: str = "",
        semantic_enabled: bool = False,
        semantic_min_similarity: float = 0.5,
        semantic_backend: str = "char_ngram",
    ) -> tuple[Any, str]:
        analyzer: dict[str, Any] = {
            "model": analyzer_model,
            "temperature": analyzer_temperature,
            "max_retries": analyzer_max_retries,
            "timeout": analyzer_timeout,
        }
        if analyzer_system_prompt:
            analyzer["system_prompt"] = analyzer_system_prompt

        document = {
            "analyzer": analyzer,
            "resolver": {
                "knowledge_base": knowledge_base,
                "strict_mode": resolver_strict_mode,
                "allow_aliases": resolver_allow_aliases,
                "expansion_enabled": resolver_expansion_enabled,
                "max_expansion_depth": resolver_max_expansion_depth,
                "include_nsfw": resolver_include_nsfw,
                **(
                    {"knowledge_base_version": resolver_knowledge_base_version}
                    if resolver_knowledge_base_version
                    else {}
                ),
            },
            "validator": {"allow_unknown_fields": validator_allow_unknown_fields},
            "semantic": {
                "enabled": semantic_enabled,
                "min_similarity": semantic_min_similarity,
                "backend": semantic_backend,
            },
            "prompt_builder": {
                "target": prompt_target,
                "separator": prompt_separator,
                "remove_duplicate_tags": prompt_remove_duplicate_tags,
            },
            "debug": {"enabled": debug_enabled, "level": debug_level},
        }

        try:
            config = Config.from_json(document)
        except ConfigError as error:
            return (None, format_messages([error.message]))
        return (config, "")
