import aiohttp

from app.config import settings
from app.core.exceptions import AllDebridAPIError, AllDebridHTTPError

_BASE_URL = "https://api.alldebrid.com/v4"
_AGENT = "AlldebridBot"


class AllDebridClient:
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
                async with session.get(
                    f"{_BASE_URL}/user", params=params
                ) as response:
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
