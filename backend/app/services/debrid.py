from typing import Protocol

from app.config import settings
from app.models.domain import DebridProvider
from app.services.alldebrid import AllDebridClient
from app.services.realdebrid import RealDebridClient

MagnetId = int | str


class DebridClient(Protocol):
    name: DebridProvider
    display_name: str

    async def ping(self) -> bool: ...

    async def debrid_link(self, url: str) -> dict: ...

    async def upload_magnet(self, magnet: str) -> MagnetId: ...

    async def get_magnet_status(self, magnet_id: MagnetId) -> dict: ...

    async def get_magnet_files(self, magnet_id: MagnetId) -> list[str]: ...


_PROVIDERS: dict[DebridProvider, type[DebridClient]] = {
    DebridProvider.ALLDEBRID: AllDebridClient,
    DebridProvider.REALDEBRID: RealDebridClient,
}


def get_debrid_client(provider: str | DebridProvider | None = None) -> DebridClient:
    selected_value = (provider or settings.debrid_provider).lower()
    try:
        selected = DebridProvider(selected_value)
        client_cls = _PROVIDERS[selected]
    except (KeyError, ValueError) as exc:
        supported = ", ".join(sorted(_PROVIDERS))
        raise ValueError(
            f"Unsupported debrid provider: {selected_value} ({supported})"
        ) from exc
    return client_cls()
