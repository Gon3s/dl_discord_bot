from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import SearchResponse
from app.models.schemas import SearchResult as SearchResultSchema
from app.scrapers.base import get_scraper

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    source: str = Query("wawacity", description="Scraper source"),
    category: str = Query("films", description="Content category"),
    year: int | None = Query(None, description="Release year filter"),
    limit: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    try:
        scraper = get_scraper(source)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source!r}")

    raw = await scraper.search(q, category, year, limit)

    results = [
        SearchResultSchema(
            title=r.title,
            url=r.url,
            year=r.year,
            category=category,
            quality=r.quality,
            language=r.language,
            source=r.source,
            poster_url=r.poster_url,
        )
        for r in raw
    ]
    return SearchResponse(results=results, total=len(results), source=source)
