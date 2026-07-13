"""aiohttp route registration for the KB Editor (issue #123, #124).

Registers the editor's API and static page on the ComfyUI server sub-route
``/scene-compiler/kb``. Guarded so importing the package without ComfyUI (or
without ``PromptServer``) is a no-op — the compiler and tests never require the
server. The route handlers delegate to the transport-independent functions in
:mod:`nodes.kb_editor.handlers`.
"""

from __future__ import annotations

from pathlib import Path

from . import handlers

_ROUTE = "/scene-compiler/kb"
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_KB_DIR = _PACKAGE_ROOT / "knowledge_base"
_WEB_INDEX = Path(__file__).resolve().parent / "web" / "index.html"


def register_routes(kb_dir: str | Path | None = None) -> bool:
    """Register the editor routes on the ComfyUI PromptServer. Return True on success.

    A no-op returning False when ComfyUI/aiohttp/PromptServer is unavailable, so the
    package stays import-safe outside ComfyUI.
    """
    try:
        from aiohttp import web
        from server import PromptServer
    except Exception:
        return False

    kb_dir = Path(kb_dir) if kb_dir is not None else _DEFAULT_KB_DIR
    routes = PromptServer.instance.routes

    @routes.get(_ROUTE)
    async def _page(_request):
        if not _WEB_INDEX.is_file():
            return web.Response(status=404, text="KB editor page not found.")
        return web.FileResponse(_WEB_INDEX)

    @routes.get(_ROUTE + "/api/entries")
    async def _list(_request):
        status, payload = handlers.api_list(kb_dir)
        return web.json_response(payload, status=status)

    @routes.get(_ROUTE + "/api/entries/{entry_id}")
    async def _get(request):
        status, payload = handlers.api_get(kb_dir, request.match_info["entry_id"])
        return web.json_response(payload, status=status)

    @routes.post(_ROUTE + "/api/entries")
    async def _create(request):
        status, payload = handlers.api_create(kb_dir, await request.json())
        return web.json_response(payload, status=status)

    @routes.put(_ROUTE + "/api/entries/{entry_id}")
    async def _update(request):
        status, payload = handlers.api_update(
            kb_dir, request.match_info["entry_id"], await request.json()
        )
        return web.json_response(payload, status=status)

    @routes.delete(_ROUTE + "/api/entries/{entry_id}")
    async def _delete(request):
        status, payload = handlers.api_delete(kb_dir, request.match_info["entry_id"])
        return web.json_response(payload, status=status)

    @routes.post(_ROUTE + "/api/validate")
    async def _validate(request):
        status, payload = handlers.api_validate(kb_dir, await request.json())
        return web.json_response(payload, status=status)

    return True
