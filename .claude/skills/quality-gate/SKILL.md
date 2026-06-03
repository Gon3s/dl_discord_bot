---
name: quality-gate
description: Lance le garde-fou qualité local avant un commit/PR sur DLux — format + lint Python (ruff) sur backend et bot, puis build Angular du frontend. À utiliser avant de committer, d'ouvrir une PR, ou quand l'utilisateur demande de "vérifier que ça build / ça passe".
---

# quality-gate

Reproduit localement ce que la CI (`.github/workflows/ci.yml`) vérifiera, pour
attraper les régressions avant le push.

## Étapes

1. **Backend — format + lint**
   ```bash
   cd backend
   uv run ruff format
   uv run ruff check
   ```
   Config : `line-length = 88`, règles `E, F, I, UP`, `alembic/` exclu.

2. **Bot — lint** (même règle ruff, pas de pyproject dédié → utiliser celui du backend)
   ```bash
   cd bot
   uv run ruff check .
   ```

3. **Frontend — build**
   ```bash
   cd frontend
   npm run build
   ```
   > WSL : ne pas utiliser le `npm` Windows. Si besoin :
   > `export PATH="$PWD/.codex/runtime/node-v22.12.0-linux-x64/bin:$PATH"`

## Critère de succès

`ruff check` sans erreur ET `ng build` terminé sans erreur. Si `ruff format` a
modifié des fichiers, les signaler (ils font partie du diff à committer).

Si une étape échoue, s'arrêter, rapporter l'erreur exacte, ne pas committer.
