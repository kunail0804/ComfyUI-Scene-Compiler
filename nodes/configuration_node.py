"""ComfyUI node for the compiler Configuration (MASTER_SPEC §20, §23).

A thin interface: it collects the configuration options as node inputs and emits a
single COMPILER_CONFIG that the other nodes consume, so behaviour can change without
editing the workflow. It also loads the Knowledge Base from the configured path and
emits it for the Resolver, so the Knowledge Base directory is entered in exactly one
place (there is no separate Knowledge Base Loader node). It never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config, ConfigError

from .adapters import format_messages
from .kb_loading import load_cached_knowledge_base

_DEBUG_LEVELS = ["none", "basic", "verbose", "developer"]


class ConfigurationNode:
    """Centralizes compiler configuration and loads the Knowledge Base for the pipeline."""

    CATEGORY = "Scene Compiler"
    FUNCTION = "run"
    RETURN_TYPES = ("COMPILER_CONFIG", "KNOWLEDGE_BASE", "STRING", "STRING")
    RETURN_NAMES = ("config", "knowledge_base", "warnings", "errors")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "analyzer_model": (
                    "STRING",
                    {
                        "default": "llama3",
                        "tooltip": "Ollama model the Scene Analyzer uses to read the description.",
                    },
                ),
                "analyzer_temperature": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.1,
                        "tooltip": "Analyzer sampling temperature. 0 = most repeatable.",
                    },
                ),
                "analyzer_max_retries": (
                    "INT",
                    {
                        "default": 3,
                        "min": 0,
                        "max": 10,
                        "tooltip": "How many times to re-ask when the model returns bad JSON.",
                    },
                ),
                "analyzer_timeout": (
                    "INT",
                    {
                        "default": 300,
                        "min": 1,
                        "max": 3600,
                        "tooltip": (
                            "Seconds to wait for the model. 300 s is generous so a model that "
                            "cold-loads into VRAM on the first call does not time out."
                        ),
                    },
                ),
                "knowledge_base": (
                    "STRING",
                    {
                        "default": "knowledge_base/",
                        "tooltip": (
                            "Knowledge Base directory. Relative paths resolve against the node "
                            "package. This is the authoritative path when this Configuration is "
                            "wired into the Knowledge Base Loader."
                        ),
                    },
                ),
                "resolver_strict_mode": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "Report unknown concepts instead of guessing."},
                ),
                "resolver_allow_aliases": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "Resolve aliases to their canonical entry."},
                ),
                "resolver_expansion_enabled": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "Auto-add tags from an entry's expansion list."},
                ),
                "resolver_max_expansion_depth": (
                    "INT",
                    {
                        "default": 8,
                        "min": 1,
                        "max": 32,
                        "tooltip": "How deep expansion may recurse before stopping.",
                    },
                ),
                "resolver_include_nsfw": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Include explicit-rated Knowledge Base entries. Off = SFW only.",
                    },
                ),
                "validator_allow_unknown_fields": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Keep unrecognized Scene JSON fields instead of stripping them.",
                    },
                ),
                "prompt_target": (
                    "STRING",
                    {
                        "default": "easy_illustrious",
                        "tooltip": "Reserved prompt-format label. Currently informational.",
                    },
                ),
                "prompt_separator": (
                    "STRING",
                    {
                        "default": ",",
                        "tooltip": "String used to join the resolved tags into the final prompt.",
                    },
                ),
                "prompt_remove_duplicate_tags": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Drop duplicate tags after expansion (warns SC0007).",
                    },
                ),
                "debug_enabled": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "Enable extra diagnostic logging."},
                ),
                "debug_level": (
                    _DEBUG_LEVELS,
                    {"default": "basic", "tooltip": "Verbosity of debug logging when enabled."},
                ),
            },
            # Appended at the END so saved workflows keep their positional widget
            # values (ComfyUI stores widget values positionally).
            "optional": {
                "analyzer_system_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Advanced: override the analyzer system prompt.",
                    },
                ),
                "resolver_knowledge_base_version": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Pin a KB dataset version. Empty = unpinned.",
                    },
                ),
                "semantic_enabled": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Opt-in nearest-neighbour fallback for concepts that miss "
                            "deterministic lookup. Off by default; deterministic lookup wins."
                        ),
                    },
                ),
                "semantic_min_similarity": (
                    "FLOAT",
                    {
                        "default": 0.5,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": "Minimum similarity to accept a semantic-fallback match.",
                    },
                ),
                "semantic_backend": (
                    "STRING",
                    {
                        "default": "char_ngram",
                        "tooltip": "Embedding backend for the semantic fallback (offline).",
                    },
                ),
                "knowledge_base_reload": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "tooltip": "Bump to force a fresh read of the Knowledge Base from disk.",
                    },
                ),
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
        knowledge_base_reload: int = 0,
    ) -> tuple[Any, Any, str, str]:
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
            return (None, None, "", format_messages([error.message]))

        # Load the Knowledge Base from the configured path/version and emit it for
        # the Resolver, so the Knowledge Base directory is entered in one place.
        kb, warnings, errors, _raw = load_cached_knowledge_base(
            knowledge_base,
            resolver_knowledge_base_version,
            knowledge_base_reload,
        )
        return (config, kb, warnings, errors)
