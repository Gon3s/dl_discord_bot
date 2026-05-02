from typing import Protocol

from app.config import settings
from app.services.alldebrid import AllDebridClient
from app.services.realdebrid import RealDebridClient

MagnetId = int | str


class DebridClient(Protocol):
    name: str
    display_name: str

    async def ping(self) -> bool: ...

    async def debrid_link(self, url: str) -> dict: ...

    async def upload_magnet(self, magnet: str) -> MagnetId: ...

    async def get_magnet_status(self, magnet_id: MagnetId) -> dict: ...

    async def get_magnet_files(self, magnet_id: MagnetId) -> list[str]: ...


_PROVIDERS = {
    "alldebrid": AllDebridClient,
    "realdebrid": RealDebridClient,
}


def get_debrid_client(provider: str | None = None) -> DebridClient:
    selected = (provider or settings.debrid_provider).lower()
    try:
        client_cls = _PROVIDERS[selected]
    except KeyError as exc:
        supported = ", ".join(sorted(_PROVIDERS))
        raise ValueError(
            f"Unsupported debrid provider: {selected} ({supported})"
        ) from exc
    return client_cls()
