from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DebridAPIError
from app.services.realdebrid import RealDebridClient


def _mock_response(status: int, json_data: dict | list | None = None) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data if json_data is not None else {})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _mock_session(
    get_response: MagicMock | None = None,
    post_response: MagicMock | None = None,
) -> MagicMock:
    session = MagicMock()
    session.get = MagicMock(return_value=get_response)
    session.post = MagicMock(return_value=post_response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def client() -> RealDebridClient:
    return RealDebridClient()


class TestPing:
    async def test_returns_true_when_user_endpoint_accepts_token(
        self, client: RealDebridClient
    ) -> None:
        session = _mock_session(get_response=_mock_response(200, {"id": 1}))

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.ping()

        assert result is True

    async def test_returns_false_on_http_error(self, client: RealDebridClient) -> None:
        session = _mock_session(
            get_response=_mock_response(401, {"error": "Bad token"})
        )

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.ping()

        assert result is False


class TestDebridLink:
    async def test_maps_download_to_common_link(self, client: RealDebridClient) -> None:
        payload = {
            "id": "abc",
            "filename": "file.mkv",
            "download": "https://rd.example.com/file.mkv",
        }
        session = _mock_session(post_response=_mock_response(200, payload))

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.debrid_link("https://1fichier.com/?abc")

        assert result["link"] == "https://rd.example.com/file.mkv"
        assert result["filename"] == "file.mkv"

    async def test_raises_readable_api_error(self, client: RealDebridClient) -> None:
        session = _mock_session(
            post_response=_mock_response(
                503, {"error": "File unavailable", "error_code": 8}
            )
        )

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession", return_value=session
        ):
            with pytest.raises(DebridAPIError) as exc_info:
                await client.debrid_link("https://1fichier.com/?abc")

        assert "File unavailable" in str(exc_info.value)
        assert exc_info.value.code == "8"


class TestMagnets:
    async def test_upload_magnet_returns_torrent_id(
        self, client: RealDebridClient
    ) -> None:
        session = _mock_session(
            post_response=_mock_response(201, {"id": "torrent-123"})
        )

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.upload_magnet("magnet:?xt=urn:btih:ABC")

        assert result == "torrent-123"

    async def test_status_selects_largest_file_when_waiting_for_selection(
        self, client: RealDebridClient
    ) -> None:
        first_info = {
            "id": "torrent-123",
            "status": "waiting_files_selection",
            "files": [
                {"id": 1, "path": "/sample.mkv", "bytes": 10},
                {"id": 2, "path": "/movie.mkv", "bytes": 1000},
            ],
        }
        selected_info = {
            "id": "torrent-123",
            "status": "downloaded",
            "files": [{"id": 2, "path": "/movie.mkv", "bytes": 1000, "selected": 1}],
            "links": ["https://host.example.com/movie"],
        }
        select_response = _mock_response(204)
        select_session = _mock_session(post_response=select_response)

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession",
            side_effect=[
                _mock_session(get_response=_mock_response(200, first_info)),
                select_session,
                _mock_session(get_response=_mock_response(200, selected_info)),
            ],
        ):
            result = await client.get_magnet_status("torrent-123")

        assert result["status"] == "downloaded"
        select_session.post.assert_called_once()
        assert select_session.post.call_args.kwargs["data"] == {"files": "2"}

    async def test_get_magnet_files_unrestricts_torrent_links(
        self, client: RealDebridClient
    ) -> None:
        info = {
            "id": "torrent-123",
            "status": "downloaded",
            "links": ["https://host.example.com/movie"],
        }
        unrestricted = {
            "filename": "movie.mkv",
            "download": "https://rd.example.com/movie.mkv",
        }

        with patch(
            "app.services.realdebrid.aiohttp.ClientSession",
            side_effect=[
                _mock_session(get_response=_mock_response(200, info)),
                _mock_session(post_response=_mock_response(200, unrestricted)),
            ],
        ):
            result = await client.get_magnet_files("torrent-123")

        assert result == ["https://rd.example.com/movie.mkv"]
