"""ComfyUI node for the compiler Configuration (MASTER_SPEC §20, §23).

A thin interface: it collects the settings a user actually needs to touch and emits
a single COMPILER_CONFIG the other nodes consume, so behaviour can change without
editing the workflow. It also loads the Knowledge Base and emits it for the Resolver,
so the pipeline needs no separate loader node. It never imports ComfyUI.
"""

from __future__ import annotations

from typing import Any

from compiler.common.config import Config, ConfigError

from .adapters import format_messages
from .kb_loading import load_cached_knowledge_base

_DEBUG_LEVELS = ["none", "basic", "verbose", "developer"]

# The Knowledge Base ships inside the package, so its path is fixed rather than a
# user-facing setting.
_KNOWLEDGE_BASE_PATH = "knowledge_base/"


class ConfigurationNode:
    """Centralizes compiler settings and loads the Knowledge Base for the pipeline."""

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
                        "tooltip": "Which local Ollama model reads your description (e.g. llama3).",
                    },
                ),
                "analyzer_temperature": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.1,
                        "tooltip": "How freely the model interprets. 0 = most consistent.",
                    },
                ),
                "analyzer_max_retries": (
                    "INT",
                    {
                        "default": 3,
                        "min": 0,
                        "max": 10,
                        "tooltip": "How many times to retry if the model returns a bad answer.",
                    },
                ),
                "analyzer_timeout": (
                    "INT",
                    {
                        "default": 300,
                        "min": 1,
                        "max": 3600,
                        "tooltip": (
                            "How long to wait for the model, in seconds. The default is generous "
                            "so the first run (while the model loads) doesn't time out."
                        ),
                    },
                ),
                "resolver_strict_mode": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Report concepts not in the Knowledge Base instead of guessing.",
                    },
                ),
                "resolver_allow_aliases": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Map synonyms to the same tag (e.g. 'girl' = 'female').",
                    },
                ),
                "resolver_expansion_enabled": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Automatically add related tags (e.g. an outfit's parts).",
                    },
                ),
                "resolver_max_expansion_depth": (
                    "INT",
                    {
                        "default": 8,
                        "min": 1,
                        "max": 32,
                        "tooltip": "How far related tags are followed. Higher adds more tags.",
                    },
                ),
                "resolver_include_nsfw": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Allow explicit (NSFW) tags. Off keeps results safe-for-work.",
                    },
                ),
                "validator_allow_unknown_fields": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Keep unexpected fields in the scene data. Usually leave off.",
                    },
                ),
                "prompt_remove_duplicate_tags": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Remove repeated tags from the final prompt. Recommended on.",
                    },
                ),
                "debug_enabled": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "Turn on extra logging to troubleshoot."},
                ),
                "debug_level": (
                    _DEBUG_LEVELS,
                    {"default": "basic", "tooltip": "How much detail the logs include."},
                ),
            },
            # Appended at the END so saved workflows keep their positional widget
            # values (ComfyUI stores widget values positionally).
            "optional": {
                "resolver_knowledge_base_version": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Advanced: pin a Knowledge Base version. Empty = default.",
                    },
                ),
                "semantic_enabled": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Find the closest known tag when a concept isn't recognized. Off by "
                            "default; it never invents tags."
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
                        "tooltip": "How close a match must be for the closest-tag search.",
                    },
                ),
                "semantic_backend": (
                    "STRING",
                    {
                        "default": "char_ngram",
                        "tooltip": "Advanced: which method the closest-tag search uses.",
                    },
                ),
                "knowledge_base_reload": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "tooltip": "Bump this if you edited the Knowledge Base, to reload it.",
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
        resolver_strict_mode: bool,
        resolver_allow_aliases: bool,
        resolver_expansion_enabled: bool,
        resolver_max_expansion_depth: int,
        resolver_include_nsfw: bool,
        validator_allow_unknown_fields: bool,
        prompt_remove_duplicate_tags: bool,
        debug_enabled: bool,
        debug_level: str,
        resolver_knowledge_base_version: str = "",
        semantic_enabled: bool = False,
        semantic_min_similarity: float = 0.5,
        semantic_backend: str = "char_ngram",
        knowledge_base_reload: int = 0,
    ) -> tuple[Any, Any, str, str]:
        document = {
            "analyzer": {
                "model": analyzer_model,
                "temperature": analyzer_temperature,
                "max_retries": analyzer_max_retries,
                "timeout": analyzer_timeout,
            },
            "resolver": {
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
            "prompt_builder": {"remove_duplicate_tags": prompt_remove_duplicate_tags},
            "debug": {"enabled": debug_enabled, "level": debug_level},
        }

        try:
            config = Config.from_json(document)
        except ConfigError as error:
            return (None, None, "", format_messages([error.message]))

        # Load the shipped Knowledge Base and emit it for the Resolver, so the
        # Knowledge Base is loaded in one place with no separate loader node.
        kb, warnings, errors, _raw = load_cached_knowledge_base(
            _KNOWLEDGE_BASE_PATH,
            resolver_knowledge_base_version,
            knowledge_base_reload,
        )
        return (config, kb, warnings, errors)
