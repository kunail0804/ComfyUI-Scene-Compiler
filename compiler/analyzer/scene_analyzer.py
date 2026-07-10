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

# Retry temperature escalation (§12.9). The prompt is reused byte-for-byte on
# every attempt, so at temperature 0 a bad-JSON attempt would deterministically
# repeat and every retry would fail identically. Escalating the sampling
# temperature on retries only (never the first attempt) lets a malformed run
# self-recover, exactly like a fresh manual re-run, while keeping the happy path
# deterministic.
_TEMPERATURE_STEP = 0.2
_TEMPERATURE_CAP = 1.0


def _attempt_temperature(base: float, attempt_index: int) -> float:
    """Temperature for a 0-based attempt: the base first, then escalating on retries."""
    if attempt_index == 0:
        return base
    return min(base + _TEMPERATURE_STEP * attempt_index, _TEMPERATURE_CAP)


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
    raw_response = ""

    base_temperature = config.analyzer.temperature

    for _ in range(max_attempts):
        temperature = _attempt_temperature(base_temperature, attempts)
        attempts += 1
        try:
            backend_result = backend.generate(prompt, temperature=temperature)
        except (BackendUnavailableError, BackendTimeoutError) as exc:
            # Terminal: the backend is unreachable or too slow; retrying cannot help.
            return _finalize(
                CompilerResult().add_error(exc.to_message()),
                model=model,
                attempts=attempts,
                duration=duration,
                raw_response=raw_response,
                logger=logger,
            )
        except BackendResponseError as exc:
            last_failure = CompilerResult().add_error(exc.to_message(attempt=attempts))
            continue

        model = backend_result.model
        duration += backend_result.duration_seconds
        raw_response = backend_result.text

        parsed = parse_scene_response(backend_result.text, logger)
        if parsed.success:
            return _finalize(
                parsed,
                model=model,
                attempts=attempts,
                duration=duration,
                raw_response=raw_response,
                logger=logger,
            )
        last_failure = parsed

    # Retries exhausted: return the last bad-response failure (SC0011 / SC0018).
    return _finalize(
        last_failure,
        model=model,
        attempts=attempts,
        duration=duration,
        raw_response=raw_response,
        logger=logger,
    )


def _finalize(
    result: CompilerResult,
    *,
    model: str,
    attempts: int,
    duration: float,
    raw_response: str,
    logger: StructuredLogger | None,
) -> CompilerResult:
    """Attach analyzer telemetry to a result and log the outcome."""
    metadata: dict[str, Any] = {
        "model": model,
        "attempts": attempts,
        "retries": attempts - 1,
        "duration_seconds": duration,
        "valid": result.success,
        # The last raw model text, so a failed compile is still debuggable; empty
        # when the backend never returned text (a terminal connection/timeout).
        "raw_response": raw_response,
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
