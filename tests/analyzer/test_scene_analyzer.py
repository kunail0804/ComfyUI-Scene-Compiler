"""Tests for the Scene Analyzer retry orchestration (issue #18, §12.9, §12.10)."""

from __future__ import annotations

import json

import pytest

from compiler.analyzer.backend import (
    BackendResult,
    BackendTimeoutError,
    BackendUnavailableError,
)
from compiler.analyzer.scene_analyzer import analyze
from compiler.common.config import Config
from schemas.models import Scene


def valid_scene_text() -> str:
    return json.dumps(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": ["female"],
                    "appearance": [],
                    "clothing": [],
                    "accessories": [],
                    "pose": [],
                    "expression": [],
                    "actions": [],
                }
            ],
            "interactions": [],
            "objects": [],
            "environment": [],
            "camera": [],
            "lighting": [],
            "metadata": {},
        }
    )


class FakeBackend:
    """A scripted backend: each item is a response string or an exception to raise."""

    def __init__(self, script: list) -> None:
        self._script = list(script)
        self.calls = 0
        self.prompts: list[str] = []
        self.temperatures: list[float | None] = []

    def generate(self, prompt: str, *, temperature: float | None = None) -> BackendResult:
        self.calls += 1
        self.prompts.append(prompt)
        self.temperatures.append(temperature)
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return BackendResult(text=item, model="llama3", duration_seconds=0.01)


def codes(messages) -> list[str]:
    return [m.code for m in messages]


def config(max_retries: int = 3) -> Config:
    return Config.from_json({"analyzer": {"max_retries": max_retries}})


# --- success ---------------------------------------------------------------


def test_first_attempt_success() -> None:
    backend = FakeBackend([valid_scene_text()])
    result = analyze("A girl.", backend, config())
    assert result.success
    assert isinstance(result.data, Scene)
    assert backend.calls == 1


def test_succeeds_on_retry() -> None:
    backend = FakeBackend(["not json", valid_scene_text()])
    result = analyze("A girl.", backend, config())
    assert result.success
    assert backend.calls == 2


def test_prompt_is_reused_unchanged_across_retries() -> None:
    backend = FakeBackend(["not json", "still not json", valid_scene_text()])
    analyze("A girl.", backend, config())
    assert len(set(backend.prompts)) == 1  # identical prompt every attempt


def test_temperature_escalates_on_retries_only() -> None:
    # First attempt at the base temperature (deterministic), retries escalate so a
    # bad-JSON run can self-recover without a manual re-run.
    backend = FakeBackend(["not json", "still not json", valid_scene_text()])
    analyze("A girl.", backend, config())
    assert backend.temperatures == pytest.approx([0.0, 0.2, 0.4])


def test_temperature_escalation_builds_on_configured_base() -> None:
    backend = FakeBackend(["bad", valid_scene_text()])
    cfg = Config.from_json({"analyzer": {"temperature": 0.5}})
    analyze("A girl.", backend, cfg)
    assert backend.temperatures == pytest.approx([0.5, 0.7])


def test_temperature_is_capped() -> None:
    backend = FakeBackend(["bad"] * 10)
    cfg = Config.from_json({"analyzer": {"temperature": 0.9, "max_retries": 5}})
    analyze("A girl.", backend, cfg)
    assert max(backend.temperatures) <= 1.0
    assert backend.temperatures[-1] == pytest.approx(1.0)  # escalation is clamped at the cap


def test_prompt_includes_system_prompt_and_description() -> None:
    backend = FakeBackend([valid_scene_text()])
    analyze("A blonde girl.", backend, config())
    sent = backend.prompts[0]
    assert "Scene Analyzer" in sent  # system prompt
    assert "A blonde girl." in sent  # user description


# --- bounded retries -------------------------------------------------------


def test_exhausts_retries_then_sc0011() -> None:
    backend = FakeBackend(["bad"] * 10)
    result = analyze("A girl.", backend, config(max_retries=3))
    assert not result.success
    assert "SC0011" in codes(result.errors)
    assert backend.calls == 4  # 1 initial + 3 retries


def test_zero_retries_means_single_attempt() -> None:
    backend = FakeBackend(["bad", valid_scene_text()])
    result = analyze("A girl.", backend, config(max_retries=0))
    assert not result.success
    assert backend.calls == 1


# --- terminal failures -----------------------------------------------------


def test_connection_failure_is_fatal_sc0012_no_retry() -> None:
    backend = FakeBackend([BackendUnavailableError("refused")])
    result = analyze("A girl.", backend, config())
    assert not result.success
    assert "SC0012" in codes(result.errors)
    assert backend.calls == 1  # not retried


def test_timeout_is_sc0013_no_retry() -> None:
    backend = FakeBackend([BackendTimeoutError("timed out")])
    result = analyze("A girl.", backend, config())
    assert not result.success
    assert "SC0013" in codes(result.errors)
    assert backend.calls == 1


# --- telemetry -------------------------------------------------------------


def test_metadata_reports_attempts() -> None:
    backend = FakeBackend(["bad", valid_scene_text()])
    result = analyze("A girl.", backend, config())
    assert result.metadata["attempts"] == 2
    assert result.metadata["retries"] == 1


def test_raw_response_captured_on_success() -> None:
    text = valid_scene_text()
    backend = FakeBackend([text])
    result = analyze("A girl.", backend, config())
    assert result.metadata["raw_response"] == text


def test_raw_response_captures_last_failed_text() -> None:
    # On exhaustion the raw model text of the last attempt is surfaced so the
    # failure is debuggable even though no Scene was produced.
    backend = FakeBackend(["garbage output"] * 10)
    result = analyze("A girl.", backend, config(max_retries=1))
    assert not result.success
    assert result.metadata["raw_response"] == "garbage output"


def test_raw_response_empty_on_terminal_backend_error() -> None:
    backend = FakeBackend([BackendTimeoutError("timed out")])
    result = analyze("A girl.", backend, config())
    assert result.metadata["raw_response"] == ""
