"""Shared HTTP client construction and retry policy for registry clients."""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from aml_poland_mcp.config import Settings

USER_AGENT = "aml-poland-mcp/0.1 (+https://github.com/Ustingit/Ustin.Integrations.AML.Poland.Mcp)"


def build_client(settings: Settings, *, headers: dict[str, str] | None = None, **kwargs: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        **kwargs,
    )


async def request_with_retry(
    client: httpx.AsyncClient,
    settings: Settings,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Retry transient network failures (not HTTP error status codes) with backoff."""
    async for attempt in AsyncRetrying(
        reraise=True,
        stop=stop_after_attempt(settings.http_max_retries),
        wait=wait_exponential(multiplier=0.5, max=5),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)
        ),
    ):
        with attempt:
            return await client.request(method, url, **kwargs)
    raise AssertionError("unreachable: AsyncRetrying always returns or raises")
