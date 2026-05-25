# CLAUDE.md — dl_discord_bot v2

## Présentation du projet

Application trois tiers pour rechercher et télécharger des films/séries/mangas
depuis Wawacity via AllDebrid.

- **`backend/`** — FastAPI (Python 3.12) : toute la logique scraping, debrid, téléchargement, BDD
- **`frontend/`** — Angular 21 + Tailwind CSS v3 : interface web principale
- **`bot/`** — Discord Bot thin client : appelle le backend via HTTP

Docs complètes : `docs/plan-v2.md` et `docs/architecture-v2.md`

---

## Principes de travail LLM

Ces règles complètent les consignes projet. Elles privilégient la prudence et
la simplicité ; pour les tâches triviales, utiliser son jugement.

### Réfléchir avant de coder
- Ne pas supposer silencieusement : expliciter les hypothèses importantes.
- Si plusieurs interprétations existent, les présenter avant d'implémenter.
- Signaler les compromis et proposer l'approche la plus simple quand elle suffit.
- Si un point bloque ou reste ambigu, le nommer clairement et demander une précision.

### Simplicité d'abord
- Écrire le minimum de code qui résout la demande.
- Ne pas ajouter de fonctionnalité, d'abstraction ou de configurabilité spéculative.
- Éviter la gestion d'erreurs pour des scénarios impossibles dans le contexte.
- Si une solution devient volumineuse alors qu'elle peut rester courte, simplifier.

### Changements chirurgicaux
- Modifier uniquement les fichiers et lignes nécessaires à la demande.
- Ne pas refactorer, reformater ou nettoyer du code adjacent sans raison directe.
- Respecter le style existant, même si une autre approche serait préférée ailleurs.
- Supprimer seulement les imports, variables ou fonctions rendus inutiles par ses
  propres changements.
- Mentionner le code mort ou les problèmes hors périmètre au lieu de les corriger
  sans demande explicite.

### Exécution orientée objectif
- Transformer chaque tâche en critères de succès vérifiables.
- Pour un bug, reproduire ou cibler le comportement attendu avant de corriger.
- Pour une refactorisation, vérifier que les tests passent avant et après si possible.
- Pour une tâche multi-étapes, garder un plan court avec la vérification associée.

---

## Lancer le projet

### Développement (local)

```bash
# Backend (sert aussi le frontend buildé sur :8000)
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Frontend hot-reload (dev uniquement)
cd frontend
npm ci
npm run start -- --port 4200

# Bot Discord
cd bot
uv run python main.py
```

### Production (Docker Compose)

```bash
cp .env.example .env  # remplir DISCORD_TOKEN, ALLDEBRID_API_KEY, etc.
docker compose up -d --build
```

- `BACKEND_URL` et `SELENIUM_BINARY_LOCATION` sont surchargés automatiquement par `docker-compose.yml`.
- `DATABASE_URL` pointe vers le volume `backend_db` (`/app/data/dl_bot.db`).
- Fichiers téléchargés dans le volume `media` (`/data/media`).

### Production (systemd)

```bash
# Première installation (build Angular + migrations + services)
bash deploy/install.sh

# Redémarrer après une mise à jour du backend
sudo systemctl restart dl_backend.service discord_bot.service

# Redémarrer après une mise à jour du frontend
cd frontend && ng build --configuration production
sudo systemctl restart dl_backend.service
```

> L'interface web est accessible sur **`http://<serveur>:8000`** — servie directement par FastAPI.

### WSL / Node

Ne pas utiliser le `npm` Windows depuis WSL. Installer Node dans WSL ou utiliser
le runtime local si présent :

```bash
export PATH="$PWD/.codex/runtime/node-v22.12.0-linux-x64/bin:$PATH"
cd frontend
npm ci
npm run build
```

---

## Variables d'environnement

Copier `.env.example` → `.env` à la racine. Variables clés :

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Token du bot Discord |
| `DISCORD_GUILD` | ID du serveur Discord |
| `ALLDEBRID_API_KEY` | Clé API AllDebrid |
| `DOWNLOAD_PATH` | Chemin de stockage des fichiers (ex: `/data/media`) |
| `WAWACITY_URL` | URL de base Wawacity (ex: `https://www.wawacity.city/`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./dl_bot.db` |
| `MAX_CONCURRENT_DOWNLOADS` | Nombre de téléchargements simultanés (défaut: 2) |
| `BACKEND_URL` | URL du backend pour le bot (ex: `http://localhost:8000`) |

---

## Migrations BDD

```bash
cd backend

# Créer une nouvelle migration
uv run alembic revision --autogenerate -m "description"

# Appliquer les migrations
uv run alembic upgrade head

# Rollback d'une migration
uv run alembic downgrade -1
```

---

## Architecture des scrapers

Pour ajouter une nouvelle source de données, créer `backend/app/scrapers/<nom>.py` :

```python
from app.scrapers.base import BaseScraper, SearchResult, ProviderLinks, register

@register
class MonScraper(BaseScraper):
    source_name = "mon_source"  # valeur du param ?source= dans l'API

    async def search(
        self, query, category, year=None, limit=10, sort=None, page=1
    ) -> list[SearchResult]:
        ...

    async def get_provider_links(self, url, providers) -> list[ProviderLinks]:
        ...

    async def get_episodes(self, url, providers=None):
        ...
```

Aucune autre modification n'est nécessaire. Le registre est automatique.

**Sources actuelles :**
- `wawacity` — implémenté (`backend/app/scrapers/wawacity.py`)

---

## Conventions de code

### Python (backend + bot)
- **Formatter** : `ruff format` (remplace black)
- **Linter** : `ruff check`
- `ruff` est une dépendance dev du backend : utiliser `cd backend && uv run ruff check`
- **Type hints** obligatoires sur toutes les fonctions publiques
- Async partout dans le backend — pas de `requests` ni d'appels bloquants dans les coroutines
- Les appels Selenium (bloquants) doivent être wrappés dans `asyncio.get_event_loop().run_in_executor(None, ...)`
- **Selenium ne supporte pas la parallélisation** — utiliser `_dl_protect_sem = asyncio.Semaphore(1)` pour sérialiser les sessions Chrome
- Exceptions custom dans `app/core/exceptions.py` — pas de `assert False` ni de `print()`

### TypeScript (frontend)
- **Angular 21 standalone components** uniquement — pas de NgModule.
- **Tailwind CSS v3.4** actuellement. La migration v4 est suivie par l'issue #71.
- **`signal()` / `computed()`** pour l'état local quand c'est adapté.
- **`linkedSignal()`** pour l'état dérivé mais modifiable.
- **`resource`/RxJS** selon le pattern déjà présent dans la feature concernée.
- **`takeUntilDestroyed()`** pour les subscriptions dans le constructeur — remplace `OnDestroy + Subscription`
- `ApiService` pour tous les appels HTTP — pas de `HttpClient` en direct dans les composants
- `WsService` pour toutes les connexions WebSocket
- `inject()` à la place de l'injection par constructeur

---

## Structure des endpoints API

```
GET    /api/v1/search
POST   /api/v1/downloads
GET    /api/v1/downloads
GET    /api/v1/downloads/{id}
DELETE /api/v1/downloads/{id}
POST   /api/v1/downloads/{id}/retry   ← reset + re-enqueue si status=error
GET    /api/v1/episodes
GET    /api/v1/history
DELETE /api/v1/history/{id}
GET    /api/v1/settings
PUT    /api/v1/settings
GET    /api/v1/status
WS     /ws/downloads/{id}
WS     /ws/queue
```

Schémas Pydantic dans `backend/app/models/schemas.py`.

---

## Fichiers importants

| Fichier | Rôle |
|---|---|
| `backend/app/main.py` | FastAPI factory, lifespan, montage des routers |
| `backend/app/core/queue.py` | File de téléchargement asyncio, workers |
| `backend/app/core/events.py` | Bus événements WebSocket (dict UUID→Queue) |
| `backend/app/scrapers/base.py` | BaseScraper ABC + registre de scrapers |
| `backend/app/services/download_service.py` | Logique debrid + téléchargement + progression |
| `frontend/src/app/core/models/` | Interfaces TypeScript (SearchResult, Download, etc.) |
| `frontend/src/app/core/services/api.service.ts` | Wrapper HttpClient → backend :8000 |
| `frontend/src/app/core/services/ws.service.ts` | RxJS WebSocketSubject → WS :8000 |
| `frontend/src/app/features/search/` | Feature search (component + routes) |
| `frontend/src/app/features/downloads/` | Feature downloads (component + routes) |
| `frontend/src/app/features/history/` | Feature history (component + routes) |
| `frontend/src/app/features/settings/` | Feature settings (component + routes) |
| `bot/client.py` | Thin client HTTP vers le backend |

---

## Workflow issue

1. `/start-issue {numero} {nom}` — crée la branche `feat/{numero}-{nom}` depuis `main`
2. Implémenter avec les skills ci-dessous
3. `/finish-issue {numero}` — met à jour docs + ferme l'issue + ouvre la PR
4. **Attendre la revue et validation de la PR avant de merger**
5. Après merge : `/deploy` pour mettre en prod

## Skills disponibles

| Commande | Description |
|---|---|
| `/start-issue` | Crée une branche `feat/{numero}-{nom}` depuis `main` |
| `/finish-issue` | Met à jour docs, ferme l'issue, ouvre la PR |
| `/add-scraper` | Scaffolde un nouveau scraper + ouvre une PR |
| `/db-migrate` | Crée et applique une migration Alembic + ouvre une PR |
| `/check-api` | Vérifie que tous les endpoints API répondent correctement |
| `/deploy` | Build frontend + redémarre la stack via systemd |
| `/test` | Lance la suite de tests du backend |
