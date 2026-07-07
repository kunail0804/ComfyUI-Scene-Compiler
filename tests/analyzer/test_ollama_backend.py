"""Tests for the Ollama Analyzer backend (issue #15). No live Ollama required."""

from __future__ import annotations

import urllib.error

import pytest

from compiler.analyzer.backend import (
    AnalyzerBackend,
    BackendResponseError,
    BackendTimeoutError,
    BackendUnavailableError,
    OllamaBackend,
)
from compiler.common.config import Config
from compiler.common.result import Severity


def make_backend(transport) -> OllamaBackend:
    return OllamaBackend(model="llama3", temperature=0.0, timeout=60, transport=transport)


# --- interface -------------------------------------------------------------


def test_ollama_backend_implements_interface() -> None:
    backend = make_backend(lambda url, payload, timeout: {"response": "x"})
    assert isinstance(backend, AnalyzerBackend)


def test_from_config_uses_analyzer_section() -> None:
    config = Config.from_json({"analyzer": {"model": "mistral", "temperature": 0.0, "timeout": 30}})
    backend = OllamaBackend.from_config(config, transport=lambda u, p, t: {"response": "x"})
    result = backend.generate("hello")
    assert result.model == "mistral"


# --- success ---------------------------------------------------------------


def test_successful_generate_returns_text_and_telemetry() -> None:
    captured = {}

    def transport(url, payload, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {"response": '{"characters": []}'}

    result = make_backend(transport).generate("A blonde girl in a red dress.")
    assert result.text == '{"characters": []}'
    assert result.model == "llama3"
    assert result.duration_seconds >= 0
    # Prompt is sent unmodified, with the configured model/temperature/timeout.
    assert captured["payload"]["prompt"] == "A blonde girl in a red dress."
    assert captured["payload"]["model"] == "llama3"
    assert captured["payload"]["options"]["temperature"] == pytest.approx(0.0)
    assert captured["payload"]["stream"] is False
    assert captured["timeout"] == 60
    assert captured["url"].endswith("/api/generate")


# --- failure modes ---------------------------------------------------------


def test_timeout_maps_to_sc0013() -> None:
    def transport(url, payload, timeout):
        raise TimeoutError("timed out")

    backend = make_backend(transport)
    with pytest.raises(BackendTimeoutError) as exc:
        backend.generate("hi")
    assert exc.value.code == "SC0013"
    assert exc.value.to_message().code == "SC0013"


def test_connection_failure_maps_to_sc0012_fatal() -> None:
    def transport(url, payload, timeout):
        raise ConnectionError("refused")

    backend = make_backend(transport)
    with pytest.raises(BackendUnavailableError) as exc:
        backend.generate("hi")
    assert exc.value.code == "SC0012"
    assert exc.value.to_message().severity is Severity.FATAL


def test_urlerror_maps_to_connection_failure() -> None:
    def transport(url, payload, timeout):
        raise urllib.error.URLError("no route")

    backend = make_backend(transport)
    with pytest.raises(BackendUnavailableError):
        backend.generate("hi")


def test_http_error_maps_to_sc0018() -> None:
    def transport(url, payload, timeout):
        raise urllib.error.HTTPError(url, 500, "server error", hdrs=None, fp=None)

    backend = make_backend(transport)
    with pytest.raises(BackendResponseError) as exc:
        backend.generate("hi")
    assert exc.value.code == "SC0018"


def test_missing_response_field_maps_to_sc0018() -> None:
    def transport(url, payload, timeout):
        return {"unexpected": "shape"}

    backend = make_backend(transport)
    with pytest.raises(BackendResponseError) as exc:
        backend.generate("hi")
    assert exc.value.code == "SC0018"


def test_non_dict_response_maps_to_sc0018() -> None:
    def transport(url, payload, timeout):
        return "not a dict"

    backend = make_backend(transport)
    with pytest.raises(BackendResponseError):
        backend.generate("hi")
