# Architecture v2 — dl_discord_bot

## 1. Vue d'ensemble du système

```mermaid
graph TB
    subgraph Clients
        DC[🤖 Discord Bot<br/>thin client HTTP]
        WB[🌐 Navigateur<br/>Angular 21 + Tailwind 4]
    end

    subgraph Backend["⚙️ Backend FastAPI :8000"]
        direction TB
        API[REST API<br/>/api/v1/*]
        WS[WebSocket<br/>/ws/*]
        SVC[Services Layer<br/>search · download · alldebrid]
        QUEUE[Download Queue<br/>asyncio workers]
        SCRAPERS[Scrapers<br/>wawacity · darkiworld†]
        DB[(SQLite<br/>downloads · history · settings)]
    end

    subgraph External["🌍 Services externes"]
        WAW[Wawacity<br/>Selenium + BS4]
        DLP[dl-protect.link<br/>Turnstile bypass]
        AD[AllDebrid API<br/>link debridding]
        CDN[Fichiers source<br/>1fichier · Turbobit · Rapidgator]
    end

    subgraph Storage["💾 Stockage"]
        FS[Système de fichiers<br/>Movies/ · Shows/]
    end

    DC -->|HTTP + aiohttp| API
    WB -->|HTTP + Angular HttpClient| API
    WB -->|RxJS WebSocketSubject| WS

    API --> SVC
    WS --> QUEUE
    SVC --> QUEUE
    SVC --> SCRAPERS
    SVC --> DB
    QUEUE --> SVC
    QUEUE -->|événements progression| WS

    SCRAPERS -->|Selenium + BS4| WAW
    SCRAPERS -->|Selenium UC| DLP
    SVC -->|aiohttp| AD
    QUEUE -->|aiohttp streaming| CDN
    QUEUE -->|écriture chunks| FS

    style DC fill:#5865F2,color:#fff
    style WB fill:#DD0031,color:#fff
    style Backend fill:#1a1a2e,color:#fff
    style External fill:#16213e,color:#fff
    style Storage fill:#0f3460,color:#fff
```

---

## 2. Flux de données — Téléchargement serveur

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant C as Client<br/>(Discord / Web)
    participant API as FastAPI
    participant SVC as DownloadService
    participant SCR as WawacityScraper
    participant DLP as dl-protect.link
    participant AD as AllDebrid
    participant FS as Fichiers

    U->>C: "Télécharger Inception (serveur)"
    C->>API: POST /api/v1/downloads<br/>{ source_url, media_type, destination: "server" }
    API-->>C: { download_id: uuid, status: "queued" }

    Note over API,FS: Worker asyncio prend en charge

    API->>SVC: enqueue(task)
    SVC->>SCR: get_provider_links(source_url)
    SCR->>DLP: Selenium — bypass Turnstile
    DLP-->>SCR: URL protégée provider
    SCR-->>SVC: [ProviderLinks]

    SVC->>AD: debrid_link(protected_url)
    AD-->>SVC: direct_url + filename

    loop Téléchargement par chunks
        SVC->>FS: écriture chunk
        SVC->>API: emit(progress_pct, speed_mbps)
        API-->>C: WS { status, progress_pct, speed_mbps, eta_s }
    end

    SVC->>API: emit(status: "completed")
    API-->>C: WS { status: "completed", filename }
```

---

## 3. Flux de données — Téléchargement client (lien direct)

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant WB as Angular Frontend
    participant API as FastAPI
    participant SVC as DownloadService
    participant SCR as WawacityScraper
    participant AD as AllDebrid

    U->>WB: "Télécharger Inception (lien direct)"
    WB->>API: POST /api/v1/downloads<br/>{ source_url, destination: "client" }
    API-->>WB: { download_id: uuid, status: "queued" }

    Note over API,AD: Même pipeline jusqu'à AllDebrid, pas d'écriture disque

    API->>SVC: enqueue(task)
    SVC->>SCR: get_provider_links(source_url)
    SCR-->>SVC: [ProviderLinks]
    SVC->>AD: debrid_link(protected_url)
    AD-->>SVC: debrid_url (TTL limité)

    SVC->>API: emit(status: "ready_for_client", debrid_url)
    API-->>WB: WS { status: "ready_for_client", debrid_url }
    WB->>U: window.open(debrid_url)<br/>→ téléchargement navigateur natif

    Note over WB,U: Aucun fichier stocké côté serveur
```

---

## 4. Architecture interne du Backend

```mermaid
graph LR
    subgraph api["api/v1/"]
        S[search.py]
        D[downloads.py]
        H[history.py]
        ST[settings.py]
        STA[status.py]
        W[ws.py]
    end

    subgraph core["core/"]
        Q[queue.py<br/>DownloadQueue<br/>asyncio.Queue + Semaphore]
        E[events.py<br/>Event Bus<br/>dict UUID → asyncio.Queue]
    end

    subgraph services["services/"]
        SS[search_service.py]
        DS[download_service.py]
        AL[alldebrid.py<br/>AllDebridClient async]
    end

    subgraph scrapers["scrapers/"]
        BS[base.py<br/>BaseScraper ABC<br/>@register decorator]
        WW[wawacity.py<br/>WawacityScraper]
        DW[darkiworld.py<br/>DarkiworldScraper †]
    end

    subgraph models["models/"]
        ORM[orm.py<br/>SQLAlchemy tables]
        SCH[schemas.py<br/>Pydantic schemas]
    end

    S --> SS
    D --> Q
    D --> DS
    H --> ORM
    ST --> ORM
    STA --> Q
    W --> E

    SS --> BS
    DS --> AL
    DS --> E
    Q --> DS
    Q --> E

    BS --> WW
    BS --> DW

    WW -->|Selenium + BS4| WAW[(Wawacity)]
    AL -->|aiohttp| AD[(AllDebrid API)]

    style BS fill:#2d6a4f,color:#fff
    style Q fill:#1b4332,color:#fff
    style E fill:#1b4332,color:#fff
```

---

## 5. Schéma de la base de données

```mermaid
erDiagram
    downloads {
        TEXT id PK "UUID"
        DATETIME created_at
        DATETIME updated_at
        TEXT title
        TEXT source_url
        TEXT source "wawacity | darkiworld"
        TEXT media_type "movie | serie"
        TEXT destination "server | client"
        TEXT status "queued | scraping | debriding | downloading | completed | error | cancelled | ready_for_client"
        TEXT provider "1fichier | Turbobit | Rapidgator"
        TEXT filename
        TEXT file_path "NULL si client"
        TEXT direct_url "URL AllDebrid débriddée"
        INTEGER file_size "bytes"
        INTEGER bytes_downloaded
        TEXT error_message
        TEXT requested_by "Discord user ID | web"
    }

    history {
        INTEGER id PK
        DATETIME created_at
        TEXT title
        TEXT source_url
        TEXT source
        TEXT media_type
        TEXT filename
        TEXT status "completed | error"
        TEXT requested_by
    }

    settings {
        TEXT key PK "download_path | default_source | default_providers | ..."
        TEXT value
        DATETIME updated_at
    }
```

---

## 6. Architecture des scrapers (plugin system)

```mermaid
classDiagram
    class BaseScraper {
        <<abstract>>
        +str source_name
        +search(query, category, year, limit) list~SearchResult~
        +get_provider_links(url, providers) list~ProviderLinks~
    }

    class SearchResult {
        +str title
        +str year
        +str quality
        +str language
        +str image_url
        +str source_url
        +str source
    }

    class ProviderLinks {
        +str title
        +list~str~ links
        +str provider
    }

    class WawacityScraper {
        +str source_name = "wawacity"
        +search() list~SearchResult~
        +get_provider_links() list~ProviderLinks~
        -_resolve_dl_protect() str
        -_match_language() str
    }

    class DarkiworldScraper {
        +str source_name = "darkiworld"
        +search() NotImplementedError
        +get_provider_links() NotImplementedError
    }

    class ScraperRegistry {
        +dict _registry
        +register(cls) decorator
        +get_scraper(source) BaseScraper
    }

    BaseScraper <|-- WawacityScraper
    BaseScraper <|-- DarkiworldScraper
    BaseScraper ..> SearchResult
    BaseScraper ..> ProviderLinks
    ScraperRegistry --> BaseScraper
```

---

## 7. Structure du monorepo

```
dl_discord_bot/                     ← monorepo racine
│
├── backend/                        ← FastAPI (Python)
│   ├── app/
│   │   ├── main.py                 ← factory + lifespan (démarrage workers)
│   │   ├── config.py               ← pydantic-settings
│   │   ├── database.py             ← SQLAlchemy async + aiosqlite
│   │   ├── api/v1/
│   │   │   ├── search.py           ← GET /api/v1/search
│   │   │   ├── downloads.py        ← POST/GET/DELETE /api/v1/downloads
│   │   │   ├── history.py          ← GET/DELETE /api/v1/history
│   │   │   ├── settings.py         ← GET/PUT /api/v1/settings
│   │   │   ├── status.py           ← GET /api/v1/status
│   │   │   └── ws.py               ← WS /ws/downloads/{id} + /ws/queue
│   │   ├── core/
│   │   │   ├── queue.py            ← DownloadQueue (asyncio.Queue + Semaphore)
│   │   │   └── events.py           ← Event bus (dict UUID → asyncio.Queue)
│   │   ├── scrapers/
│   │   │   ├── base.py             ← BaseScraper ABC + @register + get_scraper()
│   │   │   ├── wawacity.py         ← ← migration parser.py
│   │   │   └── darkiworld.py       ← stub NotImplementedError
│   │   ├── services/
│   │   │   ├── search_service.py   ← orchestre scraper
│   │   │   ├── download_service.py ← debrid + download + progression
│   │   │   └── alldebrid.py        ← ← migration alldebrid.py (async)
│   │   └── models/
│   │       ├── orm.py              ← tables SQLAlchemy
│   │       └── schemas.py          ← Pydantic request/response
│   ├── alembic/                    ← migrations BDD
│   ├── scripts/
│   │   └── migrate_csv.py          ← import history.csv → SQLite
│   └── pyproject.toml
│
├── bot/                            ← Discord Bot (Python)
│   ├── main.py                     ← entry point
│   ├── client.py                   ← BackendClient (aiohttp wrapper)
│   ├── cogs/
│   │   ├── search.py               ← !search → GET /api/v1/search
│   │   └── download.py             ← !url, !status → POST /api/v1/downloads
│   └── pyproject.toml              ← sans selenium/pandas/beautifulsoup4
│
├── frontend/                       ← Angular 21 + Tailwind CSS v3
│   ├── src/app/
│   │   ├── core/
│   │   │   ├── models/
│   │   │   │   └── api.models.ts   ← interfaces TypeScript partagées
│   │   │   └── services/
│   │   │       ├── api.service.ts  ← HttpClient → :8000/api/v1
│   │   │       └── ws.service.ts   ← RxJS WebSocketSubject → :8000/ws
│   │   ├── features/               ← lazy-loaded via loadChildren
│   │   │   ├── search/             ← rxResource search + modal téléchargement
│   │   │   ├── downloads/          ← linkedSignal + WS patch en temps réel
│   │   │   ├── history/            ← params signal + pagination
│   │   │   └── settings/           ← linkedSignal par champ initialisé depuis API
│   │   └── shared/
│   │       └── components/
│   │           └── sidebar/        ← rxResource status + polling 10s
│   └── package.json
│
├── docs/
│   └── architecture-v2.md          ← ce fichier
├── docker-compose.yml
└── .env.example
```

---

## 8. Déploiement Docker

```mermaid
graph TB
    subgraph docker["docker-compose.yml"]
        subgraph net["réseau interne dl_network"]
            BE["backend<br/>:8000<br/>image: python:3.12-slim<br/>uvicorn app.main:app"]
            BOT["bot<br/>image: python:3.12-slim<br/>depends_on: backend"]
            FE["frontend<br/>:80<br/>image: node + nginx<br/>ng build → nginx"]
        end

        V1[("volume<br/>download_path<br/>/data/media")]
        V2[("volume<br/>sqlite_db<br/>/data/db")]
    end

    USER["👤 Utilisateur<br/>réseau local / VPN"] -->|:80| FE
    USER -->|Discord| BOT
    FE -->|:8000| BE
    BOT -->|:8000| BE
    BE --- V1
    BE --- V2

    style BE fill:#009688,color:#fff
    style BOT fill:#5865F2,color:#fff
    style FE fill:#DD0031,color:#fff
```

> † Darkiworld : stub prévu en Phase 4, implémentation future
