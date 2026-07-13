"""Typed, injectable compiler configuration (MASTER_SPEC §23).

Configuration changes behaviour, never architecture, and MUST stay deterministic:
there is no random-seed option and unknown keys are rejected. Every section and
field is optional; omitted values fall back to the §23.2 defaults.

Configuration is loaded once and injected into stages — this module intentionally
exposes no global/singleton config. Invalid configuration is a Fatal condition
(the compiler cannot run) and raises :class:`ConfigError` carrying an ``SC0014``
message.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from compiler.common.result import Message, Severity
from schemas.validation import validate_document

_CONFIG_SCHEMA = "configuration"


class ConfigError(Exception):
    """Raised when configuration is invalid; carries the Fatal SC0014 message."""

    def __init__(self, message: Message) -> None:
        super().__init__(message.description)
        self.message = message


def _section_from_json(section_cls: type, data: Mapping[str, Any] | None) -> Any:
    """Build a config section, filling missing fields with the section's defaults."""
    values = data or {}
    known = {f.name for f in fields(section_cls)}
    return section_cls(**{name: values[name] for name in known if name in values})


@dataclass(frozen=True)
class AnalyzerConfig:
    """Scene Analyzer options (§23.2). temperature 0 maximizes repeatability."""

    backend: str = "ollama"
    model: str = "llama3"
    temperature: float = 0.0
    max_retries: int = 3
    timeout: int = 60
    system_prompt: str | None = None

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "backend": self.backend,
            "model": self.model,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
        }
        if self.system_prompt is not None:
            result["system_prompt"] = self.system_prompt
        return result


@dataclass(frozen=True)
class ResolverConfig:
    """Resolver options (§23.2)."""

    knowledge_base: str = "knowledge_base/"
    strict_mode: bool = True
    allow_aliases: bool = True
    expansion_enabled: bool = True
    max_expansion_depth: int = 8
    include_nsfw: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "knowledge_base": self.knowledge_base,
            "strict_mode": self.strict_mode,
            "allow_aliases": self.allow_aliases,
            "expansion_enabled": self.expansion_enabled,
            "max_expansion_depth": self.max_expansion_depth,
            "include_nsfw": self.include_nsfw,
        }


@dataclass(frozen=True)
class ValidatorConfig:
    """Scene Validator options (§23.2)."""

    allow_unknown_fields: bool = False

    def to_json(self) -> dict[str, Any]:
        return {"allow_unknown_fields": self.allow_unknown_fields}


@dataclass(frozen=True)
class PromptBuilderConfig:
    """Prompt-rendering options (§23.2).

    ``separator`` joins the resolved tags into the flat prompt;
    ``remove_duplicate_tags`` gates the post-expansion tag deduplication in the
    Resolver (SC0007). ``trim_empty_outputs`` was removed in V2: after the V1.1
    drop of categories there are no empty outputs to trim.
    """

    target: str = "easy_illustrious"
    separator: str = ","
    remove_duplicate_tags: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "separator": self.separator,
            "remove_duplicate_tags": self.remove_duplicate_tags,
        }


@dataclass(frozen=True)
class DebugConfig:
    """Debug/logging options (§23.2)."""

    enabled: bool = False
    level: str = "basic"

    def to_json(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "level": self.level}


@dataclass(frozen=True)
class Config:
    """The complete compiler configuration (§23.2), immutable once produced."""

    schema: str = "1.0"
    analyzer: AnalyzerConfig = AnalyzerConfig()
    resolver: ResolverConfig = ResolverConfig()
    validator: ValidatorConfig = ValidatorConfig()
    prompt_builder: PromptBuilderConfig = PromptBuilderConfig()
    debug: DebugConfig = DebugConfig()

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Config:
        """Validate and build a Config; raise ConfigError (SC0014) if invalid."""
        issues = validate_document(data, _CONFIG_SCHEMA)
        if issues:
            details = "; ".join(f"{i.path or '<root>'}: {i.message}" for i in issues)
            raise ConfigError(
                Message(
                    code="SC0014",
                    severity=Severity.FATAL,
                    title="Invalid configuration",
                    description=f"Configuration failed schema validation: {details}",
                    context={"issues": [i.message for i in issues]},
                )
            )
        return cls(
            schema=data.get("schema", "1.0"),
            analyzer=_section_from_json(AnalyzerConfig, data.get("analyzer")),
            resolver=_section_from_json(ResolverConfig, data.get("resolver")),
            validator=_section_from_json(ValidatorConfig, data.get("validator")),
            prompt_builder=_section_from_json(PromptBuilderConfig, data.get("prompt_builder")),
            debug=_section_from_json(DebugConfig, data.get("debug")),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "analyzer": self.analyzer.to_json(),
            "resolver": self.resolver.to_json(),
            "validator": self.validator.to_json(),
            "prompt_builder": self.prompt_builder.to_json(),
            "debug": self.debug.to_json(),
        }


def load_config(path: str | Path) -> Config:
    """Load and validate configuration from a JSON file.

    Raises:
        ConfigError: If the file contents fail schema validation (SC0014).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Config.from_json(data)
