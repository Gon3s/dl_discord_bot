---
name: api-smoke
description: Vérifie que les endpoints de l'API backend DLux répondent, via la collection Bruno (dossier bruno/). À utiliser après un démarrage du backend, avant un déploiement, ou quand l'utilisateur demande de "tester l'API / vérifier les endpoints".
---

# api-smoke

Joue la collection Bruno `bruno/` (DLux API) contre une cible pour un smoke test
des endpoints (search, downloads, episodes, history, favorites, settings, status).

## Prérequis

- Backend lancé (`cd backend && uv run uvicorn app.main:app --port 8000`).
- CLI Bruno : `npx @usebruno/cli` (pas d'install globale requise).
- Environnements dispo : `bruno/environments/local.bru` et `server.bru`.

## Étapes

```bash
cd bruno
npx @usebruno/cli run . --env local
```

Cibler le serveur prod : `--env server`.

## Fallback (sans Bruno CLI)

Smoke test manuel des routes clés (voir section "Structure des endpoints API"
du `CLAUDE.md`) avec `curl` :

```bash
curl -s localhost:8000/api/v1/status
curl -s "localhost:8000/api/v1/search?source=wawacity&category=films"
curl -s localhost:8000/api/v1/downloads
curl -s localhost:8000/api/v1/favorites
curl -s localhost:8000/api/v1/notifications
curl -s localhost:8000/api/v1/history
curl -s localhost:8000/api/v1/settings
```

## Critère de succès

Toutes les requêtes Bruno passent (assertions vertes) / tous les `curl`
renvoient 2xx. Rapporter toute route en erreur avec son code HTTP.
