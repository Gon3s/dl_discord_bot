<div align="center">

# 🎬 dl_discord_bot

**Application trois tiers pour rechercher et télécharger des films, séries et mangas**  
via AllDebrid / Real-Debrid, pilotable depuis une interface web ou Discord.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Angular](https://img.shields.io/badge/Angular-21-DD0031?logo=angular&logoColor=white)](https://angular.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/tests-140%20passed-4CAF50?logo=pytest&logoColor=white)](backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

![Demo](demo/demo.gif)

</div>

---

## ✨ Fonctionnalités

- 🔍 **Recherche unifiée** - Films, séries et mangas sur [Wawacity](https://www.wawacity.city/), [DarkiWorld](https://darkiworld16.com) et [1337x](https://1337x.to) depuis une seule interface
- ⚡ **Débridage automatique** - Compatible [AllDebrid](https://alldebrid.com) et [Real-Debrid](https://real-debrid.com), résolution des liens dl-protect via Selenium
- 📺 **Gestion des épisodes** - Sélection de saisons et épisodes directement depuis l'UI
- 📡 **Progression temps réel** - Suivi des téléchargements via WebSocket
- 📂 **Historique & favoris** - Consultation et recherche des téléchargements passés
- ⚙️ **Paramètres dynamiques** - Configuration modifiable depuis l'interface sans redémarrage
- 🤖 **Bot Discord** - Lancer une recherche ou un téléchargement depuis n'importe quel canal

---

## 📸 Aperçu

<details>
<summary>Voir les screenshots</summary>

| Recherche | Modal téléchargement |
|:---------:|:--------------------:|
| ![Search](demo/screenshots/02_search_results.png) | ![Modal](demo/screenshots/03_download_modal.png) |

| Sélection d'épisodes | File de téléchargement |
|:--------------------:|:----------------------:|
| ![Episodes](demo/screenshots/05_episodes_panel.png) | ![Downloads](demo/screenshots/06_downloads.png) |

| Historique | Paramètres |
|:----------:|:----------:|
| ![History](demo/screenshots/07_history.png) | ![Settings](demo/screenshots/08_settings.png) |

</details>

---

## 🏗️ Architecture

```
dl_discord_bot/
├── backend/        FastAPI · SQLite · Alembic · aiohttp · SeleniumBase
├── frontend/       Angular 21 · Tailwind CSS v3 · Signals · WebSocket
├── bot/            Discord thin client → appels HTTP au backend
└── deploy/         Scripts systemd (install.sh + units)
```

Le backend sert également le frontend buildé en production - un seul port `:8000` suffit.

---

## 🚀 Démarrage rapide

### Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Python | 3.12 |
| [uv](https://docs.astral.sh/uv/) | dernière |
| Node.js | 20+ |
| Chrome / Chromium | requis pour Selenium (liens dl-protect) |

### 1. Configuration

```bash
cp .env.example .env
```

Remplir au minimum dans `.env` :

```bash
DISCORD_TOKEN=          # Token du bot Discord
DEBRID_PROVIDER=alldebrid
ALLDEBRID_API_KEY=      # ou REALDEBRID_API_TOKEN=
DOWNLOAD_PATH=/data/media
WAWACITY_URL=https://www.wawacity.city/
```

> Voir la section [Variables d'environnement](#-variables-denvironnement) pour la liste complète.

### 2. Développement local

```bash
# Backend - API + frontend buildé sur :8000
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Frontend - hot-reload sur :4200 (dev uniquement)
cd frontend
npm ci && npm run start -- --port 4200

# Bot Discord
cd bot
uv run python main.py
```

> En développement, le proxy Angular redirige `/api` et `/ws` vers `:8000` automatiquement.

### 3. Production (systemd)

```bash
bash deploy/install.sh
```

Ce script :
1. Build le frontend Angular (`ng build --configuration production`)
2. Applique les migrations Alembic
3. Installe et démarre `dl_backend.service` + `discord_bot.service`

L'interface est ensuite accessible sur **`http://<serveur>:8000`**.

```bash
# Mise à jour après un pull
sudo systemctl restart dl_backend.service discord_bot.service

# Logs en direct
journalctl -u dl_backend -u discord_bot -f
```

---

## 🔧 Variables d'environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Token du bot Discord | `MTI...` |
| `DISCORD_GUILD` | ID du serveur Discord | `123456789` |
| `DEBRID_PROVIDER` | Fournisseur actif | `alldebrid` ou `realdebrid` |
| `ALLDEBRID_API_KEY` | Clé API AllDebrid | `abc123` |
| `REALDEBRID_API_TOKEN` | Token API Real-Debrid | `abc123` |
| `DOWNLOAD_PATH` | Répertoire de destination | `/data/media` |
| `WAWACITY_URL` | URL de base Wawacity | `https://www.wawacity.city/` |
| `1337X_URL` | URL de base 1337x | `https://1337x.to` |
| `DARKIWORLD_URL` | URL de base DarkiWorld | `https://darkiworld16.com` |
| `DARKIWORLD_EMAIL` | Email du compte DarkiWorld | `user@example.com` |
| `DARKIWORLD_PASSWORD` | Mot de passe du compte DarkiWorld | `***` |
| `DATABASE_URL` | SQLite async | `sqlite+aiosqlite:///./dl_bot.db` |
| `MAX_CONCURRENT_DOWNLOADS` | Téléchargements simultanés | `2` |
| `SELENIUM_BINARY_LOCATION` | Binaire Chrome pour SeleniumBase | `cft` ou `/usr/bin/chromium` |
| `BACKEND_URL` | URL backend pour le bot | `http://localhost:8000` |

> Les paramètres opérationnels (`debrid_provider`, `download_path`, etc.) sont modifiables depuis l'interface web sans redémarrage.

---

## 🌐 API REST

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/search` | Rechercher un titre (`?q=&source=&category=`) |
| `GET` | `/api/v1/episodes` | Lister les épisodes d'une série |
| `POST` | `/api/v1/downloads` | Lancer un téléchargement |
| `GET` | `/api/v1/downloads` | Lister les téléchargements actifs |
| `GET` | `/api/v1/downloads/{id}` | Détail d'un téléchargement |
| `DELETE` | `/api/v1/downloads/{id}` | Supprimer un téléchargement |
| `POST` | `/api/v1/downloads/{id}/retry` | Relancer un téléchargement en erreur |
| `GET` | `/api/v1/history` | Historique des téléchargements |
| `DELETE` | `/api/v1/history/{id}` | Supprimer une entrée de l'historique |
| `GET` | `/api/v1/favorites` | Favoris |
| `GET` | `/api/v1/settings` | Lire la configuration |
| `PUT` | `/api/v1/settings` | Mettre à jour la configuration |
| `GET` | `/api/v1/status` | Santé du backend |
| `WS` | `/ws/downloads/{id}` | Progression temps réel d'un téléchargement |
| `WS` | `/ws/queue` | État de la file d'attente |

Une collection [Bruno](https://www.usebruno.com/) complète est disponible dans `bruno/`.

---

## 🤖 Commandes Discord

| Commande | Description |
|----------|-------------|
| `!search <titre> [films\|series\|mangas]` | Rechercher un titre |
| `!url <url>` | Télécharger depuis une URL directe |
| `!status` | Statut du backend et du fournisseur de débridage |

---

## 🧩 Ajouter un scraper

Créer `backend/app/scrapers/<nom>.py` - le registre est automatique :

```python
from app.scrapers.base import BaseScraper, SearchResult, ProviderLinks, register

@register
class MonScraper(BaseScraper):
    source_name = "mon_source"  # valeur du paramètre ?source= dans l'API

    async def search(
        self, query: str, category: str, year=None, limit=10, sort=None, page=1
    ) -> list[SearchResult]: ...

    async def get_provider_links(
        self, url: str, providers: list[str]
    ) -> list[ProviderLinks]: ...

    async def get_episodes(self, url: str, providers=None): ...
```

Aucune autre modification n'est nécessaire.

---

## 🧪 Tests & qualité

```bash
cd backend

# Suite de tests (pytest-asyncio)
uv run pytest

# Linter
uv run ruff check

# Formatter
uv run ruff format
```

---

## 🗄️ Migrations base de données

```bash
cd backend

# Créer une migration après modification des modèles ORM
uv run alembic revision --autogenerate -m "description"

# Appliquer toutes les migrations
uv run alembic upgrade head

# Rollback d'une migration
uv run alembic downgrade -1
```

---

## 📖 Documentation

- [`docs/plan-v2.md`](docs/plan-v2.md) - Plan d'implémentation et décisions de conception
- [`docs/architecture-v2.md`](docs/architecture-v2.md) - Diagrammes d'architecture

---

## ⚠️ Avertissement légal

Ce projet est fourni à des fins éducatives et pour usage personnel uniquement.  
Respectez les conditions d'utilisation des sites sources et les lois en vigueur dans votre pays concernant le téléchargement de contenus protégés.

---

## 📄 Licence

[MIT](LICENSE)
