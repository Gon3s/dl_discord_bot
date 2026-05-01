from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AllDebridAPIError, AllDebridHTTPError
from app.services.alldebrid import AllDebridClient


def _mock_response(status: int, json_data: dict) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _mock_session(response: MagicMock) -> MagicMock:
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    session.post = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def client():
    return AllDebridClient()


class TestRedirectLink:
    async def test_returns_direct_url(self, client: AllDebridClient) -> None:
        payload = {
            "status": "success",
            "data": {"links": ["https://direct.example.com/file.mkv"]},
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.redirect_link("https://dl-protect.link/abc")

        assert result == "https://direct.example.com/file.mkv"

    async def test_raises_on_http_error(self, client: AllDebridClient) -> None:
        session = _mock_session(_mock_response(503, {}))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            with pytest.raises(AllDebridHTTPError) as exc_info:
                await client.redirect_link("https://dl-protect.link/abc")

        assert exc_info.value.status == 503

    async def test_raises_on_api_error(self, client: AllDebridClient) -> None:
        payload = {
            "status": "error",
            "error": {"message": "Invalid link", "code": "LINK_ERROR"},
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            with pytest.raises(AllDebridAPIError) as exc_info:
                await client.redirect_link("https://dl-protect.link/abc")

        assert "Invalid link" in str(exc_info.value)
        assert exc_info.value.code == "LINK_ERROR"


class TestDebridLink:
    async def test_unlocks_direct_link(self, client: AllDebridClient) -> None:
        payload = {
            "status": "success",
            "data": {
                "link": "https://cdn.example.com/file.mkv",
                "filename": "file.mkv",
            },
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.debrid_link("https://1fichier.com/?abc123")

        assert result["filename"] == "file.mkv"

    async def test_raises_on_http_error(self, client: AllDebridClient) -> None:
        session = _mock_session(_mock_response(401, {}))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            with pytest.raises(AllDebridHTTPError) as exc_info:
                await client.debrid_link("https://1fichier.com/?abc123")

        assert exc_info.value.status == 401

    async def test_raises_on_api_error(self, client: AllDebridClient) -> None:
        payload = {
            "status": "error",
            "error": {"message": "Locked link", "code": "LINK_LOCKED"},
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            with pytest.raises(AllDebridAPIError) as exc_info:
                await client.debrid_link("https://1fichier.com/?abc123")

        assert exc_info.value.code == "LINK_LOCKED"


class TestMagnets:
    async def test_upload_magnet_returns_id(self, client: AllDebridClient) -> None:
        payload = {
            "status": "success",
            "data": {"magnets": [{"id": 123, "hash": "ABC"}]},
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.upload_magnet("magnet:?xt=urn:btih:ABC")

        assert result == 123

    async def test_get_magnet_status_returns_payload(
        self, client: AllDebridClient
    ) -> None:
        payload = {
            "status": "success",
            "data": {"magnets": [{"id": 123, "status": "Ready"}]},
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.get_magnet_status(123)

        assert result["magnets"][0]["status"] == "Ready"

    async def test_get_magnet_files_returns_largest_first(
        self, client: AllDebridClient
    ) -> None:
        payload = {
            "status": "success",
            "data": {
                "files": [
                    {"link": "https://cdn.example.com/sample.mkv", "size": 10},
                    {"link": "https://cdn.example.com/movie.mkv", "size": 1000},
                ]
            },
        }
        session = _mock_session(_mock_response(200, payload))

        with patch(
            "app.services.alldebrid.aiohttp.ClientSession", return_value=session
        ):
            result = await client.get_magnet_files(123)

        assert result == [
            "https://cdn.example.com/movie.mkv",
            "https://cdn.example.com/sample.mkv",
        ]
