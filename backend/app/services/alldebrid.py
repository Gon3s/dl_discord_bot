import aiohttp

from app.config import settings
from app.core.exceptions import AllDebridAPIError, AllDebridHTTPError
from app.models.domain import DebridProvider

_BASE_URL = "https://api.alldebrid.com/v4"
_AGENT = "AlldebridBot"


class AllDebridClient:
    name = DebridProvider.ALLDEBRID
    display_name = "AllDebrid"

    def __init__(self) -> None:
        self._api_key = settings.alldebrid_api_key

    def _base_params(self) -> dict[str, str]:
        return {"agent": _AGENT, "apikey": self._api_key}

    async def redirect_link(self, url: str) -> str:
        """Resolve a redirect/protection link and return the direct URL."""
        params = {**self._base_params(), "link": url}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_BASE_URL}/link/redirector", params=params
            ) as response:
                if response.status != 200:
                    raise AllDebridHTTPError(response.status)
                data = await response.json()

        if data["status"] == "error":
            error = data.get("error", {})
            raise AllDebridAPIError(
                error.get("message", "Unknown error"), error.get("code")
            )

        return data["data"]["links"][0]

    async def ping(self) -> bool:
        """Return True if the AllDebrid API is reachable and the key is valid."""
        params = {**self._base_params()}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{_BASE_URL}/user", params=params) as response:
                    if response.status != 200:
                        return False
                    data = await response.json()
            return data.get("status") == "success"
        except Exception:
            return False

    async def debrid_link(self, url: str) -> dict:
        """Unlock a link via AllDebrid and return the unlock data."""
        params = {**self._base_params(), "link": url}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_BASE_URL}/link/unlock", params=params
            ) as response:
                if response.status != 200:
                    raise AllDebridHTTPError(response.status)
                data = await response.json()

        if data["status"] == "error":
            error = data.get("error", {})
            raise AllDebridAPIError(
                error.get("message", "Unknown error"), error.get("code")
            )

        return data["data"]

    async def upload_magnet(self, magnet: str) -> int:
        """Upload a magnet link to AllDebrid and return its magnet ID."""
        params = self._base_params()
        form = {"magnets[]": magnet}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_BASE_URL}/magnet/upload", params=params, data=form
            ) as response:
                if response.status != 200:
                    raise AllDebridHTTPError(response.status)
                data = await response.json()

        if data["status"] == "error":
            error = data.get("error", {})
            raise AllDebridAPIError(
                error.get("message", "Unknown error"), error.get("code")
            )

        magnet_data = data.get("data", {})
        candidates = magnet_data.get("magnets") or magnet_data.get("magnet") or []
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
        elif isinstance(candidates, dict):
            first = candidates
        else:
            first = magnet_data

        magnet_id = first.get("id") or first.get("magnet_id") or first.get("magnetId")
        if magnet_id is None:
            raise AllDebridAPIError("AllDebrid returned no magnet ID")
        return int(magnet_id)

    async def get_magnet_status(self, magnet_id: int) -> dict:
        """Return the raw AllDebrid status payload for a magnet."""
        params = {**self._base_params(), "id": str(magnet_id)}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_BASE_URL}/magnet/status", params=params
            ) as response:
                if response.status != 200:
                    raise AllDebridHTTPError(response.status)
                data = await response.json()

        if data["status"] == "error":
            error = data.get("error", {})
            raise AllDebridAPIError(
                error.get("message", "Unknown error"), error.get("code")
            )

        return data.get("data", {})

    async def get_magnet_files(self, magnet_id: int) -> list[str]:
        """Return unlocked AllDebrid file links for a magnet, largest first."""
        params = {**self._base_params(), "id": str(magnet_id)}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_BASE_URL}/magnet/files", params=params
            ) as response:
                if response.status != 200:
                    raise AllDebridHTTPError(response.status)
                data = await response.json()

        if data["status"] == "error":
            error = data.get("error", {})
            raise AllDebridAPIError(
                error.get("message", "Unknown error"), error.get("code")
            )

        return self._extract_file_links(data.get("data", {}))

    def _extract_file_links(self, payload: dict) -> list[str]:
        files = payload.get("files")
        if files is None:
            magnets = payload.get("magnets") or payload.get("magnet") or []
            if isinstance(magnets, list) and magnets:
                files = magnets[0].get("files")
            elif isinstance(magnets, dict):
                files = magnets.get("files")
        if not isinstance(files, list):
            return []

        candidates: list[tuple[int, str]] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            link = item.get("link") or item.get("url")
            links = item.get("links")
            if link is None and isinstance(links, list) and links:
                link = links[0]
            if not link:
                continue
            try:
                size = int(item.get("size") or item.get("bytes") or 0)
            except (TypeError, ValueError):
                size = 0
            candidates.append((size, str(link)))

        candidates.sort(reverse=True)
        return [link for _, link in candidates]
