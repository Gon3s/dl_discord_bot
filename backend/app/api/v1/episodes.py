from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import EpisodeLinkRead, EpisodeRead
from app.scrapers.base import get_scraper

router = APIRouter()


@router.get("/episodes", response_model=list[EpisodeRead])
async def get_episodes(
    url: str = Query(..., description="URL de la page série"),
    source: str = Query("wawacity", description="Scraper source"),
    providers: str = Query("", description="Providers filtrés, séparés par virgule"),
) -> list[EpisodeRead]:
    try:
        scraper = get_scraper(source)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source!r}")

    provider_list = [p.strip() for p in providers.split(",") if p.strip()]

    try:
        raw = await scraper.get_episodes(url, provider_list or None)
    except NotImplementedError:
        raise HTTPException(
            status_code=501, detail=f"Episodes not implemented for source: {source!r}"
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Scraper error: {exc}") from exc

    return [
        EpisodeRead(
            title=ep.title,
            number=ep.number,
            links=[
                EpisodeLinkRead(provider=pl.provider, url=pl.urls[0])
                for pl in ep.provider_links
                if pl.urls
            ],
        )
        for ep in raw
    ]
