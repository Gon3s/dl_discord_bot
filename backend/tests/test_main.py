import pytest


class TestAppStartup:
    async def test_docs_available(self, client):
        response = await client.get("/docs")
        assert response.status_code == 200

    async def test_openapi_schema(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "dl_discord_bot API"
        assert data["info"]["version"] == "2.0.0"

    async def test_unknown_route_returns_404(self, client):
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404
