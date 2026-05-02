import pytest

from app.services.alldebrid import AllDebridClient
from app.services.debrid import get_debrid_client
from app.services.realdebrid import RealDebridClient


def test_get_debrid_client_returns_alldebrid() -> None:
    client = get_debrid_client("alldebrid")

    assert isinstance(client, AllDebridClient)


def test_get_debrid_client_returns_realdebrid() -> None:
    client = get_debrid_client("realdebrid")

    assert isinstance(client, RealDebridClient)


def test_get_debrid_client_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported debrid provider"):
        get_debrid_client("unknown")
