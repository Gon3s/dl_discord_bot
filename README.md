<div align="center">

# 🎬 DLux

**Self-hosted media downloader with a web UI and Discord bot.**  
Search movies, TV shows and manga, debrид links via AllDebrid / Real-Debrid, track downloads in real time.

[![Release](https://img.shields.io/github/v/release/Gon3s/dlux?color=blue)](https://github.com/Gon3s/dlux/releases)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Angular](https://img.shields.io/badge/Angular-21-DD0031?logo=angular&logoColor=white)](https://angular.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/tests-120%20passed-4CAF50?logo=pytest&logoColor=white)](backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

![Demo](demo/demo.gif)

</div>

---

## What is this?

A three-tier application built for personal use on a home server:

- **Web UI** (Angular 21) - search, browse episodes, manage the download queue, history, favorites
- **FastAPI backend** - scraping, debrid resolution, async download queue, SQLite persistence, WebSocket progress
- **Discord bot** - trigger searches and downloads from any channel without opening a browser

Everything runs in Docker. One port (`:8765`) exposes both the API and the pre-built frontend.

---

## ✨ Features

- 🔍 **Search** - movies, TV shows, manga from a single interface
- ⚡ **Auto-debrid** - AllDebrid and Real-Debrid support, dl-protect link resolution via SeleniumBase
- 📺 **Episode picker** - browse seasons and individual episodes before downloading
- 📡 **Real-time progress** - WebSocket-based download tracking
- 📂 **History & favorites** - searchable download history, save titles for later
- ⚙️ **Live settings** - change debrid provider, download path and concurrency from the UI without restarting
- 🤖 **Discord bot** - `!search`, `!url`, `!status` slash commands
- 🌐 **Cloudflare Tunnel** - optional, for remote access without port-forwarding

---

## 📸 Screenshots

<details>
<summary>Expand</summary>

| Search | Download modal |
|:------:|:--------------:|
| ![Search](demo/screenshots/02_search_results.png) | ![Modal](demo/screenshots/03_download_modal.png) |

| Episode picker | Download queue |
|:--------------:|:--------------:|
| ![Episodes](demo/screenshots/05_episodes_panel.png) | ![Downloads](demo/screenshots/06_downloads.png) |

| History | Settings |
|:-------:|:--------:|
| ![History](demo/screenshots/07_history.png) | ![Settings](demo/screenshots/08_settings.png) |

</details>

---

## 🚀 Quick start (Docker)

**Minimum required - copy, fill in two values, run:**

```yaml
# docker-compose.minimal.yml
services:
  backend:
    image: ghcr.io/gon3s/dlux-backend:latest
    ports:
      - "8765:8000"
    environment:
      DEBRID_PROVIDER: alldebrid
      ALLDEBRID_API_KEY: YOUR_KEY
      DOWNLOAD_PATH: /data/media
    volumes:
      - media:/data/media
      - backend_db:/app/data
    shm_size: '2gb'
    restart: unless-stopped
volumes:
  media:
  backend_db:
```

```bash
docker compose -f docker-compose.minimal.yml up -d
# Open http://localhost:8765
```

**Full stack with Discord bot and optional Cloudflare Tunnel:**

```bash
cp .env.example .env   # fill in the variables below
docker compose up -d
```

```bash
# .env - required
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD=your_server_id
DEBRID_PROVIDER=alldebrid        # or realdebrid
ALLDEBRID_API_KEY=your_key       # or REALDEBRID_API_TOKEN=
DOWNLOAD_PATH=/data/media

# .env - optional
CLOUDFLARE_TUNNEL_TOKEN=         # for remote access without port-forwarding
MAX_CONCURRENT_DOWNLOADS=2
```

Images are built by GitHub Actions on every push to `main` and published to `ghcr.io`.

---

## 🏗️ Architecture

```
dlux/
├── backend/    FastAPI - SQLite - Alembic - aiohttp - SeleniumBase
├── frontend/   Angular 21 - Tailwind CSS v3 - Signals - WebSocket
├── bot/        Discord thin client -> HTTP calls to the backend
└── deploy/     systemd units (alternative to Docker)
```

The backend serves the pre-built frontend as static files - a single port handles everything.

---

## 🔧 All environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | - |
| `DISCORD_GUILD` | Discord server ID | - |
| `DEBRID_PROVIDER` | `alldebrid` or `realdebrid` | `alldebrid` |
| `ALLDEBRID_API_KEY` | AllDebrid API key | - |
| `REALDEBRID_API_TOKEN` | Real-Debrid API token | - |
| `DOWNLOAD_PATH` | Destination folder | `/data/media` |
| `WAWACITY_URL` | Wawacity base URL | `https://www.wawacity.city/` |
| `DATABASE_URL` | SQLite async URL | `sqlite+aiosqlite:///./dl_bot.db` |
| `MAX_CONCURRENT_DOWNLOADS` | Parallel downloads | `2` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Tunnel token | - |
| `SELENIUM_BINARY_LOCATION` | Chrome binary for SeleniumBase | auto |
| `BACKEND_URL` | Backend URL used by the bot | `http://localhost:8000` |

> Operational settings (`debrid_provider`, `download_path`, concurrency) can also be changed live from the web UI without restarting.

---

## 🌐 REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/search` | Search (`?q=&source=&category=`) |
| `GET` | `/api/v1/episodes` | List episodes for a series URL |
| `POST` | `/api/v1/downloads` | Queue a download |
| `GET` | `/api/v1/downloads` | List active downloads |
| `GET` | `/api/v1/downloads/{id}` | Get download details |
| `DELETE` | `/api/v1/downloads/{id}` | Cancel / remove a download |
| `POST` | `/api/v1/downloads/{id}/retry` | Retry a failed download |
| `GET` | `/api/v1/history` | Download history |
| `DELETE` | `/api/v1/history/{id}` | Remove a history entry |
| `GET` | `/api/v1/favorites` | List favorites |
| `POST` | `/api/v1/favorites` | Add a favorite |
| `DELETE` | `/api/v1/favorites/{id}` | Remove a favorite |
| `GET` | `/api/v1/settings` | Read settings |
| `PUT` | `/api/v1/settings` | Update settings |
| `GET` | `/api/v1/status` | Backend health + debrid status |
| `WS` | `/ws/downloads/{id}` | Real-time download progress |
| `WS` | `/ws/queue` | Real-time queue state |

A full [Bruno](https://www.usebruno.com/) collection is available in `bruno/`.

---

## 🤖 Discord commands

| Command | Description |
|---------|-------------|
| `!search <title> [films\|series\|mangas]` | Search for a title |
| `!url <url>` | Download from a direct page URL |
| `!status` | Backend health and debrid provider status |

---

## 🧩 Adding a scraper

Drop a new file in `backend/app/scrapers/<name>.py` - the registry is automatic, no other file needs editing:

```python
from app.scrapers.base import BaseScraper, SearchResult, ProviderLinks, register

@register
class MyScraper(BaseScraper):
    source_name = "mysite"   # maps to the ?source= query parameter

    async def search(
        self, query: str, category: str, year=None, limit=10, sort=None, page=1
    ) -> list[SearchResult]: ...

    async def get_provider_links(
        self, url: str, providers: list[str]
    ) -> list[ProviderLinks]: ...

    async def get_episodes(self, url: str, providers=None): ...
```

See `backend/app/scrapers/wawacity.py` for a reference implementation.  
Contributions for new sources are welcome - see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🧪 Tests & code quality

```bash
cd backend
uv run pytest           # 120 tests
uv run ruff check       # linter
uv run ruff format      # formatter
```

---

## 🗄️ Database migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1
```

---

## 🖥️ Local development (without Docker)

### Requirements

| Tool | Min version |
|------|-------------|
| Python | 3.12 |
| [uv](https://docs.astral.sh/uv/) | latest |
| Node.js | 20+ |
| Chrome / Chromium | for Selenium (dl-protect links) |

```bash
# Backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Frontend (hot-reload on :4200)
cd frontend && npm ci && npm run start -- --port 4200

# Discord bot
cd bot && uv run python main.py
```

The Angular dev proxy forwards `/api` and `/ws` to `:8000` automatically.

---

## ⚠️ Legal notice

This project is provided for **educational purposes and personal use only**.  
It does not host, distribute or cache any copyrighted content - it automates interactions with third-party websites.  
You are solely responsible for ensuring your use complies with the terms of service of any website you access and with the copyright laws of your country.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports, new scrapers and UI improvements are all welcome.

---

## 📄 License

[MIT](LICENSE)
