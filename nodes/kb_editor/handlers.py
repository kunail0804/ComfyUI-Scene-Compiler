"""Transport-independent KB Editor request handlers (issues #123, #125).

Each handler is a pure function ``(kb_dir, ...) -> (status_code, payload)`` so it
can be unit-tested without a running ComfyUI/aiohttp server (acceptance for #123).
The aiohttp routes in :mod:`nodes.kb_editor.routes` are thin adapters over these.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import service


def api_list(kb_dir: str | Path) -> tuple[int, dict[str, Any]]:
    return 200, {"entries": service.list_entries(kb_dir)}


def api_get(kb_dir: str | Path, entry_id: str) -> tuple[int, dict[str, Any]]:
    entry = service.get_entry(kb_dir, entry_id)
    if entry is None:
        return 404, {"error": f"No entry with id '{entry_id}'."}
    return 200, {"entry": entry}


def api_validate(kb_dir: str | Path, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    entry = body.get("entry", {})
    errors = service.validate(kb_dir, entry, body.get("original_id"))
    return 200, {"valid": not errors, "errors": errors}


def _save(kb_dir, entry, original_id) -> tuple[int, dict[str, Any]]:
    try:
        return 200, service.save_entry(kb_dir, entry, original_id)
    except service.ValidationError as error:
        return 400, {"saved": False, "errors": error.errors}


def api_create(kb_dir: str | Path, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return _save(kb_dir, body.get("entry", {}), original_id=None)


def api_update(
    kb_dir: str | Path, entry_id: str, body: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    return _save(kb_dir, body.get("entry", {}), original_id=entry_id)


def api_delete(kb_dir: str | Path, entry_id: str) -> tuple[int, dict[str, Any]]:
    if service.delete_entry(kb_dir, entry_id):
        return 200, {"deleted": True, "id": entry_id}
    return 404, {"deleted": False, "error": f"No entry with id '{entry_id}'."}
