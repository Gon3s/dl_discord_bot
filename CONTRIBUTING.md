# Contributing

Contributions are welcome - bug reports, new scrapers, UI improvements, translations.

## Getting started

```bash
git clone https://github.com/gon3s/dl-discord-bot
cd dl-discord-bot
cp .env.example .env   # fill in your keys
```

Start the backend in watch mode and the frontend dev server:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm ci && npm run start -- --port 4200
```

## Adding a scraper (easiest contribution)

Create `backend/app/scrapers/<name>.py` - no other file needs to change:

```python
from app.scrapers.base import BaseScraper, SearchResult, ProviderLinks, register

@register
class MyScraper(BaseScraper):
    source_name = "mysite"   # used as ?source= query param

    async def search(self, query, category, year=None, limit=10, sort=None, page=1) -> list[SearchResult]: ...
    async def get_provider_links(self, url, providers) -> list[ProviderLinks]: ...
    async def get_episodes(self, url, providers=None): ...
```

See `backend/app/scrapers/wawacity.py` for a full reference implementation.

## Running tests

```bash
cd backend
uv run pytest           # full suite (~120 tests)
uv run ruff check       # linter
uv run ruff format      # formatter
```

All tests must pass before opening a PR.

## Pull request checklist

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check` reports no errors
- [ ] New endpoints have a corresponding Bruno request in `bruno/`
- [ ] New env variables are documented in `.env.example` and `README.md`

## Reporting issues

Please include:
- Your OS and deployment method (Docker / systemd / local)
- Relevant logs (`docker compose logs backend` or `journalctl -u dl_backend`)
- Steps to reproduce
