"""JWT and Twynity persona identity helpers.

FastMCP's JWTVerifier protects MCP transport requests. Starlette custom routes
are separate, so they explicitly verify the bearer token against account-service
JWKS here before trusting identity claims.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import httpx
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token, get_http_headers
from jose import JWTError, jwt
from starlette.exceptions import HTTPException
from starlette.requests import Request

from app.config import settings


@dataclass(frozen=True)
class TwynityIdentity:
    user_id: str
    persona_id: str


def get_auth_provider() -> JWTVerifier:
    """Build FastMCP's bearer-token verifier for the MCP transport."""
    jwks_url = (
        f"{settings.ACCOUNT_SERVICE_URL.rstrip('/')}"
        f"/{settings.ACCOUNT_SERVICE_JWKS_ENDPOINT.lstrip('/')}"
    )
    return JWTVerifier(jwks_uri=jwks_url, algorithm="RS256", audience=settings.SERVICE_ID)


async def get_identity(request: Request) -> TwynityIdentity:
    """Verify a request JWT and require its trusted user ID plus Persona-Id.

    Persona identity is request context supplied by Twynity, never a tool
    argument. Missing or invalid identity fails closed.
    """
    return await get_identity_from_headers(request.headers)


async def get_identity_from_headers(headers: Mapping[str, str]) -> TwynityIdentity:
    """Resolve trusted identity from HTTP/MCP headers using the same checks."""
    authorization = headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    persona_id = headers.get(settings.PERSONA_ID_HEADER.lower())
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="A valid Twynity bearer token is required")
    if not persona_id:
        raise HTTPException(
            status_code=400,
            detail=f"Authenticated request is missing the '{settings.PERSONA_ID_HEADER}' header",
        )

    jwks_url = (
        f"{settings.ACCOUNT_SERVICE_URL.rstrip('/')}"
        f"/{settings.ACCOUNT_SERVICE_JWKS_ENDPOINT.lstrip('/')}"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
        header = jwt.get_unverified_header(token)
        key = next(key for key in response.json()["keys"] if key.get("kid") == header.get("kid"))
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=settings.SERVICE_ID
        )
    except (httpx.HTTPError, KeyError, StopIteration, JWTError, ValueError) as exc:
        # Log the real cause (signature, audience, JWKS fetch, or kid lookup)
        # so deployment logs diagnose 401s without guessing. The client only
        # sees the generic message; the detail lives in the server log.
        import logging
        logging.getLogger(__name__).warning(
            "JWT verification failed for kid=%s service=%s: %s: %s",
            jwt.get_unverified_header(token).get("kid") if token else "?",
            settings.SERVICE_ID,
            type(exc).__name__,
            exc,
        )
        raise HTTPException(status_code=401, detail="Twynity bearer token could not be verified") from exc

    user_id = claims.get("id") or claims.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Verified token has no user identity claim")
    return TwynityIdentity(user_id=user_id, persona_id=persona_id)


async def get_identity_from_context() -> TwynityIdentity:
    """Resolve identity from FastMCP's verified request context (MCP transport).

    Use this from MCP *tools* (not custom routes). The transport ``JWTVerifier``
    has already verified the bearer token and published it via
    ``get_access_token()`` — so we read the decoded claims directly instead of
    re-fetching JWKS and re-verifying. That also sidesteps FastMCP stripping the
    ``authorization`` header from ``get_http_headers()`` (which would make a
    header-based re-verification 401 on every tool call).

    ``Persona-Id`` is still read from the request headers (it is *not* among the
    stripped headers), so project scoping works exactly as before. A valid
    token and Persona-Id are both required here (the project model scopes every
    stored connection to a (user_id, persona_id) pair).
    """
    access_token = get_access_token()
    if access_token is None:
        raise HTTPException(status_code=401, detail="A valid Twynity bearer token is required")

    claims = getattr(access_token, "claims", None) or {}
    user_id = claims.get("id") or claims.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Verified token has no user identity claim")

    persona_id = get_http_headers().get(settings.PERSONA_ID_HEADER.lower())
    if not persona_id or not persona_id.strip():
        raise HTTPException(
            status_code=400,
            detail=f"Authenticated request is missing the '{settings.PERSONA_ID_HEADER}' header",
        )
    persona_id = persona_id.strip()
    return TwynityIdentity(user_id=user_id, persona_id=persona_id)
