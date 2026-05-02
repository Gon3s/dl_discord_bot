import pytest

from app.services.alldebrid import AllDebridClient
from app.services.debrid import get_debrid_client


def test_get_debrid_client_returns_alldebrid() -> None:
    client = get_debrid_client("alldebrid")

    assert isinstance(client, AllDebridClient)


def test_get_debrid_client_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported debrid provider"):
        get_debrid_client("unknown")
