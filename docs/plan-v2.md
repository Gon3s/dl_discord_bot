# Plan v2 : dl_discord_bot

## État actuel

La v2 est désormais l'architecture principale du dépôt `main`.

- **FastAPI backend** — couche logique partagée (scraping, debrid, téléchargement, BDD)
- **Angular 21 + Tailwind CSS v3 frontend** — interface web principale
- **Discord bot allégé** — thin client qui appelle le backend
- **Déploiement systemd** — `deploy/install.sh`, `dl_backend.service`, `discord_bot.service`

Docker Compose reste à faire et est suivi par l'issue #44. La migration
Tailwind CSS v4 reste à faire et est suivie par l'issue #71.

---

## Structure du projet (monorepo)

```
dl_discord_bot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI factory + lifespan
│   │   ├── config.py            # pydantic-settings (.env)
│   │   ├── database.py          # SQLAlchemy async + aiosqlite
│   │   ├── api/v1/
│   │   │   ├── search.py        # GET /api/v1/search
│   │   │   ├── downloads.py     # POST/GET/DELETE /api/v1/downloads
│   │   │   ├── history.py       # GET/DELETE /api/v1/history
│   │   │   ├── episodes.py      # GET /api/v1/episodes
│   │   │   ├── favorites.py     # favoris
│   │   │   └── settings.py      # GET/PUT /api/v1/settings
│   │   ├── core/
│   │   │   ├── queue.py         # Gestionnaire de file asyncio
│   │   │   └── events.py        # Bus d'événements WS (dict asyncio.Queue)
│   │   ├── scrapers/
│   │   │   ├── base.py          # Abstract BaseScraper
│   │   │   ├── wawacity.py      # Migration de parser.py
│   │   │   ├── darkiworld.py    # Implémentation avec session authentifiée
│   │   │   └── x1337.py         # Recherche 1337x + extraction magnet
│   │   ├── services/
│   │   │   ├── download_service.py
│   │   │   └── alldebrid.py     # Migration async de alldebrid.py
│   │   └── models/
│   │       ├── orm.py           # Tables SQLAlchemy
│   │       └── schemas.py       # Schémas Pydantic
│   ├── alembic/                 # Migrations BDD
│   └── pyproject.toml
│
├── frontend/                    # Angular 21 + Tailwind 3
│   ├── src/app/
│   │   ├── features/
│   │   │   ├── search/          # Recherche + sélection résultats
│   │   │   ├── downloads/       # File active + progression WS
│   │   │   ├── history/         # Historique paginé + recherche
│   │   │   └── settings/        # Config (path, source par défaut)
│   │   ├── core/services/
│   │   │   ├── api.service.ts   # Wrapper HTTP vers backend
│   │   │   └── ws.service.ts    # WebSocket progression
│   │   └── shared/              # Composants réutilisables
│   └── package.json
│
├── bot/
│   ├── main.py                  # Entry point
│   ├── client.py                # HTTP client vers backend API
│   └── cogs/
│       ├── search.py            # !search → appelle /api/v1/search
│       └── download.py          # !url → appelle /api/v1/downloads
│
├── deploy/
└── .env.example
```

---

## Backend — API FastAPI

### Endpoints

```
GET  /api/v1/search?q=...&source=wawacity&category=films&year=2024&limit=10
GET  /api/v1/search?q=...&source=1337x&category=films&limit=10
POST /api/v1/downloads        body: { source_url, media_type, destination: "server"|"client" }
GET  /api/v1/downloads        → liste avec statut/progression
GET  /api/v1/downloads/{id}
DELETE /api/v1/downloads/{id} → annulation
POST /api/v1/downloads/{id}/retry
GET  /api/v1/episodes
GET  /api/v1/favorites

GET  /api/v1/history?page=1&limit=50&q=...
DELETE /api/v1/history/{id}

GET  /api/v1/settings
PUT  /api/v1/settings

GET  /api/v1/status           → { queue_size, active, disk_free_gb, alldebrid_ok }

WS   /ws/downloads/{id}       → { status, progress_pct, speed_mbps, eta_s, filename }
WS   /ws/queue                → événements globaux de la file
```

### Destination "client" (téléchargement navigateur)
- `destination: "client"` → le backend **ne télécharge pas** le fichier
- Il appelle AllDebrid pour obtenir l'URL directe débriddée
- Retourne `{ debrid_url: "https://..." }` dans la réponse
- Le frontend déclenche un `window.open(debrid_url)` ou un lien `<a href>` direct
- Pas de streaming côté serveur, pas de stockage inutile

### Base de données — SQLite + SQLAlchemy async

Tables :
```sql
downloads (id UUID PK, title, source_url, media_type, destination, status,
           progress_pct, speed_mbps, filename, created_at, completed_at, error)
history   (id UUID PK, title, source_url, filename, media_type, source,
           downloaded_at)
settings  (key TEXT PK, value TEXT)
```

Remplace `history.csv` + pandas. Migration via Alembic.

### Scraper abstraction

```python
# scrapers/base.py
class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    async def search(self, query, category, year, limit, sort, page) -> list[SearchResult]: ...

    async def get_provider_links(self, url, providers) -> list[ProviderLinks]: ...
    async def get_episodes(self, url, providers=None) -> list[Episode]: ...
```

- `wawacity.py` — migration de `parser.py` (Selenium + BS4)
- `darkiworld.py` — implémenté (login Selenium + API JSON)
- `x1337.py` — implémenté (aiohttp + BS4, magnets filtrés sur seeders > 0)
- `scrapers/base.py` expose le registre automatique selon `source`

### Flux magnet AllDebrid
- Un scraper peut retourner `ProviderLinks(provider="magnet", urls=[...])`.
- `DownloadService` envoie le magnet à AllDebrid (`magnet/upload`), poll
  `magnet/status`, puis récupère les fichiers via `magnet/files`.
- Les fichiers sont triés par taille décroissante côté client AllDebrid ; le
  premier lien est utilisé comme fichier principal.
- Le flux DDL existant reste inchangé pour Wawacity/DarkiWorld.

### Suppression du code inutile (refacto)
- Supprimer `pandas` (remplacé par SQLite)
- Supprimer `python-slugify` si non essentiel
- Réécrire `alldebrid.py` en async pur (aiohttp uniquement)
- Corriger le bug logique `bot.py:459` (`and` → `or`)
- Remplacer la recherche O(n) dans `history.csv` par une requête SQL indexée

---

## Frontend — Angular 21 + Tailwind 3

### Setup
- Angular 21 (standalone components, signals)
- Tailwind CSS v3.4
- Angular HttpClient vers le backend FastAPI
- WebSocket natif (ou RxJS WebSocketSubject) pour la progression

### Pages

**Search** (`/search`)
- Barre de recherche avec sélecteur source / catégorie / année
- Grille résultats : poster, titre, année, qualité, langue
- Bouton "Télécharger" → modal : choix destination (serveur / lien direct)
- Si "lien direct" → appel API → `window.open(debrid_url)`

**Downloads** (`/downloads`)
- Liste téléchargements actifs avec barre de progression temps-réel (WS)
- File d'attente avec bouton annulation

**History** (`/history`)
- Tableau paginé searchable
- Suppression d'entrées

**Settings** (`/settings`)
- `DOWNLOAD_PATH`, source par défaut, providers préférés

### Pas d'authentification
- App exposée uniquement en réseau local / VPN
- Aucun middleware d'auth côté backend pour les routes web

---

## Bot Discord — thin client

- Chaque commande fait un appel HTTP au backend local
- `!search <query> <category>` → `GET /api/v1/search` puis pagination Discord
- `!url <url> <folder>` → `POST /api/v1/downloads` avec `destination: "server"`
- `!status` → `GET /api/v1/status`
- Suppression de toute logique scraping/debrid/download du bot

---

## Ordre d'implémentation

1. **Backend core** — config, BDD, modèles, migration CSV→SQLite
2. **Scrapers** — migration `wawacity.py` + `alldebrid.py` async
3. **Services + API REST** — endpoints search + downloads + history
4. **WebSocket** — bus événements + progression temps-réel
5. **Frontend Angular** — scaffold + pages search + downloads
6. **Bot refacto** — thin client HTTP
7. **Settings + Status** — derniers endpoints + page settings frontend
8. **Déploiement systemd** — services backend + bot, frontend servi par FastAPI
9. **Docker** — à faire (#44)

---

## Fichiers critiques à migrer/réécrire

| Fichier actuel | Destination v2 |
|---|---|
| `bot.py` | `bot/cogs/search.py`, `bot/cogs/download.py`, `bot/client.py` |
| `parser.py` | `backend/app/scrapers/wawacity.py` |
| `alldebrid.py` | `backend/app/services/alldebrid.py` (async) |
| `history.csv` | Table `history` SQLite via Alembic migration |

---

## Vérification (test end-to-end)

1. `bash deploy/install.sh` → backend + frontend sur `:8000`, bot via systemd
2. Rechercher "dragon ball" sur `/search` → résultats Wawacity affichés
3. Cliquer "Télécharger" → destination "serveur" → fichier téléchargé dans `DOWNLOAD_PATH/Movies/`
4. Cliquer "Télécharger" → destination "lien direct" → `debrid_url` retournée, navigateur ouvre le lien
5. `/downloads` montre la progression temps-réel via WebSocket
6. `/history` liste les téléchargements passés
7. Bot Discord : `!search "inception" films` → mêmes résultats via API
8. `GET /api/v1/status` → `200 OK` avec infos disque et AllDebrid
