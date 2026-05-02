import aiohttp

from app.config import settings
from app.core.exceptions import DebridAPIError, DebridHTTPError

_BASE_URL = "https://api.real-debrid.com/rest/1.0"


class RealDebridClient:
    name = "realdebrid"
    display_name = "Real-Debrid"

    def __init__(self) -> None:
        self._api_token = settings.realdebrid_api_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    async def _json_response(self, response: aiohttp.ClientResponse) -> dict:
        if response.status in {200, 201}:
            return await response.json()
        if response.status == 204:
            return {}

        try:
            data = await response.json()
        except Exception:
            raise DebridHTTPError(response.status) from None

        message = data.get("error") or f"HTTP error {response.status}"
        code = data.get("error_code")
        raise DebridAPIError(str(message), str(code) if code is not None else None)

    async def ping(self) -> bool:
        """Return True if the Real-Debrid API is reachable and the token is valid."""
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.get(f"{_BASE_URL}/user") as response:
                    return response.status == 200
        except Exception:
            return False

    async def debrid_link(self, url: str) -> dict:
        """Unrestrict a hoster link and map Real-Debrid output to the common shape."""
        async with aiohttp.ClientSession(headers=self._headers()) as session:
            async with session.post(
                f"{_BASE_URL}/unrestrict/link", data={"link": url}
            ) as response:
                data = await self._json_response(response)

        if isinstance(data, list):
            data = data[0] if data else {}

        direct_url = data.get("download")
        if direct_url:
            data["link"] = direct_url
        return data

    async def upload_magnet(self, magnet: str) -> str:
        """Upload a magnet link to Real-Debrid and return its torrent ID."""
        async with aiohttp.ClientSession(headers=self._headers()) as session:
            async with session.post(
                f"{_BASE_URL}/torrents/addMagnet", data={"magnet": magnet}
            ) as response:
                data = await self._json_response(response)

        torrent_id = data.get("id")
        if torrent_id is None:
            raise DebridAPIError("Real-Debrid returned no torrent ID")
        return str(torrent_id)

    async def get_magnet_status(self, magnet_id: int | str) -> dict:
        """Return torrent info, selecting the largest file when RD asks for it."""
        info = await self._torrent_info(magnet_id)
        if info.get("status") == "waiting_files_selection":
            file_ids = self._largest_file_ids(info)
            if not file_ids:
                raise DebridAPIError("Real-Debrid returned no selectable torrent files")
            await self._select_files(magnet_id, ",".join(file_ids))
            info = await self._torrent_info(magnet_id)
        return info

    async def get_magnet_files(self, magnet_id: int | str) -> list[str]:
        """Return unrestricted torrent links, largest selected file first."""
        info = await self._torrent_info(magnet_id)
        links = info.get("links") or []
        if not isinstance(links, list):
            return []

        direct_links: list[str] = []
        for link in links:
            data = await self.debrid_link(str(link))
            direct_url = data.get("link")
            if direct_url:
                direct_links.append(str(direct_url))
        return direct_links

    async def _torrent_info(self, magnet_id: int | str) -> dict:
        async with aiohttp.ClientSession(headers=self._headers()) as session:
            async with session.get(
                f"{_BASE_URL}/torrents/info/{magnet_id}"
            ) as response:
                return await self._json_response(response)

    async def _select_files(self, magnet_id: int | str, files: str) -> None:
        async with aiohttp.ClientSession(headers=self._headers()) as session:
            async with session.post(
                f"{_BASE_URL}/torrents/selectFiles/{magnet_id}",
                data={"files": files},
            ) as response:
                await self._json_response(response)

    def _largest_file_ids(self, info: dict) -> list[str]:
        files = info.get("files")
        if not isinstance(files, list):
            return []

        candidates: list[tuple[int, str]] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            file_id = item.get("id")
            if file_id is None:
                continue
            try:
                size = int(item.get("bytes") or 0)
            except (TypeError, ValueError):
                size = 0
            candidates.append((size, str(file_id)))

        if not candidates:
            return []
        candidates.sort(reverse=True)
        return [candidates[0][1]]
