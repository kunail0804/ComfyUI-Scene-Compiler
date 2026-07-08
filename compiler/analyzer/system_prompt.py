"""Loading of the official Analyzer system prompt (MASTER_SPEC §13).

The default prompt ships under ``prompts/`` and defines the Analyzer's behaviour
(extract explicit concepts only; never generate tags or invent information). It is
overridable via ``config.analyzer.system_prompt``.
"""

from __future__ import annotations

from pathlib import Path

from compiler.common.config import Config

DEFAULT_SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "analyzer_system_prompt.md"
)


def load_default_system_prompt() -> str:
    """Return the official system prompt shipped under ``prompts/``."""
    return DEFAULT_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def resolve_system_prompt(config: Config) -> str:
    """Return the configured system prompt, or the shipped default when unset."""
    if config.analyzer.system_prompt is not None:
        return config.analyzer.system_prompt
    return load_default_system_prompt()
