"""Analyzer backend interface and the Ollama implementation (MASTER_SPEC §12.3, §12.10).

The Scene Analyzer is the only LLM stage. The backend is kept behind a generic
:class:`AnalyzerBackend` interface so it can be swapped without touching any
downstream stage, and it never imports downstream compiler modules.

:class:`OllamaBackend` talks to a local Ollama server's ``/api/generate`` endpoint
over HTTP using only the standard library. The HTTP call is an injectable
``transport`` so the backend is fully unit-testable without a live Ollama.

Failure modes map to specific codes: connection failure -> SC0012 (Fatal),
timeout -> SC0013, and an unexpected/model response -> SC0018.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from compiler.common.config import Config
from compiler.common.message_codes import message
from compiler.common.result import Message

_DEFAULT_BASE_URL = "http://localhost:11434"

# A transport performs the HTTP POST and returns the parsed JSON body. It may
# raise TimeoutError, ConnectionError, or urllib.error.URLError/HTTPError.
Transport = Callable[[str, dict[str, Any], float], Any]


@dataclass(frozen=True)
class BackendResult:
    """A successful backend response plus telemetry for logging (§12.10)."""

    text: str
    model: str
    duration_seconds: float


class AnalyzerBackendError(Exception):
    """Base class for backend failures; ``code`` maps to Appendix B / extensions."""

    code = "SC0018"

    def to_message(self, **context: Any) -> Message:
        return message(self.code, str(self), **context)


class BackendUnavailableError(AnalyzerBackendError):
    """The backend could not be reached (connection failure)."""

    code = "SC0012"


class BackendTimeoutError(AnalyzerBackendError):
    """The backend did not respond within the configured timeout."""

    code = "SC0013"


class BackendResponseError(AnalyzerBackendError):
    """The backend returned an unexpected response or a model/HTTP error."""

    code = "SC0018"


@runtime_checkable
class AnalyzerBackend(Protocol):
    """A language-model backend that turns a prompt into raw text."""

    def generate(
        self, prompt: str, *, temperature: float | None = None
    ) -> BackendResult:  # pragma: no cover - interface
        ...


def _urllib_transport(url: str, payload: dict[str, Any], timeout: float) -> Any:
    """Default transport: POST JSON and return the parsed JSON body (stdlib only)."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (local Ollama)
        return json.loads(response.read().decode("utf-8"))


class OllamaBackend:
    """Analyzer backend backed by a local Ollama server."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        timeout: float = 60,
        base_url: str = _DEFAULT_BASE_URL,
        transport: Transport | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._timeout = timeout
        self._base_url = base_url.rstrip("/")
        self._transport = transport or _urllib_transport

    @classmethod
    def from_config(
        cls,
        config: Config,
        base_url: str = _DEFAULT_BASE_URL,
        transport: Transport | None = None,
    ) -> OllamaBackend:
        """Build a backend from a Config's ``analyzer`` section."""
        return cls(
            model=config.analyzer.model,
            temperature=config.analyzer.temperature,
            timeout=config.analyzer.timeout,
            base_url=base_url,
            transport=transport,
        )

    def generate(self, prompt: str, *, temperature: float | None = None) -> BackendResult:
        """Send ``prompt`` unmodified to Ollama and return the raw text response.

        Args:
            prompt: The full prompt, sent byte-for-byte unchanged.
            temperature: Optional per-call sampling temperature; falls back to the
                backend's configured temperature when ``None``. Used by the retry
                orchestration to perturb sampling without altering the prompt.

        Raises:
            BackendTimeoutError: On timeout (SC0013).
            BackendUnavailableError: On connection failure (SC0012).
            BackendResponseError: On an HTTP error or unexpected response (SC0018).
        """
        url = f"{self._base_url}/api/generate"
        effective_temperature = self._temperature if temperature is None else temperature
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": effective_temperature},
        }

        start = time.perf_counter()
        try:
            raw = self._transport(url, payload, self._timeout)
        except TimeoutError as exc:
            raise BackendTimeoutError(
                f"Analyzer backend timed out after {self._timeout}s."
            ) from exc
        except urllib.error.HTTPError as exc:
            raise BackendResponseError(
                f"Analyzer backend returned HTTP {exc.code}: {exc.reason}."
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise BackendTimeoutError(
                    f"Analyzer backend timed out after {self._timeout}s."
                ) from exc
            raise BackendUnavailableError(
                f"Analyzer backend is unavailable: {exc.reason}."
            ) from exc
        except ConnectionError as exc:
            raise BackendUnavailableError(f"Analyzer backend is unavailable: {exc}.") from exc
        duration = time.perf_counter() - start

        if not isinstance(raw, dict) or "response" not in raw:
            raise BackendResponseError("Ollama response is missing the 'response' field.")
        return BackendResult(text=raw["response"], model=self._model, duration_seconds=duration)
