"""Knowledge Base Editor service logic (issues #123, #125, #126).

ComfyUI-independent: pure functions over a Knowledge Base directory, so the route
handlers stay thin and the logic is unit-testable without a running server. The
editor operates on the **curated** files only (the hand-editable surface); the
generated ``gen_*.json`` files and the ``manifest.json`` are read for validation
context but never written here.

Validation reuses the authoritative rules in
:mod:`compiler.common.kb_validation` — there is a single source of truth. Saves
are **atomic** (temp file + fsync + rename) and **format-safe**: the on-disk shape
(one entry per line, stable key order, trailing newline) is preserved and only the
edited entry changes.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from compiler.common.kb_validation import validate_cross_entry, validate_entry

_MANIFEST = "manifest.json"
_GEN_PREFIX = "gen_"

# Canonical key order for an editor-written entry (matches the curated files).
_KEY_ORDER = ("id", "aliases", "tags", "category", "expand", "rating", "deprecated", "notes")


class ValidationError(Exception):
    """Raised when a save is rejected; carries per-field validation errors."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors


def _curated_files(kb_dir: Path) -> list[Path]:
    return [
        p
        for p in sorted(kb_dir.glob("*.json"))
        if p.name != _MANIFEST and not p.name.startswith(_GEN_PREFIX)
    ]


def _all_files(kb_dir: Path) -> list[Path]:
    return [p for p in sorted(kb_dir.glob("*.json")) if p.name != _MANIFEST]


def _read(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_entries(kb_dir: str | Path) -> list[dict]:
    """Return all curated entries, sorted by id."""
    kb_dir = Path(kb_dir)
    entries = [entry for path in _curated_files(kb_dir) for entry in _read(path)]
    return sorted(entries, key=lambda e: e.get("id", ""))


def get_entry(kb_dir: str | Path, entry_id: str) -> dict | None:
    """Return the curated entry with ``entry_id``, or None."""
    for entry in list_entries(kb_dir):
        if entry.get("id") == entry_id:
            return entry
    return None


def _find_curated_file(kb_dir: Path, entry_id: str) -> Path | None:
    for path in _curated_files(kb_dir):
        if any(entry.get("id") == entry_id for entry in _read(path)):
            return path
    return None


def _all_entries_with(
    kb_dir: Path, entry: Mapping[str, Any], original_id: str | None
) -> list[dict]:
    """The whole KB state with ``entry`` applied.

    On update (``original_id`` given) the matching entry is replaced; on create
    (``original_id`` is None) the entry is appended, so a colliding id surfaces as
    a duplicate rather than silently overwriting the existing entry.
    """
    merged: list[dict] = []
    replaced = False
    for path in _all_files(kb_dir):
        for existing in _read(path):
            if original_id is not None and existing.get("id") == original_id:
                merged.append(dict(entry))
                replaced = True
            else:
                merged.append(existing)
    if not replaced:
        merged.append(dict(entry))
    return merged


def _field_for(message) -> str:
    """Map a validation message to the entry field it concerns (for the UI)."""
    context = message.context
    if context.get("path"):
        return str(context["path"]).split("/")[0]
    if context.get("alias") is not None:
        return "aliases"
    if context.get("category") is not None:
        return "category"
    if context.get("target") is not None or context.get("cycle") is not None:
        return "expand"
    return "id"


def validate(
    kb_dir: str | Path, entry: Mapping[str, Any], original_id: str | None = None
) -> list[dict[str, Any]]:
    """Validate a candidate entry against its own schema and the resulting KB state.

    Returns a list of ``{"field", "code", "message"}`` errors (empty when valid).
    """
    kb_dir = Path(kb_dir)
    messages = list(validate_entry(entry))
    # Only run cross-entry checks when the entry itself is structurally sound, so a
    # malformed id/category does not produce confusing collision noise.
    if not messages:
        messages += validate_cross_entry(_all_entries_with(kb_dir, entry, original_id))
    return [{"field": _field_for(m), "code": m.code, "message": m.description} for m in messages]


def _ordered(entry: Mapping[str, Any]) -> dict:
    """Return the entry with keys in the canonical curated order (present keys only)."""
    ordered = {key: entry[key] for key in _KEY_ORDER if key in entry}
    # Preserve any unexpected keys deterministically at the end (schema rejects them,
    # but keep them visible rather than dropping silently).
    ordered.update({k: v for k, v in entry.items() if k not in ordered})
    return ordered


def _entry_line(entry: Mapping[str, Any]) -> str:
    body = ", ".join(
        f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in entry.items()
    )
    return "{ " + body + " }"


def _dump_curated(entries: list[dict]) -> str:
    """Serialize entries one-per-line, matching the curated on-disk format."""
    if not entries:
        return "[]\n"
    lines = ",\n".join("  " + _entry_line(entry) for entry in entries)
    return "[\n" + lines + "\n]\n"


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp file + fsync + rename)."""
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)  # atomic on POSIX and Windows
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def save_entry(
    kb_dir: str | Path, entry: Mapping[str, Any], original_id: str | None = None
) -> dict[str, Any]:
    """Validate then atomically save a curated entry. Raise ValidationError if invalid.

    Updates the file the entry currently lives in; a new entry goes to
    ``<category>.json`` (created if needed). Only the edited entry changes.
    """
    kb_dir = Path(kb_dir)
    errors = validate(kb_dir, entry, original_id)
    if errors:
        raise ValidationError(errors)

    entry = _ordered(entry)
    entry_id = entry["id"]
    lookup_id = original_id if original_id is not None else entry_id
    target = _find_curated_file(kb_dir, lookup_id)
    if target is None:
        target = kb_dir / f"{entry['category']}.json"

    entries = _read(target) if target.exists() else []
    updated = False
    for index, existing in enumerate(entries):
        if existing.get("id") == lookup_id:
            entries[index] = entry
            updated = True
            break
    if not updated:
        entries.append(entry)

    _atomic_write(target, _dump_curated(entries))
    return {"saved": True, "id": entry_id, "file": target.name, "created": not updated}


def delete_entry(kb_dir: str | Path, entry_id: str) -> bool:
    """Delete a curated entry; return True if it existed."""
    kb_dir = Path(kb_dir)
    target = _find_curated_file(kb_dir, entry_id)
    if target is None:
        return False
    entries = [entry for entry in _read(target) if entry.get("id") != entry_id]
    _atomic_write(target, _dump_curated(entries))
    return True
