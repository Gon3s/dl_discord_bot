# dl_discord_bot v2

![Python](https://img.shields.io/badge/python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Angular](https://img.shields.io/badge/Angular-21-DD0031?logo=angular)
![Tests](https://img.shields.io/badge/tests-89%20passed-brightgreen?logo=pytest)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Application trois tiers pour rechercher et télécharger des films, séries et mangas depuis **Wawacity** via **AllDebrid**.

```
dl_discord_bot/
├── backend/    FastAPI · SQLite · Alembic · aiohttp · Selenium
├── frontend/   Angular 21 · Tailwind CSS v4
└── bot/        Discord thin client → backend HTTP
```

---

## Démarrage rapide

### 1. Configuration

```bash
cp .env.example .env
# Remplir DISCORD_TOKEN, ALLDEBRID_API_KEY, DOWNLOAD_PATH, WAWACITY_URL
```

### 2. Développement local

```bash
# Backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && ng serve --port 4200

# Bot Discord
cd bot && uv run python main.py
```

### 3. Production (systemd)

```bash
bash deploy/install.sh
```

> Installe et démarre `dl_backend.service` + `discord_bot.service`.  
> Voir `deploy/` pour les fichiers unit.

---

## Variables d'environnement

| Variable | Description | Exemple |
|---|---|---|
| `DISCORD_TOKEN` | Token du bot Discord | `MTI...` |
| `DISCORD_GUILD` | ID du serveur Discord | `123456789` |
| `ALLDEBRID_API_KEY` | Clé API AllDebrid | `abc123` |
| `DOWNLOAD_PATH` | Répertoire de stockage | `/data/media` |
| `WAWACITY_URL` | URL de base Wawacity | `https://www.wawacity.city/` |
| `DATABASE_URL` | SQLite async | `sqlite+aiosqlite:///./dl_bot.db` |
| `MAX_CONCURRENT_DOWNLOADS` | Téléchargements simultanés | `2` |
| `BACKEND_URL` | URL backend pour le bot | `http://localhost:8000` |

---

## API REST

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/search` | Rechercher un titre |
| `POST` | `/api/v1/downloads` | Lancer un téléchargement |
| `GET` | `/api/v1/downloads` | Lister les téléchargements |
| `GET` | `/api/v1/downloads/{id}` | Détail d'un téléchargement |
| `DELETE` | `/api/v1/downloads/{id}` | Supprimer |
| `GET` | `/api/v1/history` | Historique |
| `GET` | `/api/v1/status` | Santé du backend |
| `WS` | `/ws/downloads/{id}` | Progression temps réel |
| `WS` | `/ws/queue` | File d'attente temps réel |

---

## Tests

```bash
cd backend && uv run pytest
```

---

## Commandes Discord

| Commande | Description |
|---|---|
| `!search <query> [films\|series\|mangas]` | Rechercher un titre |
| `!url <url>` | Télécharger depuis une URL directe |
| `!status` | Statut du backend + AllDebrid |

---

## Migrations BDD

```bash
cd backend
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

---

## Ajouter un scraper

Créer `backend/app/scrapers/<nom>.py` :

```python
from app.scrapers.base import BaseScraper, SearchResult, ProviderLinks, register

@register
class MonScraper(BaseScraper):
    source_name = "mon_source"

    async def search(self, query, category, year, limit) -> list[SearchResult]: ...
    async def get_provider_links(self, url, providers) -> list[ProviderLinks]: ...
```

Aucune autre modification nécessaire — le registre est automatique.

---

## Documentation

- [`docs/plan-v2.md`](docs/plan-v2.md) — Plan d'implémentation complet
- [`docs/architecture-v2.md`](docs/architecture-v2.md) — Diagrammes d'architecture
