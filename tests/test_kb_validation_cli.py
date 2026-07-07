"""Tests for the Knowledge Base validation CLI (issue #9)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "validate_knowledge_base.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("kb_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_cli_passes_on_valid_kb(tmp_path, capsys) -> None:
    (tmp_path / "hair.json").write_text(
        json.dumps([{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]),
        encoding="utf-8",
    )
    exit_code = _load_cli().main([str(tmp_path)])
    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["valid"] is True
    assert report["entry_count"] == 1


def test_cli_fails_on_invalid_kb(tmp_path, capsys) -> None:
    (tmp_path / "bad.json").write_text(
        json.dumps([{"id": "x", "tags": ["x"], "category": "nope"}]),
        encoding="utf-8",
    )
    exit_code = _load_cli().main([str(tmp_path)])
    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["valid"] is False
    assert any(f["code"] == "SC0008" for f in report["findings"])


def test_cli_reports_invalid_json(tmp_path, capsys) -> None:
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    exit_code = _load_cli().main([str(tmp_path)])
    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert any(f["code"] == "SC0004" for f in report["findings"])
