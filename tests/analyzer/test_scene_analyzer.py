"""Tests for the Scene Analyzer retry orchestration (issue #18, §12.9, §12.10)."""

from __future__ import annotations

import json

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

    def generate(self, prompt: str) -> BackendResult:
        self.calls += 1
        self.prompts.append(prompt)
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
