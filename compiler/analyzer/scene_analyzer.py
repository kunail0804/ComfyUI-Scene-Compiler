"""The Scene Analyzer orchestration (MASTER_SPEC §12.9, §12.10).

Drives the LLM stage: compose the prompt once, call the backend, parse and
validate the response, and retry a bounded number of times on a bad response.
The original prompt is reused unchanged on every attempt (§12.9) and JSON is
never repaired heuristically.

Terminal failures return immediately: a connection failure is Fatal (SC0012) and
a timeout is SC0013. A bad response (parse/schema failure SC0011, or an
unexpected backend response SC0018) is retried; after the attempts are exhausted
the last such error is returned.
"""

from __future__ import annotations

from typing import Any

from compiler.analyzer.backend import (
    AnalyzerBackend,
    BackendResponseError,
    BackendTimeoutError,
    BackendUnavailableError,
)
from compiler.analyzer.response_parser import parse_scene_response
from compiler.analyzer.system_prompt import resolve_system_prompt
from compiler.common.config import Config
from compiler.common.log import StructuredLogger
from compiler.common.result import CompilerResult


def analyze(
    description: str,
    backend: AnalyzerBackend,
    config: Config,
    logger: StructuredLogger | None = None,
) -> CompilerResult:
    """Analyze a natural-language description into a validated Scene.

    Args:
        description: The user's natural-language scene description.
        backend: The language-model backend (see :mod:`compiler.analyzer.backend`).
        config: The compiler configuration (drives model, retries, and the prompt).
        logger: Optional structured logger.

    Returns:
        A CompilerResult whose ``data`` is the validated :class:`Scene` on
        success, or ``None`` with the terminal error otherwise. ``metadata``
        reports the model, the number of attempts/retries, and the request
        duration.
    """
    prompt = f"{resolve_system_prompt(config)}\n\n{description}"
    max_attempts = config.analyzer.max_retries + 1

    # Seeded so the type is always a CompilerResult; overwritten on the first
    # failed attempt (and the loop always runs at least once).
    last_failure = CompilerResult()
    model = config.analyzer.model
    duration = 0.0
    attempts = 0

    for _ in range(max_attempts):
        attempts += 1
        try:
            backend_result = backend.generate(prompt)
        except (BackendUnavailableError, BackendTimeoutError) as exc:
            # Terminal: the backend is unreachable or too slow; retrying cannot help.
            return _finalize(
                CompilerResult().add_error(exc.to_message()),
                model=model,
                attempts=attempts,
                duration=duration,
                logger=logger,
            )
        except BackendResponseError as exc:
            last_failure = CompilerResult().add_error(exc.to_message(attempt=attempts))
            continue

        model = backend_result.model
        duration += backend_result.duration_seconds

        parsed = parse_scene_response(backend_result.text, logger)
        if parsed.success:
            return _finalize(
                parsed, model=model, attempts=attempts, duration=duration, logger=logger
            )
        last_failure = parsed

    # Retries exhausted: return the last bad-response failure (SC0011 / SC0018).
    return _finalize(last_failure, model=model, attempts=attempts, duration=duration, logger=logger)


def _finalize(
    result: CompilerResult,
    *,
    model: str,
    attempts: int,
    duration: float,
    logger: StructuredLogger | None,
) -> CompilerResult:
    """Attach analyzer telemetry to a result and log the outcome."""
    metadata: dict[str, Any] = {
        "model": model,
        "attempts": attempts,
        "retries": attempts - 1,
        "duration_seconds": duration,
        "valid": result.success,
    }
    finalized = CompilerResult(
        data=result.data,
        warnings=result.warnings,
        errors=result.errors,
        metadata=metadata,
    )
    if logger is not None:
        logger.basic("scene_analyzed", **metadata)
    return finalized
