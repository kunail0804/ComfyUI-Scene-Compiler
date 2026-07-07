"""The Prompt Builder (MASTER_SPEC §19).

Formats the Category Map into one plain UTF-8 Prompt Output per category, plus
the reserved ``negative`` and ``scene`` outputs. This stage is formatting only:
it never generates, removes, reorders, deduplicates, escapes, or optimizes tags
(§19.1, §19.5).

Version 1 always emits all 21 outputs (19 categories + 2 reserved) so the ComfyUI
node exposes a stable set of sockets. Empty categories yield an empty string —
never null or placeholder text (§19.4). Output names are the lowercase canonical
category identifiers (and ``negative`` / ``scene``), corresponding one-to-one to
the §19.2/§19.3 display names.
"""

from __future__ import annotations

from compiler.common.categories import CANONICAL_CATEGORIES
from compiler.common.config import Config
from compiler.common.log import StructuredLogger
from compiler.common.result import CompilerResult
from schemas.models import CategoryMap, PromptOutput

# Reserved outputs, always emitted empty in V1 (nothing populates them).
RESERVED_OUTPUTS: tuple[str, ...] = ("negative", "scene")


def build_prompts(
    category_map: CategoryMap,
    config: Config,
    logger: StructuredLogger | None = None,
) -> CompilerResult:
    """Format a Category Map into the final Prompt Outputs.

    Returns:
        A CompilerResult whose ``data`` is the tuple of :class:`PromptOutput`:
        one per canonical category (in order) followed by the reserved outputs.
    """
    separator = config.prompt_builder.separator

    outputs: list[PromptOutput] = []
    for category in CANONICAL_CATEGORIES:
        value = separator.join(tag.tag for tag in category_map.tags_for(category))
        outputs.append(PromptOutput(name=category, value=value))

    for reserved in RESERVED_OUTPUTS:
        outputs.append(PromptOutput(name=reserved, value=""))

    if logger is not None:
        logger.basic("prompts_built", outputs=len(outputs))
    return CompilerResult(data=tuple(outputs))
