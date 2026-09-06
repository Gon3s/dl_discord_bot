import logging
from typing import Any

import aiohttp

from domain import Category, MediaTypeInput, ScraperSource

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {500, 502, 503, 504}


class BackendError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


class BackendClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        retries: int = 2,
        **kwargs: Any,
    ) -> Any:
        url = f"{self._base_url}{path}"
        session = await self._get_session()

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status in _RETRY_STATUSES and attempt < retries:
                        logger.warning("Backend %s %s → %s, retry %d", method, path, resp.status, attempt + 1)
                        continue
                    if resp.status >= 400:
                        body = await resp.text()
                        raise BackendError(resp.status, f"HTTP {resp.status}: {body[:200]}")
                    if resp.status == 204:
                        return None
                    return await resp.json()
            except aiohttp.ClientError as exc:
                last_exc = exc
                if attempt < retries:
                    logger.warning("Backend connection error, retry %d: %s", attempt + 1, exc)
                    continue
                raise BackendError(0, f"Connection error: {exc}") from exc

        raise BackendError(0, f"All retries exhausted: {last_exc}")

    # --- Search ---

    async def search(
        self,
        q: str,
        source: ScraperSource = "wawacity",
        category: Category | None = None,
        year: int | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": q, "source": source, "limit": limit}
        if category:
            params["category"] = category
        if year:
            params["year"] = year
        return await self._request("GET", "/api/v1/search", params=params)

    # --- Downloads ---

    async def create_download(
        self,
        source_url: str,
        title: str,
        media_type: MediaTypeInput,
        destination: str = "server",
    ) -> dict[str, Any]:
        payload = {
            "source_url": source_url,
            "title": title,
            "media_type": media_type,
            "destination": destination,
        }
        return await self._request("POST", "/api/v1/downloads", json=payload)

    async def get_downloads(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/v1/downloads")

    # --- Status ---

    async def get_status(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/status")
