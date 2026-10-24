from __future__ import annotations

import os
import secrets
from collections.abc import Callable

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

PUBLIC_EXACT_PATHS = frozenset({
    "/healthz",
    "/install.sh",
    "/bin/vox-speak",
})


def resolve_api_key_from_env(env_var: str = "VOX_API_KEY") -> str | None:
    raw = os.environ.get(env_var)
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


def extract_bearer_token(value: str | None) -> str | None:
    if value is None:
        return None
    parts = value.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def is_public_request(method: str, path: str) -> bool:
    if method.upper() not in {"GET", "HEAD"}:
        return False

    normalized = path if path == "/" else path.rstrip("/")
    if normalized in PUBLIC_EXACT_PATHS:
        return True
    return normalized.startswith("/audio/") and normalized.endswith(".ogg")


def headers_have_valid_api_key(headers: Headers, expected_key: str) -> bool:
    bearer_token = extract_bearer_token(headers.get("authorization"))
    if bearer_token and secrets.compare_digest(bearer_token, expected_key):
        return True

    x_api_key = headers.get("x-api-key")
    if x_api_key is None:
        return False
    candidate = x_api_key.strip()
    return bool(candidate) and secrets.compare_digest(candidate, expected_key)


class ApiKeyAuthMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        api_key_resolver: Callable[[], str | None] = resolve_api_key_from_env,
    ) -> None:
        self.app = app
        self._api_key_resolver = api_key_resolver

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        api_key = self._api_key_resolver()
        method = str(scope.get("method", "GET"))
        path = str(scope.get("path", "/"))
        if api_key is None or is_public_request(method, path):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if headers_have_valid_api_key(headers, api_key):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
            headers={"WWW-Authenticate": "Bear" + "er"},
        )
        await response(scope, receive, send)
