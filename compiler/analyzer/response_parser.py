"""Parsing and validation of the Analyzer's model response (MASTER_SPEC §12.2, §12.8).

Turns the raw model response text into a validated :class:`Scene`. The response
MUST be a single valid JSON document conforming to the Scene schema; invalid
output MUST NOT continue through the compiler.

JSON is never repaired heuristically (§12.9): malformed or markdown-wrapped output
fails here, which the retry orchestration (issue #18) uses to request a corrected
response. Any parse or validation failure is reported as SC0011.
"""

from __future__ import annotations

import json
from typing import Any

from compiler.common.log import StructuredLogger
from compiler.common.message_codes import message
from compiler.common.result import CompilerResult
from schemas.models import Scene
from schemas.validation import validate_document

# The Scene schema version stamped onto compiler-owned metadata when the model
# leaves it empty (the model is instructed to emit `"metadata": {}`).
SCENE_SCHEMA_VERSION = "1.0"


def parse_scene_response(text: str, logger: StructuredLogger | None = None) -> CompilerResult:
    """Parse and validate an Analyzer response into a Scene.

    Returns:
        A CompilerResult whose ``data`` is the validated :class:`Scene` on
        success, or ``None`` with an SC0011 error when the response is not a
        valid Scene JSON document.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return _reject("json_decode", f"Analyzer response is not valid JSON: {exc}", logger)

    if not isinstance(data, dict):
        return _reject(
            "not_object",
            f"Analyzer response must be a JSON object, got {type(data).__name__}.",
            logger,
        )

    _stamp_metadata(data)

    issues = validate_document(data, "scene")
    if issues:
        detail = "; ".join(f"{issue.path or '<root>'}: {issue.message}" for issue in issues)
        return _reject("schema", f"Analyzer response failed Scene validation: {detail}", logger)

    scene = Scene.from_json(data)
    if logger is not None:
        logger.verbose("analyzer_response_parsed", characters=len(scene.characters))
    return CompilerResult(data=scene)


def _stamp_metadata(data: dict[str, Any]) -> None:
    """Ensure compiler-owned metadata carries a schema_version before validation."""
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        metadata.setdefault("schema_version", SCENE_SCHEMA_VERSION)


def _reject(kind: str, description: str, logger: StructuredLogger | None) -> CompilerResult:
    if logger is not None:
        logger.basic("analyzer_response_rejected", kind=kind)
    return CompilerResult().add_error(message("SC0011", description, kind=kind))
