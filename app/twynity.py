"""Twynity discovery + API-key external-connection routes (Interconnector §10.2).

The API-key category requires:
  POST /api/v1/keys                  — store {name, key} for the auth'd user
  GET  /api/v1/keys                  — list stored keys (name only, never the key)
  GET  /api/v1/external-connection/me — connection status
  GET  /api/v1/.well-known/mcp.json  — manifest declaring external_connections.api_key
  GET  /api/v1/health                — liveness

The active user/persona comes only from the authenticated Twynity JWT + the
``Persona-Id`` request header. These routes verify JWTs explicitly because
FastMCP's auth provider does not automatically secure Starlette custom routes.
"""

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth import get_identity
from app.config import settings
from app.connection_store import get_active_store


def register_routes(mcp):
    @mcp.custom_route("/api/v1/.well-known/mcp.json", methods=["GET"])
    async def manifest(request: Request) -> JSONResponse:
        return JSONResponse({
            "name": settings.APP_TITLE,
            "base_url": f"{settings.PUBLIC_URL.rstrip('/')}/mcp",
            "version": settings.APP_VERSION,
            # §10.6 — declare only the categories this MCP implements.
            "external_connections": {
                "api_key": {"name": "service_api_key"},
                "oauth": None,
                "project": None,
            },
        })

    @mcp.custom_route("/api/v1/keys", methods=["OPTIONS"])
    async def keys_options(request: Request) -> JSONResponse:
        return JSONResponse({}, headers={"Allow": "GET, POST, OPTIONS"})

    @mcp.custom_route("/api/v1/keys", methods=["POST"])
    async def save_key(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError):
            return JSONResponse({"detail": "Request body must be valid JSON"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"detail": {"missing_or_invalid_fields": ["name", "key"]}}, status_code=422)
        name = str(payload.get("name", "")).strip()
        key = str(payload.get("key", "")).strip()
        invalid = [f for f, v in (("name", name), ("key", key)) if not v]
        if invalid:
            return JSONResponse({"detail": {"missing_or_invalid_fields": invalid}}, status_code=422)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="Key storage is not available")
        await store.save(identity.user_id, identity.persona_id, name, key)
        return JSONResponse({"configured": True})

    @mcp.custom_route("/api/v1/keys", methods=["GET"])
    async def list_keys(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="Key storage is not available")
        # public_metadata returns only the non-secret name — never the key.
        metadata = await store.public_metadata(identity.user_id, identity.persona_id)
        items = [metadata] if metadata else []
        return JSONResponse({"items": items, "item_count": len(items), "next_cursor": None})

    @mcp.custom_route("/api/v1/external-connection/me", methods=["GET"])
    async def external_connection_me(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="Key storage is not available")
        connected = await store.public_metadata(identity.user_id, identity.persona_id) is not None
        return JSONResponse({"connected": connected})

    @mcp.custom_route("/api/v1/health", methods=["GET"])
    async def health_status(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})
