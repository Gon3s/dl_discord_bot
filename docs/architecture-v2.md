# Architecture v2 — dl_discord_bot

## 1. Vue d'ensemble du système

```mermaid
graph TB
    subgraph Clients
        DC[🤖 Discord Bot<br/>thin client HTTP]
        WB[🌐 Navigateur<br/>Angular 21 + Tailwind 3]
    end

    subgraph Backend["⚙️ Backend FastAPI :8000"]
        direction TB
        SPA[Fichiers statiques<br/>Angular dist/ — catch-all /*]
        API[REST API<br/>/api/v1/*]
        WS[WebSocket<br/>/ws/*]
        SVC[Services Layer<br/>search · download · debrid]
        QUEUE[Download Queue<br/>asyncio workers]
        SCRAPERS[Scrapers<br/>wawacity · darkiworld · 1337x]
        DB[(SQLite<br/>downloads · history · settings)]
    end

    subgraph External["🌍 Services externes"]
        WAW[Wawacity<br/>Selenium + BS4]
        DWX[DarkiWorld<br/>Selenium login + API JSON]
        X1337[1337x<br/>HTML + magnets]
        DLP[dl-protect.link<br/>Turnstile bypass]
        AD[Debrid API<br/>AllDebrid · Real-Debrid]
        CDN[Fichiers source<br/>1fichier · Turbobit · Rapidgator · torrents]
    end

    subgraph Storage["💾 Stockage"]
        FS[Système de fichiers<br/>Movies/ · Shows/]
    end

    DC -->|HTTP + aiohttp| API
    WB -->|"GET /* — app shell + assets"| SPA
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
    SCRAPERS -->|aiohttp + session cookies| DWX
    SCRAPERS -->|aiohttp + BS4| X1337
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
    participant AD as Debrid provider
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

    Note over SVC,AD: Pour 1337x, le provider est "magnet" : upload_magnet → status → files.

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
    participant AD as Debrid provider

    U->>WB: "Télécharger Inception (lien direct)"
    WB->>API: POST /api/v1/downloads<br/>{ source_url, destination: "client" }
    API-->>WB: { download_id: uuid, status: "queued" }

    Note over API,AD: Même pipeline jusqu'au fournisseur de débridage, pas d'écriture disque

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
        DS[download_service.py]
        AL[debrid.py<br/>DebridClient factory]
        ADP[alldebrid.py<br/>AllDebridClient]
        RDP[realdebrid.py<br/>RealDebridClient]
    end

    subgraph scrapers["scrapers/"]
        BS[base.py<br/>BaseScraper ABC<br/>@register decorator]
        WW[wawacity.py<br/>WawacityScraper]
        DW[darkiworld.py<br/>DarkiworldScraper]
        X3[x1337.py<br/>Scraper1337x]
    end

    subgraph models["models/"]
        ORM[orm.py<br/>SQLAlchemy tables]
        SCH[schemas.py<br/>Pydantic schemas]
    end

    S --> BS
    D --> Q
    D --> DS
    H --> ORM
    ST --> ORM
    STA --> Q
    W --> E

    DS --> AL
    AL --> ADP
    AL --> RDP
    DS --> E
    Q --> DS
    Q --> E

    BS --> WW
    BS --> DW
    BS --> X3

    WW -->|Selenium + BS4| WAW[(Wawacity)]
    DW -->|Selenium login + aiohttp| DWAPI[(DarkiWorld)]
    X3 -->|aiohttp + BS4| X1337API[(1337x)]
    ADP -->|aiohttp| AD[(AllDebrid API)]
    RDP -->|aiohttp| RD[(Real-Debrid API)]

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
        TEXT source "wawacity | darkiworld | 1337x"
        TEXT media_type "movie | serie"
        TEXT destination "server | client"
        TEXT status "queued | scraping | debriding | downloading | completed | error | cancelled | ready_for_client"
        TEXT provider "1fichier | Turbobit | Rapidgator"
        TEXT filename
        TEXT file_path "NULL si client"
        TEXT direct_url "URL fournisseur débriddée"
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
        +search(query, category, year, limit, sort, page) list~SearchResult~
        +get_provider_links(url, providers) list~ProviderLinks~
        +get_episodes(url, providers) list~Episode~
    }

    class SearchResult {
        +str title
        +str year
        +str quality
        +str language
        +str poster_url
        +str url
        +str source
    }

    class ProviderLinks {
        +str provider
        +list~str~ urls
    }

    class WawacityScraper {
        +str source_name = "wawacity"
        +search() list~SearchResult~
        +get_provider_links() list~ProviderLinks~
        +get_episodes() list~Episode~
        -_resolve_dl_protect() str
        -_match_language() str
    }

    class DarkiworldScraper {
        +str source_name = "darkiworld"
        +search() list~SearchResult~
        +get_provider_links() list~ProviderLinks~
        +get_episodes() list~Episode~
    }

    class Scraper1337x {
        +str source_name = "1337x"
        +search() list~SearchResult~
        +get_provider_links() list~ProviderLinks~
        +get_episodes() list~Episode~
    }

    class ScraperRegistry {
        +dict _registry
        +register(cls) decorator
        +get_scraper(source) BaseScraper
    }

    BaseScraper <|-- WawacityScraper
    BaseScraper <|-- DarkiworldScraper
    BaseScraper <|-- Scraper1337x
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
│   │   │   ├── episodes.py         ← GET /api/v1/episodes
│   │   │   ├── favorites.py        ← GET/POST/DELETE /api/v1/favorites
│   │   │   ├── downloads.py        ← POST/GET/DELETE /api/v1/downloads
│   │   │   ├── history.py          ← GET/DELETE /api/v1/history
│   │   │   ├── settings.py         ← GET/PUT /api/v1/settings
│   │   │   ├── status.py           ← GET /api/v1/status
│   │   ├── api/
│   │   │   └── ws.py               ← WS /ws/downloads/{id} + /ws/queue
│   │   ├── core/
│   │   │   ├── queue.py            ← DownloadQueue (asyncio.Queue + Semaphore)
│   │   │   └── events.py           ← Event bus (dict UUID → asyncio.Queue)
│   │   ├── scrapers/
│   │   │   ├── base.py             ← BaseScraper ABC + @register + get_scraper()
│   │   │   ├── wawacity.py
│   │   │   └── darkiworld.py       ← session Selenium + API JSON
│   │   ├── services/
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
│   │   │   │   ├── search.type.ts  ← interfaces TypeScript partagées
│   │   │   │   ├── download.type.ts
│   │   │   │   └── index.ts
│   │   │   └── services/
│   │   │       ├── api.service.ts  ← HttpClient → /api/v1 (même origin)
│   │   │       └── ws.service.ts   ← RxJS WebSocketSubject → /ws
│   │   ├── features/               ← lazy-loaded via loadChildren
│   │   │   ├── search/             ← recherche + modal téléchargement
│   │   │   ├── downloads/          ← liste active + WS temps réel
│   │   │   ├── history/            ← params signal + pagination
│   │   │   └── settings/           ← linkedSignal par champ initialisé depuis API
│   │   └── shared/
│   │       └── components/
│   │           └── sidebar/        ← rxResource status + polling 10s
│   ├── dist/frontend/browser/      ← build prod (ng build) servi par FastAPI
│   └── package.json
│
├── docs/
│   └── architecture-v2.md          ← ce fichier
├── deploy/                         ← services systemd + install.sh
└── .env.example
```

---

## 8. Déploiement actuel : systemd

```mermaid
graph TB
    subgraph host["serveur Linux"]
        INSTALL["deploy/install.sh<br/>build Angular + migrations"]
        XVFB["xvfb.service<br/>Xvfb :99 — display virtuel<br/>pour Selenium / Turnstile"]
        BE["dl_backend.service<br/>uvicorn app.main:app :8000<br/>API + frontend statique<br/>DISPLAY=:99"]
        BOT["discord_bot.service<br/>python bot/main.py"]
        DB[("SQLite<br/>dl_bot.db")]
        MEDIA[("DOWNLOAD_PATH")]
    end

    USER["👤 Utilisateur<br/>réseau local / VPN"] -->|":8000 (UI + API)"| BE
    USER -->|Discord| BOT
    BOT -->|BACKEND_URL| BE
    INSTALL --> BE
    INSTALL --> BOT
    XVFB --> BE
    BE --- DB
    BE --- MEDIA

    style BE fill:#009688,color:#fff
    style BOT fill:#5865F2,color:#fff
    style XVFB fill:#607d8b,color:#fff
```

Docker Compose est encore à faire et suivi par l'issue #44.
