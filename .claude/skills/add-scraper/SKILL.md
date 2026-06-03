---
name: add-scraper
description: Scaffolde un nouveau scraper de source de données pour DLux. Argument = nom de la source (ex: darkiworld). À utiliser quand l'utilisateur veut ajouter une source de recherche/téléchargement en plus de wawacity.
---

# add-scraper

Crée `backend/app/scrapers/<nom>.py` implémentant `BaseScraper`. Le registre
(`@register`) est automatique — aucune autre modification de câblage nécessaire.

## Prérequis

- `$ARGUMENTS` = `source_name` (slug, ex: `darkiworld`). C'est la valeur du
  param `?source=` dans l'API.

## Contrat (voir `backend/app/scrapers/base.py`)

Implémenter les 3 méthodes abstraites ; `resolve_link` est optionnelle (override
si la source passe par dl-protect ou un intermédiaire) :

```python
from app.scrapers.base import (
    BaseScraper, SearchResult, ProviderLinks, Episode, register,
)


@register
class <Nom>Scraper(BaseScraper):
    source_name = "$ARGUMENTS"

    async def search(
        self, query="", category="films", year=None, limit=10, sort=None, page=1
    ) -> list[SearchResult]:
        ...

    async def get_provider_links(self, url, providers) -> list[ProviderLinks]:
        ...

    async def get_episodes(self, url, providers=None) -> list[Episode]:
        ...

    # async def resolve_link(self, url: str) -> str:  # si dl-protect/intermédiaire
    #     ...
```

## Règles backend (rappel)

- Async partout, pas de `requests` ni d'appel bloquant dans une coroutine.
- Selenium (bloquant) → `run_in_executor` + `asyncio.Semaphore(1)` (pas de
  parallélisation Chrome).
- Type hints obligatoires.

## Critère de succès

Fichier créé, `import` du module OK, scraper visible via `get_scraper("$ARGUMENTS")`.
Ajouter une ligne dans la table **Sources actuelles** du `CLAUDE.md`. Proposer un
test dans `backend/tests/test_scrapers.py`.
